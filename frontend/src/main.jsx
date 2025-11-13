// // frontend/src/main.jsx

// import React from 'react';
// import ReactDOM from 'react-dom/client';
// // 1. Import BrowserRouter
// import { BrowserRouter } from 'react-router-dom'; 

// import App from './App';
// import './index.css'; // Your global styles

// ReactDOM.createRoot(document.getElementById('root')).render(
//   <React.StrictMode>
//     {/* 2. Wrap your entire <App /> component like this */}
//     <BrowserRouter>
//       <App />
//     </BrowserRouter>
//   </React.StrictMode>
// );
import React from 'react';
import ReactDOM from 'react-dom/client';
// 1. Import BrowserRouter
import { BrowserRouter } from 'react-router-dom'; 
// --- ADD THIS ---
import { AuthProvider } from './context/AuthContext';
// --- END ADD ---

import App from './App';
import './index.css'; // Your global styles

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* 2. Wrap your entire <App /> component like this */}
    <BrowserRouter>
      {/* --- ADD THIS WRAPPER --- */}
      <AuthProvider>
        <App />
      </AuthProvider>
      {/* --- END ADD --- */}
    </BrowserRouter>
  </React.StrictMode>
);