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
  const res = await fetch(`${API_BASE}/api/drugs/check-interactions/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ drugs: drugList }),
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