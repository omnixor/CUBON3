import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin

import main
from services.cloudflare_ai_service import (
    AIProviderNotConfigured,
    UnsupportedScanImage,
    generate_image_report,
)


def make_png():
    image = Image.new("RGB", (2, 2), color=(60, 90, 120))
    output = io.BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("PatientName", "test-only-metadata")
    image.save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


def test_report_requires_backend_cloudflare_credentials(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)

    with pytest.raises(AIProviderNotConfigured):
        generate_image_report(make_png(), "image/png")


def test_report_sends_normalized_image_and_returns_provider_text(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"success": True, "result": {"response": "A general visual summary."}}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("services.cloudflare_ai_service.requests.post", fake_post)

    result = generate_image_report(make_png(), "image/png")

    assert result == "A general visual summary."
    assert captured["url"].endswith(
        "/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
    )
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    image_uri = captured["json"]["messages"][1]["content"][1]["image_url"]["url"]
    encoded_image = image_uri.split(",", 1)[1]
    normalized = Image.open(io.BytesIO(base64.b64decode(encoded_image)))
    assert normalized.format == "PNG"
    assert "PatientName" not in normalized.info
    assert captured["json"]["messages"][0]["role"] == "system"
    assert captured["json"]["messages"][1]["content"][1]["type"] == "image_url"
    assert "generated 3D model preview" in (
        captured["json"]["messages"][1]["content"][0]["text"]
    )


def test_report_rejects_mismatched_image_type_before_provider_call(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setattr(
        "services.cloudflare_ai_service.requests.post",
        lambda *args, **kwargs: pytest.fail("Provider should not be called"),
    )

    with pytest.raises(UnsupportedScanImage):
        generate_image_report(make_png(), "image/jpeg")


def test_report_requires_explicit_external_transfer_consent():
    client = TestClient(main.app)
    response = client.post(
        "/api/analysis/report",
        data={"consent": "false"},
        files={"file": ("scan.png", make_png(), "image/png")},
    )

    assert response.status_code == 400
    assert "consent" in response.json()["detail"].lower()


def test_report_endpoint_explains_missing_provider_configuration(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    client = TestClient(main.app)
    response = client.post(
        "/api/analysis/report",
        data={"consent": "true"},
        files={"file": ("scan.png", make_png(), "image/png")},
    )

    assert response.status_code == 503
    assert "CLOUDFLARE_ACCOUNT_ID" in response.json()["detail"]
