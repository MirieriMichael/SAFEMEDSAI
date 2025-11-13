// // frontend/src/services/api.js

// // --- DIAGNOSTIC TEST VARIABLE ---
// export const DIAGNOSTIC_MESSAGE = "SUCCESS: api.js is being read correctly!";

// const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// export async function getHealth() {
//   const res = await fetch(`${API_BASE}/api/health/`);
//   if (!res.ok) throw new Error('Health check failed');
//   return res.json();
// }

// export async function checkInteractions(drugList) {
//   const res = await fetch(`${API_BASE}/api/drugs/check-interactions/`, {
//     method: 'POST',
//     headers: {
//       'Content-Type': 'application/json',
//     },
//     body: JSON.stringify({ drugs: drugList }),
//   });

//   if (!res.ok) {
//     const errorData = await res.json().catch(() => ({ error: 'API request failed' }));
//     throw new Error(errorData.error || 'API request failed');
//   }
  
//   return res.json();
// }

// export async function analyzeImages(files) {
//   const formData = new FormData();
//   files.forEach(file => {
//     formData.append('images', file);
//   });

//   const res = await fetch(`${API_BASE}/api/drugs/scan-and-check/`, {
//     method: 'POST',
//     body: formData,
//   });

//   if (!res.ok) {
//     const errorData = await res.json().catch(() => ({ error: 'Image analysis failed' }));
//     throw new Error(errorData.error || 'Image analysis failed');
//   }
  
//   return res.json();
// }
// frontend/src/services/api.js

// --- DIAGNOSTIC TEST VARIABLE ---
export const DIAGNOSTIC_MESSAGE = "SUCCESS: api.js is being read correctly!";

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// --- NEW: Helper function to get auth headers ---
// This reads the token that AuthContext saved to localStorage.
const getAuthHeaders = () => {
  const token = localStorage.getItem('authToken');
  const headers = {
    'Content-Type': 'application/json', // Default content type
  };
  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }
  return headers;
};
// --- END NEW ---

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

// --- UPDATED: analyzeImages now sends auth token ---
export async function analyzeImages(files) {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('images', file);
  });

  // We now get the token and add it to the request headers
  // Note: We *don't* set Content-Type for FormData, browser does it.
  const authHeaders = getAuthHeaders();
  delete authHeaders['Content-Type']; // Let browser set multipart boundary

  const res = await fetch(`${API_BASE}/api/drugs/scan-and-check/`, {
    method: 'POST',
    headers: {
      ...authHeaders // <-- ADD THIS to send the token
    },
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Image analysis failed' }));
    throw new Error(errorData.error || 'Image analysis failed');
  }
  
  return res.json();
}
// --- END UPDATE ---


// --- NEW: Auth and History functions ---

export async function loginUser(username, password) {
  const res = await fetch(`${API_BASE}/api/drugs/auth/login/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ username, password }),
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Login failed' }));
    throw new Error(errorData.error || 'Login failed');
  }
  
  return res.json(); // Returns { token: "...", username: "..." }
}

export async function signupUser(username, email, password) {
  const res = await fetch(`${API_BASE}/api/drugs/auth/signup/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ username, email, password }),
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Signup failed' }));
    throw new Error(errorData.error || 'Signup failed');
  }
  
  return res.json(); // Returns { token: "...", username: "..." }
}

export async function getScanHistory() {
  const res = await fetch(`${API_BASE}/api/drugs/history/`, {
    method: 'GET',
    headers: getAuthHeaders(), // <-- MUST be authenticated
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Failed to fetch history' }));
    throw new Error(errorData.error || 'Failed to fetch history');
  }
  
  return res.json();
}
// frontend/src/services/api.js

export async function deleteScanHistory(scanId) {
  const res = await fetch(`${API_BASE}/api/drugs/history/`, {
    method: 'DELETE', // Using DELETE method
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ scan_id: scanId })
  });

  if (!res.ok) {
    throw new Error('Failed to delete item');
  }
  return res.json();
}
// frontend/src/services/api.js

// ... existing functions ...

// frontend/src/services/api.js

// ... (keep all your existing imports and functions) ...

// --- NEW: Profile & Notification Functions ---

export async function getUserProfile() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/profile/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch profile');
  return res.json();
}

// Updated to handle both JSON (tags) and FormData (images)
export async function updateUserProfile(data) {
  const isFormData = data instanceof FormData;
  const headers = getAuthHeaders();
  
  // If sending a file (FormData), delete Content-Type so browser sets the boundary
  if (isFormData) {
    delete headers['Content-Type'];
  }

  const res = await fetch(`${API_BASE}/api/drugs/auth/profile/`, {
    method: 'PUT',
    headers: headers,
    body: isFormData ? data : JSON.stringify(data),
  });
  
  if (!res.ok) throw new Error('Failed to update profile');
  return res.json();
}

export async function getNotifications() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/notifications/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch notifications');
  return res.json();
}

export async function markNotificationsRead() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/notifications/`, {
    method: 'PUT',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to update notifications');
  return res.json();
}

export async function clearUserHistory() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/profile/?target=history`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to clear history');
  return res.json();
}

export async function deleteUserAccount() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/profile/`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to delete account');
  return res.json();
}
// frontend/src/services/api.js

// ... existing functions ...

// --- NEW: Resend Verification Email ---
export async function resendVerificationEmail(email) {
  const res = await fetch(`${API_BASE}/api/drugs/auth/resend-verification/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Failed to resend email' }));
    throw new Error(errorData.error || 'Failed to resend email');
  }
  
  return res.json();
}