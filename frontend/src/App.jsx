// // frontend/src/App.jsx
// import React from 'react';
// import { Routes, Route, Link } from 'react-router-dom';

// // --- CSS IMPORTS ---
// // Global styles for the whole app (nav, footer, buttons)
// import './App.css'; 
// // Page-specific styles for the homepage
// import './HomePage.css'; 
// // Page-specific styles for the check/results page
// import './CheckPage.css'; 
// // The icon font for all pages


// // Import your page components
// import HomePage from './HomePage';
// import CheckPage from './CheckPage';
// // We'll add these later
// // import HistoryPage from './HistoryPage'; 
// // import HelpPage from './HelpPage';
// // import LoginPage from './LoginPage';

// function App() {
//   return (
//     <div className="App">
//       <nav className="app-nav">
//         <Link to="/" className="nav-logo">SafeMedsAI</Link>
//         <div className="nav-links">
//           <Link to="/check">Check Interactions</Link>
//           <Link to="/history">View History</Link>
//           <Link to="/help">Help & FAQ</Link>
//         </div>
//         <div className="nav-auth">
//           <button className="signup-button">Sign Up</button>
//           <Link to="/login" className="login-button">Login</Link>
//         </div>
//       </nav>

//       <main className="app-main">
//         {/* --- This is the Router --- */}
//         <Routes>
//           <Route path="/" element={<HomePage />} />
//           <Route path="/check" element={<CheckPage />} />
//           {/* <Route path="/history" element={<HistoryPage />} /> */}
//           {/* <Route path="/help" element={<HelpPage />} /> */}
//           {/* <Route path="/login" element={<LoginPage />} /> */}
//         </Routes>
//         {/* --- End Router --- */}
//       </main>

//       <footer className="app-footer">
//         <p>Disclaimer: This tool is for informational purposes only and is not a substitute for professional medical advice.</p>
//         <p>&copy; {new Date().getFullYear()} SafeMedsAI. All rights reserved.</p>
//       </footer>
//     </div>
//   );
// }

// export default App;
// frontend/src/App.jsx
// import React from 'react';
// import { Routes, Route, Link, useNavigate } from 'react-router-dom'; // <-- ADD 'useNavigate'

// // --- CSS IMPORTS ---
// // Global styles for the whole app (nav, footer, buttons)
// import './App.css'; 
// // Page-specific styles for the homepage
// import './HomePage.css'; 
// // Page-specific styles for the check/results page
// import './CheckPage.css'; 
// // You will need to create this CSS file for the login/signup forms
// import './AuthPage.css'; 
// // You will need to create this CSS file for the history page
// import './HistoryPage.css'; 


// // --- COMPONENT IMPORTS ---
// import HomePage from './HomePage';
// import CheckPage from './CheckPage';
// // --- ADD THIS ---
// // We are now importing all the new pages
// import HistoryPage from './HistoryPage'; 
// import LoginPage from './LoginPage';
// import SignupPage from './SignupPage'; // Added this
// import ProfilePage from './ProfilePage';
// import { useAuth } from './context/AuthContext'; // Import our auth hook

// // A simple FAQ/Help page component
// const HelpPage = () => (
//   <div className="container" style={{ padding: '2rem' }}>
//     <h2>Help & FAQ</h2>
//     <p>This is the Help & FAQ page. (From your wireframe: {`image_5021a5.jpg`})</p>
//     {/* You can build out the full FAQ here */}
//   </div>
// );
// // --- END ADD ---


// function App() {
//   // --- ADD THIS: Get auth state and functions ---
//   const { isAuthenticated, username, logout } = useAuth();
//   const navigate = useNavigate();

//   const handleLogout = () => {
//     logout();
//     navigate('/'); // Redirect to home page after logout
//   };
//   // --- END ADD ---

//   return (
//     <div className="App">
//       <nav className="app-nav">
//         <Link to="/" className="nav-logo">SafeMedsAI</Link>
//         <div className="nav-links">
//           {/* This is your original link, it's good */}
//           <Link to="/">Interaction Checker</Link> 
          
//           {/* --- ADD THIS: Show History only if logged in --- */}
//           {isAuthenticated && (
//             <Link to="/history">View History</Link>
//           )}
//           {/* --- END ADD --- */}
          
//           <Link to="/help">Help & FAQ</Link>
//         </div>
        
//         {/* --- THIS IS THE UPDATED DYNAMIC AUTH SECTION --- */}
//         <div className="nav-auth">
//           {isAuthenticated ? (
//             <>
//               <span className="nav-username">Hi, {username}</span>
//               <button onClick={handleLogout} className="logout-button">
//                 Logout
//               </button>
//             </>
//           ) : (
//             <>
//               <Link to="/signup" className="signup-button">Sign Up</Link>
//               <Link to="/login" className="login-button">Login</Link>
//             </>
//           )}
//         </div>
//         {/* --- END OF UPDATED SECTION --- */}
//       </nav>

//       <main className="app-main">
//         {/* --- This is the Router --- */}
//         <Routes>
//           <Route path="/" element={<HomePage />} />
//           <Route path="/check" element={<CheckPage />} />
          
//           {/* --- ADD THIS: Uncommented and added routes --- */}
//           <Route path="/history" element={<HistoryPage />} />
//           <Route path="/help" element={<HelpPage />} />
//           <Route path="/login" element={<LoginPage />} />
//           <Route path="/signup" element={<SignupPage />} /> 
//           <Route path="/profile" element={<ProfilePage />} />
//           {/* --- END ADD --- */}

//         </Routes>
//         {/* --- End Router --- */}
//       </main>

//       <footer className="app-footer">
//         <p>Disclaimer: This tool is for informational purposes only and is not a substitute for professional medical advice.</p>
//         <p>&copy; {new Date().getFullYear()} SafeMedsAI. All rights reserved.</p>
//       </footer>
//     </div>
//   );
// }

// export default App;
// frontend/src/App.jsx
import React from 'react';
import { Routes, Route, Link, useNavigate } from 'react-router-dom';

// --- CSS IMPORTS ---
import './App.css';
import './HomePage.css';
import './CheckPage.css';
import './AuthPage.css';
import './HistoryPage.css';
import './HelpPage.css';

// --- COMPONENT IMPORTS ---
import HomePage from './HomePage';
import CheckPage from './CheckPage';
import HistoryPage from './HistoryPage';
import LoginPage from './LoginPage';
import SignupPage from './SignupPage';
import ProfilePage from './ProfilePage';
import { useAuth } from './context/AuthContext';
import HelpPage from './HelpPage';

function App() {
  // Must be inside a Router (BrowserRouter typically in index.jsx)
  const { isAuthenticated, username, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/'); // Redirect to home page after logout
  };

  return (
    <div className="App">
      <nav className="app-nav">
        <Link to="/" className="nav-logo">SafeMedsAI</Link>

        <div className="nav-links">
          {/* Interaction Checker should point to /check */}
          <Link to="/check">Interaction Checker</Link>

          {isAuthenticated && <Link to="/history">View History</Link>}
          
          <Link to="/help">Help & FAQ</Link>
        </div>
        
        <div className="nav-auth">
          {isAuthenticated ? (
            <>
              {/* <- Changed to Link and classname unified with CSS (.navbar-username) */}
              <Link
                to="/profile"
                className="navbar-username"
                aria-label={`Go to ${username}'s profile`}
                title={`View ${username}'s profile`}
              >
                Hi, {username}
              </Link>

              <button onClick={handleLogout} className="logout-button">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/signup" className="signup-button">Sign Up</Link>
              <Link to="/login" className="login-button">Login</Link>
            </>
          )}
        </div>
      </nav>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/check" element={<CheckPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </main>

      <footer className="app-footer">
        <p>Disclaimer: This tool is for informational purposes only and is not a substitute for professional medical advice.</p>
        <p>&copy; {new Date().getFullYear()} SafeMedsAI. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;
