
import os
import requests
from pathlib import Path

from dotenv import load_dotenv
from manycore.aholo_sdk_core import AholoClientConfig
from manycore.aholo_sdk_lux3d import create_lux3d_client

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent



def get_aholo_client():
    api_key = os.getenv("AHOLO_API_KEY")

    if not api_key:
        raise ValueError("AHOLO_API_KEY is missing from .env")

    config = AholoClientConfig(
        api_key=api_key,
        region="com",
        timeout_ms=60000,
    )

    return create_lux3d_client(config)


def create_3d_task(image_path):
    client = get_aholo_client()

    image_path = Path(image_path)

    if not image_path.exists():
        raise ValueError(f"Image file not found: {image_path}")

    task_id = client.img_to_3d.create_from_file(
        str(image_path),
        version="G1",
        face_count=300000,
        output_format=["glb"],
    )

    return {
        "task_id": task_id,
        "status": "submitted",
        "image": image_path.name,
    }


def get_3d_task(task_id: int):
    client = get_aholo_client()

    result = client.tasks.retrieve(task_id)

    return dict(result)

def download_generated_model(task_id: int):
    client = get_aholo_client()
    result = client.tasks.retrieve(task_id)

    if result.get("status") != 3:
        raise ValueError("3D generation has not completed successfully.")

    outputs = result.get("outputs", [])

    glb_url = next(
        (
            output.get("content")
            for output in outputs
            if output.get("content", "").split("?")[0].lower().endswith(".glb")
        ),
        None,
    )

    if not glb_url:
        raise ValueError("No GLB output was found.")

    output_dir = BASE_DIR / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"task_{task_id}.glb"

    response = requests.get(glb_url, timeout=120)
    response.raise_for_status()

    if not response.content:
        raise ValueError("Downloaded GLB file is empty.")

    output_path.write_bytes(response.content)

    return {
        "task_id": task_id,
        "file": output_path.name,
        "size_bytes": output_path.stat().st_size,
        "status": "downloaded",
    }
