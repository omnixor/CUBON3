
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);

    if (!response.ok) {
      throw new Error('Backend health check failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Backend connection error:', error);
    throw error;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    let detail = 'Request failed';
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep the generic message if the server did not return JSON.
    }
    throw new Error(detail);
  }

  return response.json();
}

export function generate3D(file) {
  const form = new FormData();
  form.append('file', file);
  return request('/api/aholo/generate', {
    method: 'POST',
    body: form,
  });
}

export function generateAIReport(file) {
  const form = new FormData();
  form.append('file', file);
  form.append('consent', 'true');
  return request('/api/analysis/report', {
    method: 'POST',
    body: form,
  });
}

export function getTask(taskId) {
  return request(`/api/aholo/task/${taskId}`);
}

export function downloadModel(taskId) {
  return request(`/api/aholo/task/${taskId}/download`, { method: 'POST' });
}

export function getProjects() {
  return request('/api/projects');
}

export function deleteProject(taskId) {
  return request(`/api/projects/${taskId}`, { method: 'DELETE' });
}

export function importDicomSeries(files) {
  const form = new FormData();
  for (const file of files) {
    form.append('files', file, file.name);
  }
  return request('/api/dicom/import', {
    method: 'POST',
    body: form,
  });
}

export function generate3DFromDicomSlice(jobId, sliceIndex) {
  return request(
    `/api/dicom/jobs/${encodeURIComponent(jobId)}/aholo?slice_index=${sliceIndex}`,
    { method: 'POST' },
  );
}

export function getDicomSliceUrl(jobId, sliceIndex) {
  return `${API_BASE_URL}/api/dicom/jobs/${encodeURIComponent(jobId)}/slices/${sliceIndex}`;
}

export function getDicomJob(jobId) {
  return request(`/api/dicom/jobs/${encodeURIComponent(jobId)}`);
}

export function getDicomJobs() {
  return request('/api/dicom/jobs');
}

export function deleteDicomJob(jobId) {
  return request(`/api/dicom/jobs/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  });
}

export async function downloadDicomBundle(jobId) {
  const response = await fetch(
    `${API_BASE_URL}/api/dicom/jobs/${encodeURIComponent(jobId)}/bundle`,
  );
  if (!response.ok) {
    let detail = 'Could not download the converted DICOM bundle.';
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep the generic message if the server did not return JSON.
    }
    throw new Error(detail);
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = `cubon3-dicom-${jobId.slice(0, 8)}.zip`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export { API_BASE_URL };
