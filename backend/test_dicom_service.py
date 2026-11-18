import io
import json
import uuid
import zipfile

import numpy as np
import pydicom
import nibabel as nib
from fastapi.testclient import TestClient
from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

import database
from main import app
from services import dicom_service


def write_ct_slice(path, pixels, z_position, series_uid, modality="CT"):
    sop_instance_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = CTImageStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = series_uid
    dataset.Modality = modality
    dataset.InstanceNumber = int(z_position[2] if isinstance(z_position, list) else z_position) + 1
    dataset.ImagePositionPatient = (
        z_position if isinstance(z_position, list) else [0, 0, z_position]
    )
    dataset.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    dataset.PixelSpacing = [0.7, 0.7]
    dataset.SliceThickness = 1
    dataset.Rows = 2
    dataset.Columns = 2
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 1
    dataset.RescaleSlope = 1
    dataset.RescaleIntercept = -1024
    dataset.PixelData = np.asarray(pixels, dtype="<i2").tobytes()
    dataset.save_as(path, enforce_file_format=True)


def test_dicom_conversion_preserves_signed_pixels_and_slice_order(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "cubon3.db")
    monkeypatch.setattr(dicom_service, "DATA_DIR", tmp_path / "dicom_data")
    database.init_db()

    job_id = str(uuid.uuid4())
    job_dir = dicom_service.get_job_dir(job_id)
    source_dir = job_dir / "source"
    source_dir.mkdir(parents=True)
    series_uid = generate_uid()
    first_pixels = np.array([[-32768, -1], [0, 32767]], dtype=np.int16)
    second_pixels = np.array([[-1000, -10], [10, 1000]], dtype=np.int16)

    write_ct_slice(source_dir / "source_00001.dcm", second_pixels, [0.25, 0, 1], series_uid)
    write_ct_slice(source_dir / "source_00002.dcm", first_pixels, 0, series_uid)
    database.create_dicom_job(job_id, "CT series test", 2)

    dicom_service.process_dicom_job(job_id)

    job = database.get_dicom_job(job_id)
    assert job["status"] == "completed"
    assert job["slices"] == 2
    assert job["stage"] == "completed"

    volume = nib.load(job_dir / "ct_volume.nii.gz")
    np.testing.assert_array_equal(volume.shape, (2, 2, 2))
    assert float(volume.dataobj[0, 0, 0]) == -33792
    assert np.isclose(volume.affine[0, 1], -0.7)
    assert np.isclose(volume.affine[1, 0], -0.7)
    assert np.isclose(volume.affine[0, 2], -0.25)
    assert np.isclose(volume.affine[2, 2], 1.0)

    manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
    assert [float(item["position"][2]) for item in manifest["slices"]] == [0.0, 1.0]

    sidecar = json.loads(
        (job_dir / "slices" / "slice_00001.json").read_text(encoding="utf-8")
    )
    converted = np.asarray(Image.open(job_dir / "slices" / "slice_00001.png"))
    restored = converted.astype(np.int32) + sidecar["png_to_stored_value_offset"]
    np.testing.assert_array_equal(restored, first_pixels)

    with zipfile.ZipFile(job_dir / "converted-series.zip") as bundle:
        assert "source/source_00001.dcm" in bundle.namelist()
        assert "slices/slice_00001.png" in bundle.namelist()
        assert "volume/ct_volume.nii.gz" in bundle.namelist()
        assert "manifest.json" in bundle.namelist()


def test_single_xray_dicom_is_converted_without_volume_reconstruction(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "xray.db")
    monkeypatch.setattr(dicom_service, "DATA_DIR", tmp_path / "xray_data")
    database.init_db()

    job_id = str(uuid.uuid4())
    job_dir = dicom_service.get_job_dir(job_id)
    source_dir = job_dir / "source"
    source_dir.mkdir(parents=True)
    write_ct_slice(
        source_dir / "radiograph.dcm",
        np.array([[0, 100], [500, 1000]], dtype=np.int16),
        0,
        generate_uid(),
        modality="DX",
    )
    database.create_dicom_job(job_id, "X-ray test", 1)

    dicom_service.process_dicom_job(job_id)

    job = database.get_dicom_job(job_id)
    assert job["status"] == "completed"
    assert job["slices"] == 1
    manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["modality"] == "DX"
    assert manifest["volume"] is None
    assert (job_dir / "slices" / "slice_00001.png").is_file()


def test_dicom_import_runs_as_background_job_and_serves_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "cubon3-api.db")
    monkeypatch.setattr(dicom_service, "DATA_DIR", tmp_path / "dicom_api")
    database.init_db()

    sample_path = tmp_path / "sample.dcm"
    second_path = tmp_path / "sample_second.dcm"
    series_uid = generate_uid()
    pixels = np.array([[-32, -1], [1, 32]], dtype=np.int16)
    write_ct_slice(sample_path, pixels, 0, series_uid)
    write_ct_slice(second_path, pixels, 1, series_uid)
    monkeypatch.setattr(
        "main.create_3d_task",
        lambda image_path: {"task_id": 99001, "status": "submitted"},
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/dicom/import",
            files=[
                ("files", ("sample.dcm", io.BytesIO(sample_path.read_bytes()), "application/dicom")),
                ("files", ("sample_second.dcm", io.BytesIO(second_path.read_bytes()), "application/dicom")),
            ],
        )
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        status = client.get(f"/api/dicom/jobs/{job_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "completed"
        assert status.json()["slices"] == 2

        image = client.get(f"/api/dicom/jobs/{job_id}/slices/1")
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/png"

        aholo_task = client.post(
            f"/api/dicom/jobs/{job_id}/aholo",
            params={"slice_index": 1},
        )
        assert aholo_task.status_code == 200
        assert aholo_task.json()["provider_task_id"] == 99001
        assert aholo_task.json()["source_slice"] == 1

        bundle = client.get(f"/api/dicom/jobs/{job_id}/bundle")
        assert bundle.status_code == 200
        with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
            assert "slices/slice_00001.png" in archive.namelist()
            assert "volume/ct_volume.nii.gz" in archive.namelist()

        deleted = client.delete(f"/api/dicom/jobs/{job_id}")
        assert deleted.status_code == 200
        assert not dicom_service.get_job_dir(job_id).exists()
        assert database.get_dicom_job(job_id) is None


def test_image_upload_is_normalized_to_png_before_aholo(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "image.db")
    database.init_db()
    pixels = np.array([[0, 32768], [65535, 1024]], dtype=np.uint16)
    image_bytes = io.BytesIO()
    Image.fromarray(pixels).save(image_bytes, format="PNG")

    def fake_create_3d_task(image_path):
        assert str(image_path).lower().endswith(".png")
        with Image.open(image_path) as normalized:
            assert normalized.format == "PNG"
            np.testing.assert_array_equal(np.asarray(normalized), pixels)
        return {"task_id": 99002, "status": "submitted"}

    monkeypatch.setattr("main.create_3d_task", fake_create_3d_task)
    image_bytes.seek(0)

    with TestClient(app) as client:
        response = client.post(
            "/api/aholo/generate",
            files={"file": ("ct_slice.png", image_bytes, "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["provider_task_id"] == 99002
    assert response.json()["input_format"] == "lossless PNG"
