import json
import logging
import uuid
import zipfile
from pathlib import Path

import numpy as np
import pydicom
from PIL import Image
from pydicom.errors import InvalidDicomError

from database import update_dicom_job
from services.ct_pipeline_service import build_ct_volume


LOGGER = logging.getLogger(__name__)
DATA_DIR = Path(__file__).resolve().parent.parent / "dicom_data"


def get_job_dir(job_id: str) -> Path:
    try:
        normalized_id = str(uuid.UUID(job_id))
    except ValueError as error:
        raise ValueError("Invalid DICOM job ID.") from error
    return DATA_DIR / normalized_id


def process_dicom_job(job_id: str) -> None:
    job_dir = get_job_dir(job_id)
    source_dir = job_dir / "source"
    slices_dir = job_dir / "slices"
    bundle_path = job_dir / "converted-series.zip"

    update_dicom_job(job_id, "processing", stage="validating_series")
    try:
        source_paths = sorted(source_dir.glob("*.dcm"))
        if not source_paths:
            raise ValueError("The uploaded series contains no DICOM files.")

        headers = []
        series_uids = set()
        modalities = set()
        for path in source_paths:
            try:
                dataset = pydicom.dcmread(path, stop_before_pixels=True)
            except InvalidDicomError as error:
                raise ValueError("One or more uploaded files are not valid DICOM files.") from error

            if int(getattr(dataset, "SamplesPerPixel", 1)) != 1:
                raise ValueError("Color DICOM images are not supported; upload a grayscale series.")
            if int(getattr(dataset, "NumberOfFrames", 1)) != 1:
                raise ValueError("Multi-frame DICOM images are not supported yet.")

            series_uid = str(getattr(dataset, "SeriesInstanceUID", ""))
            if not series_uid:
                raise ValueError("A DICOM file is missing its Series Instance UID.")
            series_uids.add(series_uid)
            modalities.add(str(getattr(dataset, "Modality", "OT")).upper())
            headers.append((path, dataset))

        if len(series_uids) != 1:
            raise ValueError("Upload files from exactly one DICOM series at a time.")
        if len(modalities) != 1:
            raise ValueError("Upload images from only one DICOM modality at a time.")

        modality = next(iter(modalities))
        volume_info = None
        if modality == "CT" and len(headers) > 1:
            if not all(
                all(
                    hasattr(header, attribute)
                    for attribute in (
                        "ImagePositionPatient",
                        "ImageOrientationPatient",
                        "PixelSpacing",
                    )
                )
                for _, header in headers
            ):
                raise ValueError("CT series must include position, orientation, and pixel-spacing metadata.")

            orientation = headers[0][1].ImageOrientationPatient
            row = np.asarray(orientation[:3], dtype=np.float64)
            column = np.asarray(orientation[3:], dtype=np.float64)
            normal = np.cross(row, column)
            reference = np.asarray(orientation, dtype=np.float64)
            for _, header in headers:
                if not np.allclose(
                    np.asarray(header.ImageOrientationPatient, dtype=np.float64),
                    reference,
                    atol=1e-5,
                ):
                    raise ValueError("The CT series contains inconsistent image orientations.")

            headers.sort(
                key=lambda item: float(
                    np.dot(
                        np.asarray(item[1].ImagePositionPatient, dtype=np.float64),
                        normal,
                    )
                )
            )
            update_dicom_job(job_id, "processing", stage="volume_reconstruction")
            volume_path = job_dir / "ct_volume.nii.gz"
            volume_info = build_ct_volume(headers, volume_path)
        elif all(getattr(header, "InstanceNumber", None) is not None for _, header in headers):
            headers.sort(key=lambda item: float(item[1].InstanceNumber))
        else:
            headers.sort(key=lambda item: item[0].name)

        update_dicom_job(job_id, "processing", stage="image_conversion")
        slices_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "job_id": job_id,
            "modality": modality,
            "source_files": len(headers),
            "volume": volume_info,
            "slices": [],
            "pixel_values": (
                "PNG values preserve decoded stored pixel values. "
                "For signed data, add the recorded offset to recover the stored value. "
                "Apply DICOM rescale slope/intercept and display windowing separately."
            ),
            "source_compression_note": (
                "The source DICOM files are included unchanged. If a source file used "
                "lossy compression, exporting PNG cannot restore information already lost."
            ),
        }

        for index, (source_path, _) in enumerate(headers, start=1):
            dataset = pydicom.dcmread(source_path)
            pixels = np.asarray(dataset.pixel_array)
            if pixels.ndim != 2:
                raise ValueError("Each uploaded DICOM file must contain one 2D image frame.")

            bits_allocated = int(dataset.BitsAllocated)
            bits_stored = int(dataset.BitsStored)
            if bits_allocated not in (8, 16) or not 1 <= bits_stored <= bits_allocated:
                raise ValueError("Only 8-bit and 16-bit integer CT pixels are supported.")

            signed = int(dataset.PixelRepresentation) == 1
            offset = 1 << (bits_stored - 1) if signed else 0
            png_pixels = pixels.astype(np.int32) + offset
            if png_pixels.min() < 0 or png_pixels.max() > 65535:
                raise ValueError("Pixel values cannot be represented losslessly in a 16-bit PNG.")

            filename = f"slice_{index:05d}.png"
            Image.fromarray(png_pixels.astype(np.uint16)).save(
                slices_dir / filename,
                format="PNG",
                compress_level=6,
            )
            sidecar = {
                "source_file": source_path.name,
                "instance_number": getattr(dataset, "InstanceNumber", None),
                "rows": int(dataset.Rows),
                "columns": int(dataset.Columns),
                "bits_allocated": bits_allocated,
                "bits_stored": bits_stored,
                "pixel_representation": "signed" if signed else "unsigned",
                "png_to_stored_value_offset": -offset,
                "photometric_interpretation": str(
                    getattr(dataset, "PhotometricInterpretation", "MONOCHROME2")
                ),
                "rescale_slope": float(getattr(dataset, "RescaleSlope", 1)),
                "rescale_intercept": float(getattr(dataset, "RescaleIntercept", 0)),
                "pixel_spacing": list(getattr(dataset, "PixelSpacing", [])),
                "image_position_patient": list(
                    getattr(dataset, "ImagePositionPatient", [])
                ),
                "image_orientation_patient": list(
                    getattr(dataset, "ImageOrientationPatient", [])
                ),
                "slice_thickness": getattr(dataset, "SliceThickness", None),
                "transfer_syntax_uid": str(
                    getattr(getattr(dataset, "file_meta", None), "TransferSyntaxUID", "unknown")
                ),
                "lossy_image_compression": str(
                    getattr(dataset, "LossyImageCompression", "00")
                ),
            }
            sidecar_name = f"slice_{index:05d}.json"
            (slices_dir / sidecar_name).write_text(
                json.dumps(sidecar, indent=2),
                encoding="utf-8",
            )
            manifest["slices"].append(
                {
                    "image": filename,
                    "metadata": sidecar_name,
                    "position": sidecar["image_position_patient"],
                }
            )

        update_dicom_job(
            job_id,
            "processing",
            slices=len(headers),
            stage="bundling_images",
        )
        (job_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        with zipfile.ZipFile(
            bundle_path,
            "w",
            compression=zipfile.ZIP_STORED,
        ) as bundle:
            for path in source_paths:
                bundle.write(path, f"source/{path.name}")
            bundle.write(job_dir / "manifest.json", "manifest.json")
            for path in sorted(slices_dir.iterdir()):
                bundle.write(path, f"slices/{path.name}")
            if volume_info:
                bundle.write(job_dir / "ct_volume.nii.gz", "volume/ct_volume.nii.gz")

        update_dicom_job(
            job_id,
            "completed",
            slices=len(headers),
            bundle_size=bundle_path.stat().st_size,
            stage="completed",
        )
    except Exception as error:
        LOGGER.exception("DICOM import failed for job %s", job_id)
        update_dicom_job(
            job_id,
            "failed",
            error=str(error)[:500],
            stage="failed",
        )
