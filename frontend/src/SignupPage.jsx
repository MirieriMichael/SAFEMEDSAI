// // // frontend/src/SignupPage.jsx
// // import React, { useState } from 'react';
// // import { useNavigate, Link } from 'react-router-dom';
// // import { signupUser } from './services/api'; // Import our API function
// // import { useAuth } from './context/AuthContext'; // Import our auth hook

// // export default function SignupPage() {
// //   const [username, setUsername] = useState('');
// //   const [email, setEmail] = useState('');
// //   const [password, setPassword] = useState('');
// //   const [error, setError] = useState(null);
// //   const navigate = useNavigate();
// //   const { login } = useAuth(); // Get the login function from our context

// //   const handleSubmit = async (e) => {
// //     e.preventDefault();
// //     setError(null);

// //     try {
// //       const data = await signupUser(username, email, password);
// //       login(data.token, data.username); // Log the user in immediately after signup
// //       navigate('/history'); // Redirect to history page on success
// //     } catch (err) {
// //       setError(err.message || 'Failed to sign up.');
// //     }
// //   };

// //   return (
// //     <div className="auth-container">
// //       <form onSubmit={handleSubmit} className="auth-form">
// //         <h2>Create your Account</h2>
// //         {error && <p className="error-message">{error}</p>}
// //         <div className="form-group">
// //           <label htmlFor="email">Email</label>
// //           <input
// //             type="email"
// //             id="email"
// //             value={email}
// //             onChange={(e) => setEmail(e.target.value)}
// //             required
// //           />
// //         </div>
// //         <div className="form-group">
// //           <label htmlFor="username">Username</label>
// //           <input
// //             type="text"
// //             id="username"
// //             value={username}
// //             onChange={(e) => setUsername(e.target.value)}
// //             required
// //           />
// //         </div>
// //         <div className="form-group">
// //           <label htmlFor="password">Password</label>
// //           <input
// //             type="password"
// //             id="password"
// //             value={password}
// //             onChange={(e) => setPassword(e.target.value)}
// //             required
// //           />
// //         </div>
// //         <button type="submit" className="auth-button">Create Account</button>
// //         <p className="auth-switch">
// //           Already have an account? <Link to="/login">Login</Link>
// //         </p>
// //       </form>
// //     </div>
// //   );
// // }
// // frontend/src/SignupPage.jsx
// import React, { useState, useEffect } from 'react';
// import { useNavigate, Link } from 'react-router-dom';
// import { signupUser } from './services/api';
// import { useAuth } from './context/AuthContext';

// export default function SignupPage() {
//   const [username, setUsername] = useState('');
//   const [email, setEmail] = useState('');
//   const [password, setPassword] = useState('');
//   const [error, setError] = useState(null);
  
//   // Password validation state
//   const [validations, setValidations] = useState({
//     length: false,
//     number: false,
//     uppercase: false,
//   });

//   const navigate = useNavigate();
//   const { login } = useAuth();

//   // Update validation whenever password changes
//   useEffect(() => {
//     setValidations({
//       length: password.length >= 8,
//       number: /\d/.test(password), // Checks for at least one digit
//       uppercase: /[A-Z]/.test(password), // Checks for at least one capital letter
//     });
//   }, [password]);

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     if (!validations.length || !validations.number || !validations.uppercase) {
//       setError("Please ensure your password meets all criteria.");
//       return;
//     }
//     setError(null);

//     try {
//       const data = await signupUser(username, email, password);
//       login(data.token, data.username);
//       navigate('/history');
//     } catch (err) {
//       setError(err.message || 'Failed to sign up.');
//     }
//   };

//   return (
//     <div className="auth-container">
//       <form onSubmit={handleSubmit} className="auth-form">
//         <h2>Create your Account</h2>
//         {error && <p className="error-message">{error}</p>}
        
//         <div className="form-group">
//           <label htmlFor="email">Email</label>
//           <input type="email" id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
//         </div>
        
//         <div className="form-group">
//           <label htmlFor="username">Username</label>
//           <input type="text" id="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
//         </div>
        
//         <div className="form-group">
//           <label htmlFor="password">Password</label>
//           <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
//         </div>

//         {/* Password Checklist */}
//         <ul className="password-criteria">
//           <li className={validations.length ? 'valid' : ''}>At least 8 characters</li>
//           <li className={validations.number ? 'valid' : ''}>Contains a number</li>
//           <li className={validations.uppercase ? 'valid' : ''}>Contains an uppercase letter</li>
//         </ul>

//         <button type="submit" className="auth-button">Create Account</button>
//         <p className="auth-switch">
//           Already have an account? <Link to="/login">Login</Link>
//         </p>
//       </form>
//     </div>
//   );
// }
// frontend/src/SignupPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signupUser, resendVerificationEmail } from './services/api'; // Import resend function
import { useAuth } from './context/AuthContext';
import './AuthPage.css';

export default function SignupPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  // --- NEW: Loading states ---
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState('');

  const [validations, setValidations] = useState({
    length: false,
    number: false,
    uppercase: false,
  });

  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    setValidations({
      length: password.length >= 8,
      number: /\d/.test(password),
      uppercase: /[A-Z]/.test(password),
    });
  }, [password]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validations.length || !validations.number || !validations.uppercase) {
      setError("Please ensure your password meets all criteria.");
      return;
    }
    
    setError(null);
    setIsSubmitting(true); // <-- START LOADING

    try {
      await signupUser(username, email, password);
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Failed to sign up.');
    } finally {
      setIsSubmitting(false); // <-- STOP LOADING
    }
  };

  // --- NEW: Resend Handler ---
  const handleResend = async () => {
    setIsResending(true);
    setResendMessage('');
    try {
      await resendVerificationEmail(email);
      setResendMessage('Email sent successfully!');
    } catch (err) {
      setResendMessage('Error: ' + err.message);
    } finally {
      setIsResending(false);
    }
  };

  if (success) {
    return (
      <div className="auth-container" style={{textAlign: 'center'}}>
        <span className="material-symbols-outlined" style={{fontSize: '48px', color: '#4caf50', marginBottom: '1rem'}}>mark_email_read</span>
        <h2 style={{color: '#ffffff', marginBottom: '0.5rem'}}>Verify your Email</h2>
        <p style={{color: '#e0e0e0', marginBottom: '1.5rem'}}>
          We've sent a verification link to <strong>{email}</strong>. Please check your inbox (and spam folder).
        </p>
        
        <Link to="/login" className="auth-button" style={{display:'inline-block', marginBottom:'20px'}}>
          Go to Login Page
        </Link>

        <div style={{borderTop: '1px solid #444', paddingTop: '20px', marginTop: '10px'}}>
          <p style={{fontSize: '0.9rem', color: '#aaa', marginBottom: '10px'}}>
            Didn't receive the email?
          </p>
          <button 
            onClick={handleResend} 
            disabled={isResending}
            className="auth-button" 
            style={{
              background: 'transparent', 
              border: '1px solid #1193d4', 
              color: '#1193d4', 
              width: 'auto', 
              padding: '8px 16px',
              fontSize: '0.9rem'
            }}
          >
            {isResending ? 'Sending...' : 'Resend Verification Email'}
          </button>
          {resendMessage && <p style={{marginTop: '10px', color: resendMessage.includes('Error') ? '#ff4d4d' : '#4caf50', fontSize: '0.9rem'}}>{resendMessage}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <form onSubmit={handleSubmit} className="auth-form">
        <h2>Create your Account</h2>
        {error && <p className="error-message">{error}</p>}
        
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input type="email" id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        
        <div className="form-group">
          <label htmlFor="username">Username</label>
          <input type="text" id="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>

        <ul className="password-criteria">
          <li className={validations.length ? 'valid' : ''}>At least 8 characters</li>
          <li className={validations.number ? 'valid' : ''}>Contains a number</li>
          <li className={validations.uppercase ? 'valid' : ''}>Contains an uppercase letter</li>
        </ul>

        <button type="submit" className="auth-button" disabled={isSubmitting}>
          {isSubmitting ? 'Creating Account...' : 'Create Account'}
        </button>
        
        <p className="auth-switch">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </form>
    </div>
  );
}