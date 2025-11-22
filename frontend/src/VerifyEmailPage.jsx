// // frontend/src/VerifyEmailPage.jsx
// import React, { useEffect, useState } from 'react';
// import { useSearchParams, Link } from 'react-router-dom';
// import axios from 'axios'; // Or use your api.js helper if you prefer

// // Make sure this matches your API base URL
// const API_BASE = 'http://127.0.0.1:8000/api'; 

// export default function VerifyEmailPage() {
//   const [searchParams] = useSearchParams();
//   const token = searchParams.get('token');
//   const [status, setStatus] = useState('verifying'); // 'verifying', 'success', 'error'
//   const [message, setMessage] = useState('');

//   useEffect(() => {
//     if (!token) {
//       setStatus('error');
//       setMessage('No verification token found.');
//       return;
//     }

//     // Call the backend to verify
//     axios.post(`${API_BASE}/drugs/auth/verify-email/`, { token })
//       .then((res) => {
//         setStatus('success');
//         setMessage(res.data.message || 'Email verified successfully!');
//       })
//       .catch((err) => {
//         setStatus('error');
//         setMessage(err.response?.data?.error || 'Verification failed. Link may be expired.');
//       });
//   }, [token]);

//   return (
//     <div className="auth-container" style={{ textAlign: 'center', marginTop: '5rem' }}>
      
//       {/* LOADING STATE */}
//       {status === 'verifying' && (
//         <>
//           <div className="loader" style={{ margin: '0 auto 20px' }}></div>
//           <h2>Verifying your email...</h2>
//           <p>Please wait a moment.</p>
//         </>
//       )}

//       {/* SUCCESS STATE */}
//       {status === 'success' && (
//         <>
//           <span className="material-symbols-outlined" style={{ fontSize: '64px', color: '#4caf50' }}>check_circle</span>
//           <h2 style={{ color: '#4caf50' }}>Success!</h2>
//           <p>{message}</p>
//           <Link to="/login" className="auth-button" style={{ display: 'inline-block', marginTop: '20px' }}>
//             Login Now
//           </Link>
//         </>
//       )}

//       {/* ERROR STATE */}
//       {status === 'error' && (
//         <>
//           <span className="material-symbols-outlined" style={{ fontSize: '64px', color: '#ff4d4d' }}>error</span>
//           <h2 style={{ color: '#ff4d4d' }}>Verification Failed</h2>
//           <p>{message}</p>
//           <Link to="/signup" className="auth-button" style={{ display: 'inline-block', marginTop: '20px', backgroundColor: '#333' }}>
//             Back to Sign Up
//           </Link>
//         </>
//       )}
//     </div>
//   );
// }
// frontend/src/VerifyEmailPage.jsx
import React, { useEffect, useState, useRef } from 'react'; // <--- Import useRef
import { useSearchParams, Link } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [status, setStatus] = useState('loading'); 
  const [message, setMessage] = useState('Verifying...');
  
  // --- FIX: Add a ref to track if we already ran the check ---
  const hasFetched = useRef(false); 

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token found in the link.');
      return;
    }

    // --- FIX: Stop if we already checked ---
    if (hasFetched.current) return;
    hasFetched.current = true; 
    // --------------------------------------

    fetch(`${API_BASE}/api/drugs/auth/verify-email/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token })
    })
    .then(async (res) => {
        const data = await res.json();
        if (res.ok) {
            setStatus('success');
            setMessage(data.message || 'Email verified successfully!');
        } else {
            // If it fails, check if it might be because we just verified it
            if (data.error === "Invalid or expired token") {
                 // Optional: You could assume success here if you wanted, 
                 // but the useRef fix handles the root cause better.
            }
            setStatus('error');
            setMessage(data.error || 'Verification link is invalid or expired.');
        }
    })
    .catch((err) => {
        console.error(err);
        setStatus('error');
        setMessage('Network error. Please try again.');
    });

  }, [token]);

  return (
    <div className="auth-container" style={{ textAlign: 'center', marginTop: '100px' }}>
      
      {status === 'loading' && (
        <>
          <div className="loader" style={{ margin: '0 auto 20px' }}></div>
          <h2>Verifying Email...</h2>
        </>
      )}

      {status === 'success' && (
        <>
          <h2 style={{ color: '#4ade80' }}>Success!</h2>
          <p style={{ margin: '20px 0', color: '#e0e0e0' }}>{message}</p>
          <Link to="/login" className="auth-button" style={{ display: 'inline-block' }}>
            Go to Login
          </Link>
        </>
      )}

      {status === 'error' && (
        <>
          <h2 style={{ color: '#ef4444' }}>Verification Failed</h2>
          <p style={{ margin: '20px 0', color: '#e0e0e0' }}>{message}</p>
          <Link to="/signup" className="auth-button" style={{ background: '#374151' }}>
            Back to Sign Up
          </Link>
        </>
      )}
    </div>
  );
}