// frontend/src/LoginPage.jsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { loginUser } from './services/api'; // Uses your api.js
import { useAuth } from './context/AuthContext';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // 1. Call API
      const data = await loginUser(username, password);
      
      // --- [THE FIX IS HERE] ---
      // Check if the backend says "2FA Required"
      if (data.requires_2fa) {
        // Save username so the next page knows who is verifying
        localStorage.setItem('2fa_user', username);
        // Redirect to the code entry page
        navigate('/verify-2fa'); 
        return; // Stop execution here
      }
      // -------------------------

      // 2. Standard Login (No 2FA)
      // If we got a token, log them in
      if (data.token) {
          // Your AuthContext likely expects (token, username) or an object depending on your implementation
          // Based on your previous context code, it seems to take (token, username)
          login(data.token, data.username); 
          navigate('/history'); // Redirect to History/Home
      } else {
          setError('Login succeeded but no token received.');
      }

    } catch (err) {
      console.error("Login Error:", err);
      setError(err.message || 'Invalid username or password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>Login to SafeMedsAI</h2>
        
        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              required 
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="auth-footer">
          Don't have an account? <Link to="/signup">Sign Up</Link>
          <br />
        <Link to="/request-reset-password" style={{fontSize: '0.9em', color: '#aaa'}}>Forgot Password?</Link>
      </p>
      </div>
    </div>
  );
}