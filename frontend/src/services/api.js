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
// Inside frontend/src/services/api.js

const getAuthHeaders = () => {
  // MUST MATCH the key used in AuthContext ('authToken')
  const token = localStorage.getItem('authToken'); 
  
  const headers = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    // Django REST Framework expects "Token <key_string>"
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
  
  // CRITICAL: Delete Content-Type for FormData so browser sets boundary
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
// frontend/src/services/api.js

// ... existing functions ...

export async function setup2FA() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/2fa/setup/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to setup 2FA');
  return res.json(); // Returns { qr_code: "data:image..." }
}

export async function verify2FA(code) {
  const res = await fetch(`${API_BASE}/api/drugs/auth/2fa/verify/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ code }),
  });
  if (!res.ok) throw new Error('Invalid code');
  return res.json();
}

export async function disable2FA() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/2fa/disable/`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to disable 2FA');
  return res.json();
}
// ... inside frontend/src/services/api.js

// ADD THIS NEW FUNCTION
export async function sendEmailOTP() {
  const res = await fetch(`${API_BASE}/api/drugs/auth/2fa/email/`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to send email code');
  return res.json();
}

// ... (Keep setup2FA, verify2FA, disable2FA as they are)
// frontend/src/services/api.js
// ... (at the end of the file)

export async function changePassword(oldPassword, newPassword, confirmNewPassword) {
  const res = await fetch(`${API_BASE}/api/drugs/auth/change-password/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      old_password: oldPassword,
      new_password: newPassword,
      confirm_new_password: confirmNewPassword
    }),
  });
  
  const data = await res.json();
  if (!res.ok) {
    // Pass the specific error from the backend (e.g., "Incorrect old password")
    throw new Error(data.error || "Failed to change password.");
  }
  return data;
}
// frontend/src/services/api.js
// ... (at the end of the file)

export async function requestPasswordReset(email) {
  const res = await fetch(`${API_BASE}/api/drugs/auth/password-reset-request/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return res.json();
}

export async function confirmPasswordReset(uidb64, token, new_password) {
  const res = await fetch(`${API_BASE}/api/drugs/auth/password-reset-confirm/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uidb64, token, new_password }),
  });
  
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to reset password.");
  }
  return data;
}