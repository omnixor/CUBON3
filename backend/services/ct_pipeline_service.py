from pathlib import Path

import nibabel as nib
import numpy as np
import pydicom
from pydicom.pixels import apply_modality_lut


BONE_CLASSES = [
    "skull",
    "sacrum",
    "vertebrae_S1",
    *[f"vertebrae_{level}{number}" for level, count in (("C", 7), ("T", 12), ("L", 5))
      for number in range(1, count + 1)],
    *[f"rib_{side}_{number}" for side in ("left", "right") for number in range(1, 13)],
    "humerus_left",
    "humerus_right",
    "scapula_left",
    "scapula_right",
    "clavicula_left",
    "clavicula_right",
    "femur_left",
    "femur_right",
    "hip_left",
    "hip_right",
    "sternum",
    "costal_cartilages",
]

def build_ct_volume(headers: list[tuple[Path, object]], output_path: Path) -> dict:
    if len(headers) < 2:
        raise ValueError("At least two CT slices are required to reconstruct a 3D volume.")

    first_dataset = headers[0][1]
    rows = int(first_dataset.Rows)
    columns = int(first_dataset.Columns)
    orientation = np.asarray(first_dataset.ImageOrientationPatient, dtype=np.float64)
    if not np.isfinite(orientation).all():
        raise ValueError("The CT series has invalid image orientation metadata.")
    row_direction = orientation[:3]
    column_direction = orientation[3:]
    row_norm = np.linalg.norm(row_direction)
    column_norm = np.linalg.norm(column_direction)
    if row_norm == 0 or column_norm == 0:
        raise ValueError("The CT series has invalid image orientation metadata.")
    row_direction /= row_norm
    column_direction /= column_norm
    if abs(float(np.dot(row_direction, column_direction))) > 1e-4:
        raise ValueError("The CT series has invalid image orientation metadata.")

    normal = np.cross(row_direction, column_direction)
    normal /= np.linalg.norm(normal)
    pixel_spacing = np.asarray(first_dataset.PixelSpacing, dtype=np.float64)
    if not np.isfinite(pixel_spacing).all() or np.any(pixel_spacing <= 0):
        raise ValueError("The CT series has invalid pixel spacing.")
    positions = []
    for _, dataset in headers:
        if int(dataset.Rows) != rows or int(dataset.Columns) != columns:
            raise ValueError("All CT slices must have matching rows and columns.")
        if not np.allclose(
            np.asarray(dataset.ImageOrientationPatient, dtype=np.float64),
            orientation,
            atol=1e-5,
        ):
            raise ValueError("The CT series contains inconsistent image orientations.")
        if not np.allclose(
            np.asarray(dataset.PixelSpacing, dtype=np.float64),
            pixel_spacing,
            atol=1e-4,
        ):
            raise ValueError("The CT series contains inconsistent pixel spacing.")
        position = np.asarray(dataset.ImagePositionPatient, dtype=np.float64)
        if position.shape != (3,) or not np.isfinite(position).all():
            raise ValueError("The CT series has invalid slice position metadata.")
        positions.append(position)

    position_steps = np.diff(np.asarray(positions), axis=0)
    differences = position_steps @ normal
    if np.any(differences <= 0):
        raise ValueError("CT slice positions must be unique and sorted in physical space.")
    slice_spacing = float(np.median(differences))
    if not np.allclose(differences, slice_spacing, rtol=0.02, atol=0.1):
        raise ValueError("Non-uniformly spaced CT slices cannot be combined into one regular volume.")
    slice_step = np.mean(position_steps, axis=0)
    if not np.allclose(position_steps, slice_step, rtol=0.02, atol=0.1):
        raise ValueError("Non-uniformly positioned CT slices cannot be combined into one regular volume.")

    raw_path = output_path.with_suffix(".raw")
    volume = np.memmap(
        raw_path,
        dtype=np.float32,
        mode="w+",
        shape=(rows, columns, len(headers)),
    )
    image = None
    try:
        for slice_index, (path, _) in enumerate(headers):
            dataset = pydicom.dcmread(path)
            pixels = np.asarray(dataset.pixel_array)
            if pixels.shape != (rows, columns):
                raise ValueError("Every CT file must contain one matching 2D image frame.")
            modality_pixels = apply_modality_lut(pixels, dataset)
            volume[:, :, slice_index] = np.asarray(modality_pixels, dtype=np.float32)
        volume.flush()

        affine_lps = np.eye(4, dtype=np.float64)
        affine_lps[:3, 0] = column_direction * pixel_spacing[0]
        affine_lps[:3, 1] = row_direction * pixel_spacing[1]
        affine_lps[:3, 2] = slice_step
        affine_lps[:3, 3] = positions[0]
        lps_to_ras = np.diag([-1.0, -1.0, 1.0, 1.0])
        affine_ras = lps_to_ras @ affine_lps

        image = nib.Nifti1Image(volume, affine_ras)
        image.header.set_xyzt_units("mm")
        image.header.set_data_dtype(np.float32)
        nib.save(image, output_path)
    finally:
        del image
        volume.flush()
        volume._mmap.close()
        del volume
        raw_path.unlink(missing_ok=True)

    return {
        "volume": output_path.name,
        "shape": [rows, columns, len(headers)],
        "spacing_mm": [
            float(pixel_spacing[0]),
            float(pixel_spacing[1]),
            slice_spacing,
        ],
        "affine_ras": affine_ras.tolist(),
        "intensity_values": "DICOM modality LUT/rescale values (typically Hounsfield units)",
    }
