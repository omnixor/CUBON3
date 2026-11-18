
import json
import os
import shutil
import tempfile
import uuid

from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import (
    create_dicom_job,
    create_task,
    delete_dicom_job,
    delete_task,
    get_dicom_job,
    get_task,
    init_db,
    list_dicom_jobs,
    list_tasks,
    update_dicom_job,
    update_task,
)
from services.aholo_service import (
    create_3d_task,
    get_3d_task,
    download_generated_model,
    normalize_image_to_png,
)
from services.dicom_service import get_job_dir, process_dicom_job

load_dotenv()

app = FastAPI(
    title="CUBON3",
    description="AI-powered medical imaging backend",
    version="1.1.0",
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GENERATED_DIR = Path(__file__).resolve().parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
init_db()

app.mount(
    "/models",
    StaticFiles(directory=GENERATED_DIR),
    name="models",
)


@app.get("/")
def home():
    return {
        "message": "Welcome to CUBON3!",
        "status": "Backend running",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "aholo_key_configured": bool(os.getenv("AHOLO_API_KEY")),
    }


@app.post("/api/aholo/generate")
async def generate_3d(file: UploadFile = File(...)):
    temp_path = None
    normalized_path = None
    try:
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=415,
                detail="Only JPEG, PNG, and WebP images are supported.",
            )

        max_size = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
        suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name
            total_bytes = 0
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Image exceeds the {os.getenv('MAX_UPLOAD_MB', '10')} MB limit.",
                    )
                temp_file.write(chunk)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as normalized_file:
            normalized_path = normalized_file.name
        try:
            normalize_image_to_png(temp_path, normalized_path)
        except ValueError as error:
            raise HTTPException(status_code=415, detail=str(error))

        task = submit_aholo_task(normalized_path, file.filename or "Untitled scan")
        return {**task, "input_format": "lossless PNG"}
    except HTTPException:
        raise
    except Exception as error:
        print("Generation error:", repr(error))
        raise HTTPException(
            status_code=502,
            detail="The 3D generation provider could not submit the request.",
        )
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()
        if normalized_path and Path(normalized_path).exists():
            Path(normalized_path).unlink()
        await file.close()


def submit_aholo_task(image_path: str | Path, name: str):
    result = create_3d_task(image_path)
    return create_task(result["task_id"], name)


@app.get("/api/aholo/task/{task_id}")
def check_3d_task(task_id: int):
    try:
        provider = get_3d_task(task_id)
        provider_status = provider.get("status")
        status_map = {
            1: "submitted",
            2: "processing",
            3: "completed",
            4: "failed",
        }
        status = status_map.get(provider_status, str(provider_status or "unknown"))
        stored = update_task(task_id, status, provider_status)
        return {**provider, "local": stored}
    except Exception as error:
        print("Task retrieval error:", repr(error))
        raise HTTPException(
            status_code=502,
            detail="Task status retrieval failed",
        )


@app.post("/api/aholo/task/{task_id}/download")
def download_3d_model(task_id: int):
    try:
        result = download_generated_model(task_id)
        updated = update_task(
            task_id,
            "downloaded",
            3,
            glb_file=result["file"],
            size_bytes=result["size_bytes"],
        )
        return {**result, "local": updated}
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except Exception as error:
        print("Download error:", repr(error))
        raise HTTPException(
            status_code=502,
            detail="3D model download failed",
        )


@app.get("/api/projects")
def projects(limit: int = Query(default=100, ge=1, le=500)):
    return {"projects": list_tasks()[:limit]}


@app.delete("/api/projects/{task_id}")
def delete_project(task_id: int):
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"task_id": task_id, "deleted": True}


@app.post("/api/dicom/import", status_code=202)
async def import_dicom_series(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="Select a DICOM series to import.")
    if len(files) > 2000:
        raise HTTPException(status_code=413, detail="A series may contain at most 2,000 files.")

    max_bytes = int(os.getenv("MAX_DICOM_UPLOAD_MB", "1024")) * 1024 * 1024
    job_id = str(uuid.uuid4())
    job_dir = get_job_dir(job_id)
    source_dir = job_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=False)
    total_bytes = 0

    try:
        for index, file in enumerate(files, start=1):
            target = source_dir / f"source_{index:05d}.dcm"
            with target.open("wb") as output:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"DICOM upload exceeds the {os.getenv('MAX_DICOM_UPLOAD_MB', '1024')} MB limit.",
                        )
                    output.write(chunk)

        job = create_dicom_job(
            job_id,
            f"DICOM series {job_id[:8]}",
            len(files),
        )
        background_tasks.add_task(process_dicom_job, job_id)
        return job
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(job_dir, ignore_errors=True)
        print("DICOM upload error:", repr(error))
        raise HTTPException(status_code=500, detail="Could not stage the DICOM series.")
    finally:
        for file in files:
            await file.close()


@app.get("/api/dicom/jobs")
def dicom_jobs(limit: int = Query(default=100, ge=1, le=500)):
    return {"jobs": [_serialize_dicom_job(job) for job in list_dicom_jobs(limit)]}


def _serialize_dicom_job(job: dict | None):
    if job is None:
        return None
    result = dict(job)
    validation = result.pop("validation_json", None)
    result["validation"] = json.loads(validation) if validation else None
    return result


@app.get("/api/dicom/jobs/{job_id}")
def dicom_job_status(job_id: str):
    try:
        get_job_dir(job_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    job = get_dicom_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="DICOM import job not found.")
    return _serialize_dicom_job(job)


@app.get("/api/dicom/jobs/{job_id}/bundle")
def download_dicom_bundle(job_id: str):
    try:
        job_dir = get_job_dir(job_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    job = get_dicom_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="DICOM import job not found.")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="DICOM conversion is not complete.")

    bundle_path = job_dir / "converted-series.zip"
    if not bundle_path.is_file():
        raise HTTPException(status_code=500, detail="Converted DICOM bundle is missing.")
    return FileResponse(
        bundle_path,
        media_type="application/zip",
        filename=f"cubon3-dicom-{job_id[:8]}.zip",
    )


@app.get("/api/dicom/jobs/{job_id}/slices/{slice_index}")
def view_dicom_slice(job_id: str, slice_index: int):
    try:
        job_dir = get_job_dir(job_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    job = get_dicom_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="DICOM import job not found.")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="DICOM image conversion is not complete.")
    if slice_index < 1 or slice_index > job["slices"]:
        raise HTTPException(status_code=404, detail="Converted image slice not found.")

    image_path = job_dir / "slices" / f"slice_{slice_index:05d}.png"
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Converted image slice not found.")
    return FileResponse(image_path, media_type="image/png")


@app.post("/api/dicom/jobs/{job_id}/aholo")
def generate_from_dicom_slice(job_id: str, slice_index: int = Query(..., ge=1)):
    try:
        job_dir = get_job_dir(job_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    job = get_dicom_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="DICOM import job not found.")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="DICOM image conversion is not complete.")
    if slice_index > job["slices"]:
        raise HTTPException(status_code=404, detail="Converted image slice not found.")

    image_path = job_dir / "slices" / f"slice_{slice_index:05d}.png"
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Converted image slice not found.")
    try:
        task = submit_aholo_task(
            image_path,
            f"Aholo from DICOM {job_id[:8]} · slice {slice_index}",
        )
        return {**task, "input_format": "lossless PNG", "source_slice": slice_index}
    except Exception as error:
        print("Aholo submission error:", repr(error))
        raise HTTPException(
            status_code=502,
            detail="Aholo could not submit the converted image.",
        )


@app.delete("/api/dicom/jobs/{job_id}")
def delete_dicom_import(job_id: str):
    try:
        job_dir = get_job_dir(job_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    job = get_dicom_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="DICOM import job not found.")
    if job["status"] in {"queued", "processing"}:
        raise HTTPException(status_code=409, detail="Wait for conversion to finish before deleting it.")

    if job_dir.exists():
        shutil.rmtree(job_dir)
    delete_dicom_job(job_id)
    return {"job_id": job_id, "deleted": True}
