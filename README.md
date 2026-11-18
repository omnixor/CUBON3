## Overview

CUBON3 is an AI-powered CT-to-3D bone reconstruction project that explores the transformation of medical imaging data into interactive 3D models.

The project integrates **Aholo Lux3D** for image-to-3D generation, with a backend built using **FastAPI** to handle image uploads, generation requests, task monitoring, and GLB model retrieval.

The broader objective is to combine 3D reconstruction, geometric validation, and interactive visualization into a unified workflow.

## Features

### Backend
- Image upload through REST API.
- AI-powered 3D generation using Aholo Lux3D.
- Asynchronous generation task submission.
- Generation task status retrieval.
- GLB model download and storage.
- Static serving of generated 3D models.

### Project Vision
- CT-to-3D bone reconstruction.
- Geometric validation of reconstructed models.
- Interactive 3D visualization.
- Integration of medical imaging and 3D modelling workflows.

  ## Technology Stack

| Component | Technology |
|---|---|
| Backend Framework | FastAPI |
| Programming Language | Python |
| 3D Generation | Aholo Lux3D SDK |
| API Server | Uvicorn |
| Environment Management | Python dotenv |
| 3D Model Format | GLB |
| HTTP Requests | Requests |
| File Upload Handling | Python Multipart |

## Backend Setup

### 1. Clone the Repository

```bash
git clone https://github.com/omnixor/CUBON3.git
cd CUBON3
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the repository root using the example template:

**Windows:**
```powershell
Copy-Item .env.example .env
```

Add your own AHolo API key:

```env
AHOLO_API_KEY=your_aholo_api_key
```

Each developer must use their own authorized API key. Never commit `.env` to GitHub.

### 5. Start the Backend Server

From the repository root, run:

```bash
python -m uvicorn main:app --reload --app-dir backend
```

The backend will be available at:

- **API:** http://127.0.0.1:8000
- **Interactive API documentation:** http://127.0.0.1:8000/docs
- **Health check:** http://127.0.0.1:8000/api/health
