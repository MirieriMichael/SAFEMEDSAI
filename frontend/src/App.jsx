// frontend/src/App.jsx
import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';

// --- CSS IMPORTS ---
// Global styles for the whole app (nav, footer, buttons)
import './App.css'; 
// Page-specific styles for the homepage
import './HomePage.css'; 
// Page-specific styles for the check/results page
import './CheckPage.css'; 
// The icon font for all pages


// Import your page components
import HomePage from './HomePage';
import CheckPage from './CheckPage';
// We'll add these later
// import HistoryPage from './HistoryPage'; 
// import HelpPage from './HelpPage';
// import LoginPage from './LoginPage';

function App() {
  return (
    <div className="App">
      <nav className="app-nav">
        <Link to="/" className="nav-logo">SafeMedsAI</Link>
        <div className="nav-links">
          <Link to="/check">Check Interactions</Link>
          <Link to="/history">View History</Link>
          <Link to="/help">Help & FAQ</Link>
        </div>
        <div className="nav-auth">
          <button className="signup-button">Sign Up</button>
          <Link to="/login" className="login-button">Login</Link>
        </div>
      </nav>

      <main className="app-main">
        {/* --- This is the Router --- */}
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/check" element={<CheckPage />} />
          {/* <Route path="/history" element={<HistoryPage />} /> */}
          {/* <Route path="/help" element={<HelpPage />} /> */}
          {/* <Route path="/login" element={<LoginPage />} /> */}
        </Routes>
        {/* --- End Router --- */}
      </main>

      <footer className="app-footer">
        <p>Disclaimer: This tool is for informational purposes only and is not a substitute for professional medical advice.</p>
        <p>&copy; {new Date().getFullYear()} SafeMedsAI. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;