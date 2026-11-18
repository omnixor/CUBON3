
import { useEffect, useRef, useState, Suspense } from "react";
import { Canvas, useLoader } from "@react-three/fiber";
import { Bounds, OrbitControls, Environment } from "@react-three/drei";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { useNavigate } from "react-router-dom";
import {
  deleteProject,
  deleteDicomJob,
  downloadModel,
  downloadDicomBundle,
  generate3D,
  getProjects,
  getTask,
  getDicomJob,
  getDicomJobs,
  importDicomSeries,
  generate3DFromDicomSlice,
  getDicomSliceUrl,
  API_BASE_URL,
  checkBackendHealth,
} from "../services/api";

function PageLayout({ title, description, icon, children }) {
  return (
    <section className="workspace-page">
      <div className="workspace-page-heading">
        <div className="workspace-page-icon">{icon}</div>
        <div className="workspace-page-title">
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </div>

      {children}
    </section>
  );
}

export function NewScan() {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const dicomInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("image");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [task, setTask] = useState(null);
  const [dicomFiles, setDicomFiles] = useState([]);
  const [dicomJob, setDicomJob] = useState(null);
  const [dicomError, setDicomError] = useState("");
  const [dicomBusy, setDicomBusy] = useState(false);
  const [dicomJobs, setDicomJobs] = useState([]);
  const [selectedSlice, setSelectedSlice] = useState(1);
  const stageLabels = {
    queued: "Queued",
    validating_series: "Checking DICOM series",
    volume_reconstruction: "Reconstructing CT volume",
    image_conversion: "Converting DICOM images",
    bundling_images: "Preparing lossless images",
    completed: "Complete",
    failed: "Failed",
  };

  useEffect(() => {
    if (dicomJob?.status === "completed" && dicomJob.slices > 0) {
      setSelectedSlice(Math.ceil(dicomJob.slices / 2));
    }
  }, [dicomJob?.job_id, dicomJob?.status, dicomJob?.slices]);

  useEffect(() => {
    getDicomJobs()
      .then((data) => {
        setDicomJobs(data.jobs);
        const activeJob = data.jobs.find((job) => ["queued", "processing"].includes(job.status));
        if (activeJob) setDicomJob(activeJob);
      })
      .catch((loadError) => setDicomError(loadError.message));
  }, []);

  async function submit(event) {
    event.preventDefault();
    if (!file) {
      setError("Select a JPEG, PNG, or WebP image.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await generate3D(file);
      setTask(created);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!dicomJob || !["queued", "processing"].includes(dicomJob.status)) return;
    const timer = setInterval(() => {
      getDicomJob(dicomJob.job_id)
        .then((updated) => {
          setDicomJob(updated);
          setDicomJobs((current) =>
            current.map((item) => item.job_id === updated.job_id ? updated : item)
          );
        })
        .catch((pollError) => setDicomError(pollError.message));
    }, 2500);
    return () => clearInterval(timer);
  }, [dicomJob?.job_id, dicomJob?.status]);

  async function submitDicom(event) {
    event.preventDefault();
    if (!dicomFiles.length) {
      setDicomError("Select the DICOM files from one series.");
      return;
    }
    setDicomBusy(true);
    setDicomError("");
    setDicomJob(null);
    try {
      const job = await importDicomSeries(dicomFiles);
      setDicomJob(job);
      setDicomJobs((current) => [job, ...current]);
    } catch (submitError) {
      setDicomError(submitError.message);
    } finally {
      setDicomBusy(false);
    }
  }

  async function downloadDicom(jobId = dicomJob?.job_id) {
    try {
      await downloadDicomBundle(jobId);
    } catch (downloadError) {
      setDicomError(downloadError.message);
    }
  }

  async function submitDicomSlice() {
    if (!dicomJob || selectedSlice < 1 || selectedSlice > dicomJob.slices) return;
    setDicomBusy(true);
    setDicomError("");
    try {
      const created = await generate3DFromDicomSlice(dicomJob.job_id, selectedSlice);
      setTask(created);
    } catch (submitError) {
      setDicomError(submitError.message);
    } finally {
      setDicomBusy(false);
    }
  }

  async function removeDicomJob(jobId) {
    if (!window.confirm("Delete the backend DICOM source files and converted images for this job?")) return;
    try {
      await deleteDicomJob(jobId);
      setDicomJobs((current) => current.filter((item) => item.job_id !== jobId));
      setDicomJob((current) => current?.job_id === jobId ? null : current);
    } catch (deleteError) {
      setDicomError(deleteError.message);
    }
  }

  return (
    <PageLayout
      title="Create 3D with Aholo"
      description="Upload an image or convert DICOM images to lossless PNG before Aholo generation."
      icon="📤"
    >
      <div className="mode-tabs">
        <button type="button" className={mode === "image" ? "selected" : ""} onClick={() => setMode("image")}>
          Image / X-ray
        </button>
        <button type="button" className={mode === "dicom" ? "selected" : ""} onClick={() => setMode("dicom")}>
          DICOM series
        </button>
      </div>
      {mode === "image" ? (
        <form className="product-panel scan-panel" onSubmit={submit}>
          <input
            ref={inputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            hidden
          />
          <button type="button" className="dropzone" onClick={() => inputRef.current?.click()}>
            <strong>{file ? file.name : "Choose an image or X-ray"}</strong>
            <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "JPEG, PNG, or WebP · up to 10 MB"}</span>
          </button>
          <div className="dicom-note">
            The backend re-encodes the image as a lossless PNG before sending it to Aholo. A JPEG source may already contain compression loss. The image is sent to Aholo for 3D generation; upload de-identified images only.
          </div>
          {error && <div className="alert error">{error}</div>}
          {task && (
            <div className="alert success">
              Task #{task.provider_task_id} submitted.
              <button type="button" onClick={() => navigate(`/viewer?task=${task.provider_task_id}`)}>
                Open task
              </button>
            </div>
          )}
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Submitting to Aholo..." : "Create 3D with Aholo"}
          </button>
        </form>
      ) : (
        <form className="product-panel scan-panel" onSubmit={submitDicom}>
          <input
            ref={dicomInputRef}
            type="file"
            multiple
            onChange={(event) => setDicomFiles(Array.from(event.target.files || []))}
            hidden
          />
          <button type="button" className="dropzone" onClick={() => dicomInputRef.current?.click()}>
            <strong>{dicomFiles.length ? `${dicomFiles.length} DICOM files selected` : "Choose a DICOM CT or X-ray series"}</strong>
            <span>One DICOM series at a time · lossless image conversion runs on the backend</span>
          </button>
          <div className="dicom-note">
            The backend converts DICOM pixel data into lossless PNG slices. Choose one slice to send to Aholo; it receives only that 2D image, not the full CT volume, and infers 3D from that image. A CT series also gets a spatial volume reconstruction. The source DICOM and converted images remain on the backend until deleted. Use de-identified data only.
          </div>
          {dicomError && <div className="alert error">{dicomError}</div>}
          {dicomJob && (
            <div className={`alert ${dicomJob.status === "failed" ? "error" : "success"}`}>
              <span>
                {dicomJob.status === "failed"
                  ? dicomJob.error
                  : `${stageLabels[dicomJob.stage] || dicomJob.stage}: ${dicomJob.slices || 0} / ${dicomJob.source_files} images`}
              </span>
              {dicomJob.status === "completed" && dicomJob.slices > 0 && (
                <div className="dicom-aholo-flow">
                  <img
                    className="dicom-slice-preview"
                    src={getDicomSliceUrl(dicomJob.job_id, selectedSlice)}
                    alt={`Converted DICOM image ${selectedSlice}`}
                  />
                  <label>
                    Select image {selectedSlice} of {dicomJob.slices}
                    <input
                      type="range"
                      min="1"
                      max={dicomJob.slices}
                      step="1"
                      value={selectedSlice}
                      onChange={(event) => setSelectedSlice(Number(event.target.value))}
                    />
                  </label>
                  <button type="button" onClick={submitDicomSlice} disabled={dicomBusy}>
                    {dicomBusy ? "Submitting to Aholo..." : "Create 3D with Aholo"}
                  </button>
                  <button type="button" onClick={downloadDicom}>Download complete bundle</button>
                </div>
              )}
            </div>
          )}
          {task && mode === "dicom" && (
            <div className="alert success">
              Aholo task #{task.provider_task_id} submitted.
              <button type="button" onClick={() => navigate(`/viewer?task=${task.provider_task_id}`)}>
                View task
              </button>
            </div>
          )}
          <button className="primary-button" disabled={dicomBusy} type="submit">
            {dicomBusy ? "Uploading..." : "Import and convert series"}
          </button>
        </form>
      )}
      {mode === "dicom" && (
        <section className="product-panel dicom-history">
          <h3>Recent DICOM imports</h3>
          {dicomJobs.length === 0 ? (
            <p className="muted-note">No DICOM imports yet.</p>
          ) : dicomJobs.map((job) => (
            <div className="dicom-job-row" key={job.job_id}>
              <button type="button" onClick={() => setDicomJob(job)}>
                <strong>{job.name}</strong>
                <span>{job.slices || 0} / {job.source_files} images · {stageLabels[job.stage] || job.stage}</span>
              </button>
              {job.status === "completed" && (
                <button className="secondary-button" type="button" onClick={() => downloadDicom(job.job_id)}>
                  Download converted images
                </button>
              )}
              {!["queued", "processing"].includes(job.status) && (
                <button className="danger-button" type="button" onClick={() => removeDicomJob(job.job_id)}>
                  Delete local data
                </button>
              )}
            </div>
          ))}
        </section>
      )}
    </PageLayout>
  );
}

export function Viewer() {
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(window.location.search);
  const taskId = searchParams.get("task");
  const [projects, setProjects] = useState([]);
  const [project, setProject] = useState(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);

  async function refresh(id) {
    if (!id) return;
    try {
      const data = await getTask(id);
      const statusByCode = {
        1: "submitted",
        2: "processing",
        3: "completed",
        4: "failed",
      };
      setStatus(data.local?.status || statusByCode[data.status] || String(data.status || "unknown"));
      setProject(data.local);
      setError("");
    } catch (refreshError) {
      setError(refreshError.message);
    }
  }

  useEffect(() => {
    getProjects()
      .then((data) => setProjects(data.projects))
      .catch((loadError) => setError(loadError.message));
  }, []);

  useEffect(() => {
    if (!taskId) return;
    refresh(taskId);
  }, [taskId]);

  useEffect(() => {
    if (!taskId || ["completed", "failed", "downloaded"].includes(status)) return;
    const timer = setInterval(() => refresh(taskId), 5000);
    return () => clearInterval(timer);
  }, [taskId, status]);

  async function download() {
    setDownloading(true);
    setError("");
    try {
      await downloadModel(taskId);
      await refresh(taskId);
    } catch (downloadError) {
      setError(downloadError.message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <PageLayout
      title="3D Viewer"
      description="View and interact with generated 3D models."
      icon="🦴"
    >
      <div className="product-grid viewer-grid">
        <aside className="product-panel task-list">
          <h3>Tasks</h3>
          {projects.map((item) => (
            <button
              key={item.provider_task_id}
              className={String(item.provider_task_id) === taskId ? "selected" : ""}
              onClick={() => navigate(`/viewer?task=${item.provider_task_id}`)}
            >
              <span>{item.name}</span>
              <small>{item.status}</small>
            </button>
          ))}
        </aside>
        <div className="product-panel model-panel">
          {error && <div className="alert error">{error}</div>}
          {taskId && status && (
            <GenerationProgress taskId={taskId} status={status} />
          )}
          {project?.glb_file ? (
            <>
              <div className="model-stage">
                <Suspense fallback={<div className="model-loading">Loading model...</div>}>
                  <ModelViewer url={`${API_BASE_URL}/models/${encodeURIComponent(project.glb_file)}`} />
                </Suspense>
              </div>
              <a className="secondary-button" href={`${API_BASE_URL}/models/${encodeURIComponent(project.glb_file)}`} download>
                Download GLB
              </a>
            </>
          ) : status === "completed" ? (
            <button className="primary-button" onClick={download} disabled={downloading}>
              {downloading ? "Downloading..." : "Download and prepare GLB"}
            </button>
          ) : taskId ? (
            status ? null : (
              <div className="model-placeholder">
                <span>Loading task status...</span>
              </div>
            )
          ) : (
            <div className="model-placeholder">
              <strong>No task selected</strong>
              <span>Select a reconstruction from the list.</span>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}

function GenerationProgress({ taskId, status }) {
  const isComplete = ["completed", "downloaded"].includes(status);
  const isFailed = status === "failed";
  const progressByStatus = {
    submitted: 10,
    processing: 65,
    completed: 100,
    downloaded: 100,
  };
  const percent = isFailed ? null : progressByStatus[status] ?? 5;
  const labelByStatus = {
    submitted: "Submitted to Aholo",
    processing: "Aholo is generating your model",
    completed: "Generation complete",
    downloaded: "Model ready",
    failed: "Generation failed",
  };
  const label = labelByStatus[status] || "Waiting for Aholo";
  const progressClass = isFailed ? "failed" : isComplete ? "complete" : "active";

  return (
    <section className={`generation-progress-card ${progressClass}`}>
      <div className="generation-progress-header">
        <div>
          <strong>Aholo generation</strong>
          <span>Task #{taskId}</span>
        </div>
        <b>{label}{percent === null ? "" : ` · ${percent}%`}</b>
      </div>
      <div
        className="generation-progress-track"
        role="progressbar"
        aria-label="Aholo generation status"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={percent ?? undefined}
        aria-valuetext={percent === null ? label : `${label}, estimated ${percent}%`}
      >
        <div
          className="generation-progress-fill"
          style={{ width: `${percent ?? 0}%` }}
        />
      </div>
      <p>
        {isFailed
          ? "Aholo could not complete this task."
          : isComplete
            ? "Your model is ready to download."
            : "Estimated from task status; Aholo does not provide an exact percentage."}
      </p>
    </section>
  );
}

function ModelViewer({ url }) {
  const gltf = useLoader(GLTFLoader, url);
  return (
    <Canvas camera={{ position: [0, 1, 3], fov: 45 }}>
      <ambientLight intensity={1.2} />
      <directionalLight position={[5, 5, 5]} intensity={1.5} />
      <Bounds fit clip observe margin={1.2}>
        <primitive object={gltf.scene} />
      </Bounds>
      <OrbitControls makeDefault />
      <Environment preset="studio" />
    </Canvas>
  );
}

export function Analysis() {
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getProjects()
      .then((data) => setProjects(data.projects))
      .catch((loadError) => setError(loadError.message));
  }, []);

  return (
    <PageLayout
      title="Analysis"
      description="Review available scan and generation information."
      icon="📊"
    >
      <div className="product-grid analysis-grid">
        <div className="product-panel metric"><span>Total tasks</span><strong>{projects.length}</strong></div>
        <div className="product-panel metric"><span>Downloaded models</span><strong>{projects.filter((item) => item.glb_file).length}</strong></div>
        <div className="product-panel metric"><span>Provider failures</span><strong>{projects.filter((item) => item.status === "failed").length}</strong></div>
      </div>
      {error && <div className="alert error">{error}</div>}
    </PageLayout>
  );
}

export function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      const data = await getProjects();
      setProjects(data.projects);
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  useEffect(() => { load(); }, []);

  async function remove(taskId) {
    if (!window.confirm("Delete this project and any downloaded GLB model?")) return;
    try {
      await deleteProject(taskId);
      await load();
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  return (
    <PageLayout
      title="Projects"
      description="Manage your generated 3D reconstruction projects."
      icon="📁"
    >
      {error && <div className="alert error">{error}</div>}
      <div className="product-panel project-table">
        {projects.length === 0 ? (
          <p className="muted-note">No projects have been created.</p>
        ) : projects.map((project) => (
          <div className="project-row" key={project.provider_task_id}>
            <div>
              <strong>{project.name}</strong>
              <span>Task #{project.provider_task_id} · {project.created_at}</span>
            </div>
            <b className={`status-badge ${project.status}`}>{project.status}</b>
            <button className="secondary-button" onClick={() => navigate(`/viewer?task=${project.provider_task_id}`)}>Open</button>
            <button className="danger-button" onClick={() => remove(project.provider_task_id)}>Delete</button>
          </div>
        ))}
      </div>
    </PageLayout>
  );
}

export function SettingsPage() {
  const [backend, setBackend] = useState(null);

  useEffect(() => {
    checkBackendHealth()
      .then(setBackend)
      .catch(() => setBackend({ status: "unavailable", aholo_key_configured: false }));
  }, []);

  return (
    <PageLayout
      title="Settings"
      description="Manage your CUBON3 workspace."
      icon="⚙️"
    >
      <div className="product-panel settings-panel">
        <div><span>API</span><strong>{API_BASE_URL}</strong></div>
        <div><span>Backend</span><strong>{backend?.status || "Checking..."}</strong></div>
        <div><span>Aholo provider</span><strong>{backend?.aholo_key_configured ? "Configured" : backend?.status === "unavailable" ? "Backend unavailable" : backend ? "Not configured" : "Checking..."}</strong></div>
      </div>
    </PageLayout>
  );
}
