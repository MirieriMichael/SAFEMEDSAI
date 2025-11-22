// frontend/src/ResetPasswordPage.jsx
import React, { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { confirmPasswordReset } from './services/api';
import './AuthPage.css';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Get tokens from the URL
  const uidb64 = searchParams.get('uidb64');
  const token = searchParams.get('token');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    
    setError('');
    setIsLoading(true);

    try {
      const data = await confirmPasswordReset(uidb64, token, password);
      setMessage(data.message);
      setTimeout(() => navigate('/login'), 3000); // Redirect to login
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (message) {
    return (
      <div className="auth-container">
        <div className="auth-card" style={{textAlign: 'center'}}>
          <h2 style={{color: '#4ade80'}}>Success!</h2>
          <p>{message}</p>
          <Link to="/login" className="auth-button">Go to Login</Link>
        </div>
      </div>
    );
  }

  if (!uidb64 || !token) {
    return (
      <div className="auth-container">
        <div className="auth-card" style={{textAlign: 'center'}}>
          <h2 style={{color: '#ef4444'}}>Invalid Link</h2>
          <p>This password reset link is invalid or has expired.</p>
          <Link to="/login" className="auth-button">Back to Login</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>Set New Password</h2>
        
        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>New Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
          </div>
          <div className="form-group">
            <label>Confirm New Password</label>
            <input 
              type="password" 
              value={confirmPassword} 
              onChange={(e) => setConfirmPassword(e.target.value)} 
              required 
            />
          </div>
          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? 'Saving...' : 'Set New Password'}
          </button>
        </form>
      </div>
    </div>
  );
}