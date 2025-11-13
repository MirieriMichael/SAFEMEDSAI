// // frontend/src/HomePage.jsx
// import React, { useState } from 'react';
// import { Link } from 'react-router-dom'; // No useNavigate needed

// // --- THIS IS THE FIX: We only need one function for the modal ---
// const WelcomeModal = ({ onClose }) => (
//   <div className="modal-backdrop">
//     <div className="modal-content">
//       <button onClick={onClose} className="modal-close-btn">&times;</button>
//       <div className="modal-header">
//         <span className="material-symbols-outlined" style={{fontSize: '40px', color: '#1193d4'}}>
//           health_and_safety
//         </span>
//         <h2>Welcome to SafeMedsAI!</h2>
//         <p>Let's take a quick tour to show you how to get started.</p>
//       </div>
//       <div className="modal-steps">
//         <div className="modal-step">
//           <span>1</span>
//           <div>
//             <strong>Check Drug Interactions</strong>
//             <p>Start here to see if your medications are safe to take together.</p>
//           </div>
//         </div>
//         <div className="modal-step">
//           <span>2</span>
//           <div>
//             <strong>Review Your History</strong>
//             <p>Easily look back at your previous searches and results.</p>
//           </div>
//         </div>
//       </div>
//       <div className="modal-footer">
//         {/* --- Both buttons now just call onClose --- */}
//         <button onClick={onClose} className="modal-skip-btn">Skip Tour</button>
//         <button onClick={onClose} className="modal-start-btn">Get Started</button>
//       </div>
//     </div>
//   </div>
// );

// const HomePage = () => {
//   const [showModal, setShowModal] = useState(true);
  
//   const handleCloseModal = () => {
//     setShowModal(false);
//   };

//   return (
//     // This new div uses the padding from HomePage.css
//     <div className="homepage-container">
//       {showModal && <WelcomeModal onClose={handleCloseModal} />}
      
//       <section className="home-hero">
//         <h1>Your Medication Safety Net</h1>
//         <p>Effortlessly check drug interactions and keep track of your medications for your peace of mind.</p>
        
//         <Link to="/check" className="cta-button">
//           Analyze Drug Interactions
//         </Link>
//       </section>

//       <section className="home-features">
//         <div className="feature-card">
//           <span className="material-symbols-outlined feature-icon">history</span>
//           <h3>View History</h3>
//           <p>Securely access your past interaction checks anytime, anywhere.</p>
//         </div>
//         <div className="feature-card">
//           <span className="material-symbols-outlined feature-icon">help_outline</span>
//           <h3>Help & FAQ</h3>
//           <p>Find answers to common questions and learn how to get the most out of SafeMedsAI features.</p>
//         </div>
//         <div className="feature-card">
//           <span className="material-symbols-outlined feature-icon">privacy_tip</span>
//           <h3>Data Privacy</h3>
//           <p>Your searches are your own. We are committed to protecting your privacy.</p>
//         </div>
//       </section>
//     </div>
//   );
// };

// export default HomePage;
// frontend/src/HomePage.jsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

const WelcomeModal = ({ onClose }) => (
  <div className="modal-backdrop">
    <div className="modal-content">
      <button onClick={onClose} className="modal-close-btn">&times;</button>
      <div className="modal-header">
        <span className="material-symbols-outlined" style={{fontSize: '40px', color: '#1193d4'}}>
          health_and_safety
        </span>
        <h2>Welcome to SafeMedsAI!</h2>
        <p>Let's take a quick tour to show you how to get started.</p>
      </div>
      <div className="modal-steps">
        <div className="modal-step">
          <span>1</span>
          <div>
            <strong>Check Drug Interactions</strong>
            <p>Start here to see if your medications are safe to take together.</p>
          </div>
        </div>
        <div className="modal-step">
          <span>2</span>
          <div>
            <strong>Review Your History</strong>
            <p>Easily look back at your previous searches and results.</p>
          </div>
        </div>
      </div>
      <div className="modal-footer">
        <button onClick={onClose} className="modal-skip-btn">Skip Tour</button>
        <button onClick={onClose} className="modal-start-btn">Get Started</button>
      </div>
    </div>
  </div>
);

const HomePage = () => {
  const [showModal, setShowModal] = useState(true);
  
  const handleCloseModal = () => {
    setShowModal(false);
  };

  return (
    <div className="homepage-container">
      {showModal && <WelcomeModal onClose={handleCloseModal} />}
      
      <section className="home-hero">
        <h1>Your Medication Safety Net</h1>
        <p>Effortlessly check drug interactions and keep track of your medications for your peace of mind.</p>
        
        {/* This is the simple, correct link to the Check Page */}
        <Link to="/check" className="cta-button">
          Analyze Drug Interactions
        </Link>
      </section>

      <section className="home-features">
        <div className="feature-card">
          <span className="material-symbols-outlined feature-icon">history</span>
          <h3>View History</h3>
          <p>Securely access your past interaction checks anytime, anywhere.</p>
        </div>
        <div className="feature-card">
          <span className="material-symbols-outlined feature-icon">help_outline</span>
          <h3>Help & FAQ</h3>
          <p>Find answers to common questions and learn how to get the most out of SafeMedsAI features.</p>
        </div>
        <div className="feature-card">
          <span className="material-symbols-outlined feature-icon">privacy_tip</span>
          <h3>Data Privacy</h3>
          <p>Your searches are your own. We are committed to protecting your privacy.</p>
        </div>
      </section>
    </div>
  );
};

export default HomePage;