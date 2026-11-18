
import os

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from services.aholo_service import (
    create_3d_task,
    get_3d_task,
)

load_dotenv()

app = FastAPI(
    title="ScanSpace 3D",
    description="AI-powered medical imaging backend",
    version="1.0.0",
)
GENERATED_DIR = Path(__file__).resolve().parent / "generated"

app.mount(
    "/models",
    StaticFiles(directory=GENERATED_DIR),
    name="models",
)

@app.get("/")
def home():
    return {
        "message": "Welcome to ScanSpace 3D!",
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

    try:
        suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        return create_3d_task(temp_path)

    except Exception as error:
        print("Generation error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="3D generation request failed",
        )

    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()

        await file.close()



@app.get("/api/aholo/task/{task_id}")
def check_3d_task(task_id: int):
    try:
        return get_3d_task(task_id)

    except Exception as error:
        print("Task retrieval error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Task status retrieval failed",
        )
from services.aholo_service import (
    create_3d_task,
    get_3d_task,
    download_generated_model,
)

@app.post("/api/aholo/task/{task_id}/download")
def download_3d_model(task_id: int):
    try:
        return download_generated_model(task_id)

    except Exception as error:
        print("Download error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="3D model download failed",
        )
