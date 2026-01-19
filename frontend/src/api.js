// frontend/src/services/api.js

// --- DIAGNOSTIC TEST VARIABLE ---
export const DIAGNOSTIC_MESSAGE = "SUCCESS: api.js is being read correctly!";

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export async function getHealth() {
  const res = await fetch(`${API_BASE}/api/health/`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function checkInteractions(drugList) {
  // Use scan-and-check endpoint with drug names as FormData
  const formData = new FormData();
  formData.append('drug_names', drugList.join(','));

  const res = await fetch(`${API_BASE}/api/drugs/scan-and-check/`, {
    method: 'POST',
    // Don't set Content-Type for FormData - browser sets boundary automatically
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'API request failed' }));
    throw new Error(errorData.error || 'API request failed');
  }
  
  return res.json();
}

export async function analyzeImages(files) {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('images', file);
  });

  const res = await fetch(`${API_BASE}/api/drugs/scan-and-check/`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Image analysis failed' }));
    throw new Error(errorData.error || 'Image analysis failed');
  }
  
  return res.json();
}