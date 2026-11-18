import sqlite3

from database import init_db
from database import create_task, delete_task, get_task, list_tasks, update_task


def test_task_lifecycle(tmp_path, monkeypatch):
    import database
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    init_db()

    created = create_task(12345, "scan.png")
    assert created["provider_task_id"] == 12345
    assert created["status"] == "submitted"

    updated = update_task(12345, "completed", 3)
    assert updated["status"] == "completed"
    assert get_task(12345)["provider_status"] == 3
    assert len(list_tasks()) == 1

    assert delete_task(12345)
    assert get_task(12345) is None


def test_dicom_job_migration_marks_interrupted_job_failed(tmp_path, monkeypatch):
    import database

    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE dicom_jobs (
                job_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                source_files INTEGER NOT NULL,
                slices INTEGER NOT NULL DEFAULT 0,
                bundle_size INTEGER,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO dicom_jobs (job_id, name, status, source_files)
            VALUES ('interrupted-job', 'Legacy scan', 'processing', 3)
            """
        )

    init_db()

    job = database.get_dicom_job("interrupted-job")
    assert job["status"] == "failed"
    assert job["stage"] == "failed"
    assert "backend restart" in job["error"]
    assert "validation_json" in job
