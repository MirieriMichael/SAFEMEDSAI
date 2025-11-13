// // // // frontend/src/Navbar.jsx
// // // import React from 'react';
// // // import { Link, useNavigate } from 'react-router-dom';
// // // import { useAuth } from './context/AuthContext'; // Import our auth hook

// // // export default function Navbar() {
// // //   const { isAuthenticated, username, logout } = useAuth();
// // //   const navigate = useNavigate();

// // //   const handleLogout = () => {
// // //     logout();
// // //     navigate('/'); // Redirect to home page after logout
// // //   };

// // //   return (
// // //     <nav className="navbar">
// // //       <div className="navbar-left">
// // //         <Link to="/" className="navbar-brand">
// // //           SafeMedsAI
// // //         </Link>
// // //         <div className="navbar-links">
// // //           <Link to="/">Interaction Checker</Link>
// // //           {isAuthenticated && (
// // //             <Link to="/history">History</Link>
// // //           )}
// // //           <Link to="/faq">Help & FAQ</Link>
// // //         </div>
// // //       </div>
// // //       <div className="navbar-right">
// // //         {isAuthenticated ? (
// // //           <>
// // //             <span className="navbar-username">Hi, {username}</span>
// // //             <button onClick={handleLogout} className="navbar-button logout">
// // //               Logout
// // //             </button>
// // //           </>
// // //         ) : (
// // //           <>
// // //             <Link to="/login" className="navbar-button login">
// // //               Login
// // //             </Link>
// // //             <Link to="/signup" className="navbar-button signup">
// // //               Sign Up
// // //             </Link>
// // //           </>
// // //         )}
// // //       </div>
// // //     </nav>
// // //   );
// // // }
// // // frontend/src/Navbar.jsx
// // import React from 'react';
// // import { Link, useNavigate } from 'react-router-dom';
// // import { useAuth } from './context/AuthContext'; 

// // export default function Navbar() {
// //   const { isAuthenticated, username, logout } = useAuth();
// //   const navigate = useNavigate();

// //   const handleLogout = () => {
// //     logout();
// //     navigate('/'); 
// //   };

// //   return (
// //     <nav className="navbar">
// //       <div className="navbar-left">
// //         <Link to="/" className="navbar-brand">
// //           SafeMedsAI
// //         </Link>
// //         <div className="navbar-links">
// //           {/* --- THIS IS THE FIX --- */}
// //           {/* Changed to point to /check instead of / */}
// //           <Link to="/check">Interaction Checker</Link> 
// //           {/* --- END FIX --- */}
          
// //           {isAuthenticated && (
// //             <Link to="/history">History</Link>
// //           )}
// //           <Link to="/faq">Help & FAQ</Link>
// //         </div>
// //       </div>
// //       <div className="navbar-right">
// //         {isAuthenticated ? (
// //           <>
// //             <span className="navbar-username">Hi, {username}</span>
// //             <button onClick={handleLogout} className="navbar-button logout">
// //               Logout
// //             </button>
// //           </>
// //         ) : (
// //           <>
// //             <Link to="/login" className="navbar-button login">
// //               Login
// //             </Link>
// //             <Link to="/signup" className="navbar-button signup">
// //               Sign Up
// //             </Link>
// //           </>
// //         )}
// //       </div>
// //     </nav>
// //   );
// // }
// // frontend/src/Navbar.jsx
// // import React from 'react';
// // import { Link, useNavigate, useLocation } from 'react-router-dom';
// // import { useAuth } from './context/AuthContext'; 

// // export default function Navbar() {
// //   const { isAuthenticated, username, logout } = useAuth();
// //   const navigate = useNavigate();
// //   const location = useLocation();

// //   const handleLogout = () => {
// //     logout();
// //     navigate('/'); 
// //   };

// //   // Your existing fix for the interaction checker link
// //   const handleInteractionCheckClick = (e) => {
// //     e.preventDefault();
// //     if (location.pathname === '/check') {
// //       navigate(0); // Force reload if already on check page
// //     } else {
// //       navigate('/check');
// //     }
// //   };

// //   return (
// //     <nav className="navbar">
// //       <div className="navbar-left">
// //         <Link to="/" className="navbar-brand">
// //           SafeMedsAI
// //         </Link>
// //         <div className="navbar-links">
// //           {/* Interaction Checker Link */}
// //           <a href="/check" onClick={handleInteractionCheckClick}>Interaction Checker</a>
          
// //           {isAuthenticated && (
// //             <Link to="/history">History</Link>
// //           )}
// //           <Link to="/faq">Help & FAQ</Link>
// //         </div>
// //       </div>
      
// //       <div className="navbar-right">
// //         {isAuthenticated ? (
// //           <>
// //             {/* --- THIS IS THE FIX --- */}
// //             {/* We changed 'span' to 'Link' so it's clickable */}
// //             <Link 
// //               to="/profile" 
// //               className="navbar-username" 
// //               style={{ 
// //                 marginRight: '15px', 
// //                 textDecoration: 'none', 
// //                 color: '#e0e0e0', 
// //                 fontWeight: 'bold',
// //                 cursor: 'pointer'
// //               }}
// //             >
// //               Hi, {username}
// //             </Link>
// //             {/* --- END FIX --- */}
            
// //             <button onClick={handleLogout} className="navbar-button logout">
// //               Logout
// //             </button>
// //           </>
// //         ) : (
// //           <>
// //             <Link to="/login" className="navbar-button login">Login</Link>
// //             <Link to="/signup" className="navbar-button signup">Sign Up</Link>
// //           </>
// //         )}
// //       </div>
// //     </nav>
// //   );
// // }
// // frontend/src/Navbar.jsx
// import React from 'react';
// import { Link, useNavigate, useLocation } from 'react-router-dom';
// import { useAuth } from './context/AuthContext'; 

// export default function Navbar() {
//   const { isAuthenticated, username, logout } = useAuth();
//   const navigate = useNavigate();
//   const location = useLocation();

//   const handleLogout = () => {
//     logout();
//     navigate('/'); 
//   };

//   // Your existing fix for the interaction checker link
//   const handleInteractionCheckClick = (e) => {
//     e.preventDefault();
//     if (location.pathname === '/check') {
//       navigate(0); // Force reload if already on check page
//     } else {
//       navigate('/check');
//     }
//   };

//   return (
//     <nav className="navbar">
//       <div className="navbar-left">
//         <Link to="/" className="navbar-brand">
//           SafeMedsAI
//         </Link>
//         <div className="navbar-links">
//           {/* Interaction Checker Link */}
//           <a href="/check" onClick={handleInteractionCheckClick}>Interaction Checker</a>
          
//           {isAuthenticated && (
//             <Link to="/history">History</Link>
//           )}
//           <Link to="/faq">Help & FAQ</Link>
//         </div>
//       </div>
      
//       <div className="navbar-right">
//         {isAuthenticated ? (
//           <>
//             {/* --- THIS IS THE FIX --- */}
//             {/* We changed 'span' to 'Link' so it's clickable */}
//             <Link 
//               to="/profile" 
//               className="navbar-username" 
//               style={{ 
//                 marginRight: '15px', 
//                 textDecoration: 'none', 
//                 color: '#e0e0e0', 
//                 fontWeight: 'bold',
//                 cursor: 'pointer'
//               }}
//             >
//               Hi, {username}
//             </Link>
//             {/* --- END FIX --- */}
            
//             <button onClick={handleLogout} className="navbar-button logout">
//               Logout
//             </button>
//           </>
//         ) : (
//           <>
//             <Link to="/login" className="navbar-button login">Login</Link>
//             <Link to="/signup" className="navbar-button signup">Sign Up</Link>
//           </>
//         )}
//       </div>
//     </nav>
//   );
// }
// frontend/src/Navbar.jsx
import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

export default function Navbar() {
  const { isAuthenticated, username, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleInteractionCheckClick = (e) => {
    e.preventDefault();
    if (location.pathname === '/check') {
      navigate(0);
    } else {
      navigate('/check');
    }
  };

  // Defensive profile click handler to confirm click reaches React
  const handleProfileClick = (e) => {
    e.preventDefault();
    console.log('PROFILE CLICKED — Navbar handler fired');
    // navigate programmatically (works even if Link has issues)
    navigate('/profile');
  };

  return (
    <nav className="navbar app-nav" aria-label="Main navigation">
      <div className="navbar-left">
        <Link to="/" className="nav-logo navbar-brand">SafeMedsAI</Link>
        <div className="navbar-links nav-links" role="navigation" aria-label="Primary">
          <Link to="/check" onClick={handleInteractionCheckClick}>Interaction Checker</Link>
          {isAuthenticated && <Link to="/history">History</Link>}
          <Link to="/faq">Help & FAQ</Link>
        </div>
      </div>

      <div className="navbar-right">
        {isAuthenticated ? (
          <>
            {/* Defensive clickable profile */}
            <a
              href="/profile"
              onClick={handleProfileClick}
              className="navbar-username"
              role="button"
              tabIndex={0}
              aria-label={`Go to ${username}'s profile`}
              onKeyDown={(e) => { if (e.key === 'Enter') handleProfileClick(e); }}
            >
              Hi, {username}
            </a>

            <button onClick={handleLogout} className="navbar-button logout">Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" className="navbar-button login">Login</Link>
            <Link to="/signup" className="navbar-button signup">Sign Up</Link>
          </>
        )}
      </div>
    </nav>
  );
}
