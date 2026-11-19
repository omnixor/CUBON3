import base64
import os
from io import BytesIO

import requests
from PIL import Image, ImageOps, UnidentifiedImageError


MODEL_ID = "@cf/meta/llama-3.2-11b-vision-instruct"
ALLOWED_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


class AIProviderNotConfigured(RuntimeError):
    pass


class AIProviderError(RuntimeError):
    pass


class UnsupportedScanImage(ValueError):
    pass


def _normalize_image(image_bytes: bytes, content_type: str) -> bytes:
    expected_format = ALLOWED_FORMATS.get(content_type)
    if not expected_format:
        raise UnsupportedScanImage(
            "Only JPEG, PNG, or WebP model preview images are supported."
        )
    if not image_bytes:
        raise UnsupportedScanImage("The uploaded image is empty.")

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            if source.format != expected_format:
                raise UnsupportedScanImage("The uploaded image format does not match its content type.")
            if source.width * source.height > 100_000_000:
                raise UnsupportedScanImage("Image dimensions exceed the supported limit.")
            source.load()
            image = ImageOps.exif_transpose(source)

            if image.mode in {"L", "RGB", "RGBA", "I;16", "I;16B", "I;16L"}:
                normalized = image.copy()
            elif image.mode == "I":
                minimum, maximum = image.getextrema()
                if minimum < 0 or maximum > 65535:
                    raise UnsupportedScanImage(
                        "The image pixel values cannot be represented in PNG."
                    )
                normalized = image.convert("I;16")
            elif "A" in image.getbands():
                normalized = image.convert("RGBA")
            else:
                normalized = image.convert("RGB")

            output = BytesIO()
            normalized.save(output, format="PNG", compress_level=6)
            return output.getvalue()
    except UnsupportedScanImage:
        raise
    except (UnidentifiedImageError, OSError) as error:
        raise UnsupportedScanImage("The uploaded file is not a supported image.") from error


def generate_image_report(image_bytes: bytes, content_type: str) -> str:
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_token:
        raise AIProviderNotConfigured(
            "Configure CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN on the backend."
        )

    normalized_image = _normalize_image(image_bytes, content_type)
    image_data_uri = (
        "data:image/png;base64,"
        + base64.b64encode(normalized_image).decode("ascii")
    )
    endpoint = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/{MODEL_ID}"
    )
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are describing a screenshot of a computer-rendered 3D model. "
                    "Describe only visible shape, silhouette, components, surface detail, "
                    "and rendering quality. Do not infer hidden geometry, exact dimensions, "
                    "anatomy, disease, fracture, or other medical findings. Do not recommend "
                    "treatment. Make clear that you see one rendered view, not the full model "
                    "or original scan. Avoid generic filler. Keep the report under 120 words "
                    "and use the headings Overview, Visible details, and Limits."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Write a concise, useful visual summary of this generated 3D "
                            "model preview. Distinguish visible details from uncertainty."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_uri},
                    },
                ],
            },
        ],
        "max_tokens": 512,
        "temperature": 0.1,
    }

    try:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_token}"},
            json=payload,
            timeout=(10, 90),
        )
    except requests.RequestException as error:
        raise AIProviderError("Cloudflare Workers AI could not be reached.") from error

    if response.status_code == 429:
        raise AIProviderError("Cloudflare Workers AI rate limit or free-tier quota was reached.")
    if response.status_code in {401, 403}:
        raise AIProviderError(
            "Cloudflare rejected the request. Check the API token and accept the model license."
        )
    if response.status_code == 400:
        raise AIProviderError(
            "Cloudflare rejected the image request. Check the model license and image format."
        )
    if response.status_code >= 400:
        raise AIProviderError(
            f"Cloudflare Workers AI returned HTTP {response.status_code}."
        )

    try:
        body = response.json()
    except ValueError as error:
        raise AIProviderError("Cloudflare Workers AI returned an invalid response.") from error

    if not isinstance(body, dict):
        raise AIProviderError("Cloudflare Workers AI returned an invalid response.")
    result = body.get("result")
    if isinstance(result, dict):
        report = result.get("response") or result.get("text")
    else:
        report = result
    if not isinstance(report, str) or not report.strip():
        raise AIProviderError("Cloudflare Workers AI returned no report text.")

    return report.strip()
