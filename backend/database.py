import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(os.getenv("CUBON3_DB_PATH", str(Path(__file__).resolve().parent / "cubon3.db")))


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                provider_task_id INTEGER UNIQUE,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                provider_status INTEGER,
                glb_file TEXT,
                size_bytes INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_created_at
            ON tasks(created_at DESC);

            CREATE TABLE IF NOT EXISTS dicom_jobs (
                job_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                source_files INTEGER NOT NULL,
                slices INTEGER NOT NULL DEFAULT 0,
                stage TEXT NOT NULL DEFAULT 'queued',
                bundle_size INTEGER,
                error TEXT,
                validation_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_dicom_jobs_created_at
            ON dicom_jobs(created_at DESC);
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(dicom_jobs)").fetchall()
        }
        if "stage" not in columns:
            connection.execute(
                "ALTER TABLE dicom_jobs ADD COLUMN stage TEXT NOT NULL DEFAULT 'queued'"
            )
        if "validation_json" not in columns:
            connection.execute(
                "ALTER TABLE dicom_jobs ADD COLUMN validation_json TEXT"
            )
        connection.execute(
            """
            UPDATE dicom_jobs
            SET status = 'failed',
                stage = 'failed',
                error = 'Processing was interrupted by a backend restart.',
                updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('queued', 'processing')
            """
        )


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def create_task(provider_task_id: int, name: str) -> dict:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO tasks (provider_task_id, name, status)
            VALUES (?, ?, 'submitted')
            """,
            (provider_task_id, name),
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE provider_task_id = ?",
            (provider_task_id,),
        ).fetchone()
    return dict(row)


def get_task(provider_task_id: int) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE provider_task_id = ?",
            (provider_task_id,),
        ).fetchone()
    return dict(row) if row else None


def list_tasks() -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def update_task(provider_task_id: int, status: str, provider_status: int | None,
                glb_file: str | None = None, size_bytes: int | None = None) -> dict:
    with connect() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?,
                provider_status = ?,
                glb_file = COALESCE(?, glb_file),
                size_bytes = COALESCE(?, size_bytes),
                updated_at = CURRENT_TIMESTAMP
            WHERE provider_task_id = ?
            """,
            (status, provider_status, glb_file, size_bytes, provider_task_id),
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE provider_task_id = ?",
            (provider_task_id,),
        ).fetchone()
    return dict(row)


def delete_task(provider_task_id: int) -> bool:
    task = get_task(provider_task_id)
    if not task:
        return False

    if task.get("glb_file"):
        model_path = Path(__file__).resolve().parent / "generated" / task["glb_file"]
        if model_path.exists():
            model_path.unlink()

    with connect() as connection:
        connection.execute(
            "DELETE FROM tasks WHERE provider_task_id = ?",
            (provider_task_id,),
        )
    return True


def create_dicom_job(job_id: str, name: str, source_files: int) -> dict:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO dicom_jobs (job_id, name, status, source_files)
            VALUES (?, ?, 'queued', ?)
            """,
            (job_id, name, source_files),
        )
        row = connection.execute(
            "SELECT * FROM dicom_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return dict(row)


def get_dicom_job(job_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM dicom_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return dict(row) if row else None


def list_dicom_jobs(limit: int = 100) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM dicom_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_dicom_job(
    job_id: str,
    status: str,
    slices: int | None = None,
    bundle_size: int | None = None,
    error: str | None = None,
    stage: str | None = None,
    validation_json: str | None = None,
) -> dict | None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE dicom_jobs
            SET status = ?,
                slices = COALESCE(?, slices),
                bundle_size = COALESCE(?, bundle_size),
                error = ?,
                stage = COALESCE(?, stage),
                validation_json = COALESCE(?, validation_json),
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
            """,
            (status, slices, bundle_size, error, stage, validation_json, job_id),
        )
        row = connection.execute(
            "SELECT * FROM dicom_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_dicom_job(job_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM dicom_jobs WHERE job_id = ?",
            (job_id,),
        )
    return cursor.rowcount > 0
