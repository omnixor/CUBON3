
import os
import requests
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from PIL import Image, ImageOps, UnidentifiedImageError
from manycore.aholo_sdk_core import AholoClientConfig
from manycore.aholo_sdk_lux3d import create_lux3d_client

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def normalize_image_to_png(source_path: str | Path, output_path: str | Path) -> None:
    try:
        with Image.open(source_path) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Only JPEG, PNG, and WebP images are supported.")
            if source.width * source.height > 100_000_000:
                raise ValueError("Image dimensions exceed the supported limit.")
            source.load()
            image = ImageOps.exif_transpose(source)

            if image.mode in {"L", "RGB", "RGBA", "I;16", "I;16B", "I;16L"}:
                normalized = image.copy()
            elif image.mode == "I":
                minimum, maximum = image.getextrema()
                if minimum < 0 or maximum > 65535:
                    raise ValueError("The image pixel values cannot be represented losslessly in PNG.")
                normalized = image.convert("I;16")
            elif "A" in image.getbands():
                normalized = image.convert("RGBA")
            else:
                normalized = image.convert("RGB")

            normalized.save(output_path, format="PNG", compress_level=6)
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("The uploaded file is not a supported image.") from error



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

    parsed_url = urlparse(glb_url)
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("The provider returned an invalid GLB URL.")

    output_dir = BASE_DIR / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"task_{task_id}.glb"

    response = requests.get(glb_url, timeout=120)
    response.raise_for_status()

    if not response.content:
        raise ValueError("Downloaded GLB file is empty.")

    if len(response.content) > 500 * 1024 * 1024:
        raise ValueError("Downloaded GLB file exceeds the 500 MB limit.")

    temporary_path = output_path.with_suffix(".glb.tmp")
    temporary_path.write_bytes(response.content)
    temporary_path.replace(output_path)

    return {
        "task_id": task_id,
        "file": output_path.name,
        "size_bytes": output_path.stat().st_size,
        "status": "downloaded",
    }
