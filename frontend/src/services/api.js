// frontend/src/services/api.js

// This line sets the base URL for your backend. It reads an environment
// variable when deployed, but defaults to your local server for development.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

/**
 * A function to check the health of the backend API.
 * @returns {Promise<object>} A promise that resolves to the JSON response.
 */
export async function getHealth() {
  const res = await fetch(`${API_BASE}/api/health/`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}