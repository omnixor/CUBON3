# CUBON3

CUBON3 is a browser-based medical imaging workspace for preparing CT/DICOM
images and generating interactive 3D models with Aholo Lux3D.

> **Prototype:** This project is for research and visualization only. It is not
> clinically validated and must not be used for diagnosis or treatment.

## What it does

- Accepts JPEG, PNG, and WebP images, normalizes them to PNG, and submits them to
  Aholo for 3D generation.
- Accepts a single-frame grayscale DICOM series, exports PNG slices with
  metadata, and reconstructs a spatial NIfTI volume for eligible multi-slice CT
  series.
- Lets users choose a converted DICOM slice to submit to Aholo.
- Tracks generation tasks with a status-based progress estimate, lists projects,
  and displays or downloads GLB models. Aholo does not provide an exact
  percentage.
- Packages the original DICOM files and converted data into a downloadable ZIP.

### Workflow limitations

Aholo's integration in this project accepts a 2D image, not a complete CT
volume. For DICOM, only the selected slice is submitted; the generated model is
not a 3D reconstruction of the entire scan. Re-encoding a lossy source as PNG
cannot restore information already lost in the source.

## Repository layout

```text
CUBON3/
|-- backend/
|   |-- main.py
|   |-- database.py
|   |-- requirements.txt
|   |-- services/
|   |   |-- __init__.py
|   |   |-- aholo_service.py
|   |   |-- ct_pipeline_service.py
|   |   `-- dicom_service.py
|   |-- generated/                (local GLB output)
|   |-- test_database.py
|   `-- test_dicom_service.py
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- services/
|   |   |-- styles/
|   |   |-- App.jsx
|   |   `-- main.jsx
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   `-- vite.config.js
|-- .github/workflows/ci.yml
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- docker-compose.yml
|-- LICENSE
`-- README.md
```

Local runtime data is kept separate from source code and ignored by Git:

- `backend/cubon3.db` — local SQLite database.
- `backend/dicom_data/` — uploaded DICOM files, slices, and bundles.
- `frontend/node_modules/` and `frontend/dist/` — installed packages and build
  output.
- `.env` — local credentials and configuration; create it from `.env.example`.

## Requirements

- Python 3.12
- Node.js 22 and npm
- An Aholo API key for image-to-3D generation
- Docker and Docker Compose (optional)

## Run locally

### 1. Configure the backend

From the repository root, create and activate a virtual environment, then
install the backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set your own `AHOLO_API_KEY`. Keep `.env` private; it is ignored
by Git.

Start the API from the repository root:

```powershell
python -m uvicorn main:app --reload --app-dir backend
```

The backend runs at `http://127.0.0.1:8000`. Interactive API documentation is
available at `http://127.0.0.1:8000/docs`.

### 2. Start the frontend

In a second terminal:

```powershell
cd frontend
npm ci
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

Open the Vite URL printed in the terminal (normally
`http://127.0.0.1:5173`).

For macOS/Linux, activate the virtual environment with
`source .venv/bin/activate`; set the frontend URL with
`VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev`.

## Docker

The Compose setup runs the **backend only**. Create `.env` as described above,
then run from the repository root:

```powershell
docker compose up --build
```

The API is exposed on port `8000`. Start the frontend separately using the
instructions above. The Compose file uses named volumes for the database,
generated models, and DICOM data.

## Configuration

| Variable | Used by | Default | Description |
|---|---|---|---|
| `AHOLO_API_KEY` | Backend | — | Aholo API key; required for generation. |
| `CORS_ORIGINS` | Backend | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed frontend origins. |
| `MAX_UPLOAD_MB` | Backend | `10` | Maximum raster image upload size. |
| `MAX_DICOM_UPLOAD_MB` | Backend | `1024` | Maximum total size of a DICOM upload. |
| `CUBON3_DB_PATH` | Backend | `backend/cubon3.db` | Optional SQLite database path. |
| `VITE_API_BASE_URL` | Frontend | `http://127.0.0.1:8000` | Backend URL used by the browser app. |

For a hosted setup, deploy the backend separately, set `CORS_ORIGINS` to the
frontend's exact origin, and set `VITE_API_BASE_URL` to the deployed API URL.
This repository does not deploy or host the application.

## DICOM support and data handling

- Upload files from exactly one series at a time (up to 2,000 files per upload).
- Multi-frame and color DICOM are not supported.
- Multi-slice CT volume reconstruction requires consistent spatial metadata
  and slice spacing. The volume uses DICOM modality LUT/rescale values.
- Converted PNG slices preserve decoded stored pixel values; sidecar metadata
  records the offset needed to recover signed values.
- Compressed transfer syntaxes depend on the installed pydicom decoders.
- Uploaded data remains on the backend until deleted. The application has no
  user authentication or production medical-data security controls.

Use only de-identified data. Do not expose this prototype publicly or upload
identifiable patient information. Before any real-patient use, add appropriate
authentication, authorization, encrypted transport and storage, retention
controls, and privacy/compliance review.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Backend status. |
| `GET` | `/api/health` | Health and Aholo-key configuration check. |
| `POST` | `/api/aholo/generate` | Normalize and submit a raster image. |
| `GET` | `/api/aholo/task/{task_id}` | Retrieve a generation task's status. |
| `POST` | `/api/aholo/task/{task_id}/download` | Download a generated GLB. |
| `GET` | `/api/projects` | List saved generation tasks. |
| `DELETE` | `/api/projects/{task_id}` | Delete a project and its downloaded model. |
| `POST` | `/api/dicom/import` | Start a DICOM conversion job. |
| `GET` | `/api/dicom/jobs` | List recent DICOM jobs. |
| `GET` | `/api/dicom/jobs/{job_id}` | Get a DICOM job's status. |
| `GET` | `/api/dicom/jobs/{job_id}/slices/{slice_index}` | Preview a converted slice. |
| `POST` | `/api/dicom/jobs/{job_id}/aholo?slice_index={n}` | Submit one converted slice to Aholo. |
| `GET` | `/api/dicom/jobs/{job_id}/bundle` | Download the source and converted data bundle. |
| `DELETE` | `/api/dicom/jobs/{job_id}` | Delete a DICOM job and its stored files. |
| `GET` | `/models/{filename}` | Serve a generated GLB model. |

## Development checks

From the repository root:

```powershell
python -m compileall -q backend
python -m pytest -q backend
```

For the frontend:

```powershell
cd frontend
npm ci
npm run build
```

## License and contributors

This project is distributed under the MIT License; see [LICENSE](./LICENSE).

- Jeevan Geo Vadakken
- Sujay P
- Niharika K Thilak
