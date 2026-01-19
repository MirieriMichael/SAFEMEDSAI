import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

// --- Helper API Function (Defined here for simplicity) ---
const loginWith2FA = async (username, code) => {
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
  
  const res = await fetch(`${API_BASE}/api/drugs/auth/2fa/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, code }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: 'Invalid 2FA code' }));
    throw new Error(errorData.error || 'Invalid 2FA code');
  }
  
  return res.json(); // Returns { token: "...", username: "..." }
};

export default function Verify2FAPage() {
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    // Get the username saved during the first login step
    const username = localStorage.getItem('2fa_user');
    
    if (!username) {
      setError("Session expired. Please login again.");
      setIsLoading(false);
      setTimeout(() => navigate('/login'), 2000);
      return;
    }

    try {
      const data = await loginWith2FA(username, code);
      
      if (data.token && data.username) {
        // Login Success!
        login(data.token, data.username);
        localStorage.removeItem('2fa_user'); // Clean up temporary storage
        navigate('/history');
      } else {
        setError('Login failed after 2FA.');
      }
    } catch (err) {
      setError(err.message || 'Invalid code.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <form onSubmit={handleSubmit} className="auth-form">
        <h2>Enter Security Code</h2>
        <p style={{color: '#ccc', marginBottom: '20px', textAlign: 'center'}}>
          A 6-digit code was sent to your email or is in your authenticator app.
        </p>
        
        {error && <div className="error-banner">{error}</div>}
        
        <div className="form-group">
          <label htmlFor="code">6-Digit Code</label>
          <input
            type="text"
            id="code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            disabled={isLoading}
            maxLength={6}
            placeholder="123456"
            style={{textAlign: 'center', letterSpacing: '5px', fontSize: '1.2em'}}
          />
        </div>
        <button type="submit" className="auth-button" disabled={isLoading}>
          {isLoading ? 'Verifying...' : 'Verify & Login'}
        </button>
      </form>
    </div>
  );
}