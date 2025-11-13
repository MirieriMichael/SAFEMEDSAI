// // frontend/src/HistoryPage.jsx
// import React, { useState, useEffect } from 'react';
// import { getScanHistory } from './services/api';
// import { useAuth } from './context/AuthContext';

// export default function HistoryPage() {
//   const [history, setHistory] = useState([]);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState(null);
//   const { isAuthenticated } = useAuth();

//   useEffect(() => {
//     if (!isAuthenticated) {
//       setError('You must be logged in to view this page.');
//       setLoading(false);
//       return;
//     }

//     const fetchHistory = async () => {
//       try {
//         setLoading(true);
//         const data = await getScanHistory();
//         setHistory(data);
//         setError(null);
//       } catch (err) {
//         setError(err.message || 'Could not fetch history.');
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchHistory();
//   }, [isAuthenticated]); // Re-run if auth state changes

//   const formatDate = (dateString) => {
//     return new Date(dateString).toLocaleDateString('en-US', {
//       year: 'numeric',
//       month: '2-digit',
//       day: '2-digit',
//     });
//   };

//   if (loading) {
//     return <div className="container">Loading your history...</div>;
//   }

//   if (error) {
//     return <div className="container error-message">{error}</div>;
//   }

//   return (
//     <div className="container history-page">
//       <h2>History</h2>
//       <p>Review your past drug interaction checks.</p>
      
//       <div className="history-section">
//         <h3>Drug Interaction Checks</h3>
//         <table className="history-table">
//           <thead>
//             <tr>
//               <th>Date</th>
//               <th>Drugs Checked</th>
//               <th>Actions</th>
//             </tr>
//           </thead>
//           <tbody>
//             {history.length > 0 ? (
//               history.map((scan) => (
//                 <tr key={scan.id}>
//                   <td>{formatDate(scan.created_at)}</td>
//                   <td>{scan.drug_names.join(', ')}</td>
//                   <td className="history-actions">
//                     <button className="action-button">Reopen</button>
//                     <button className="action-button delete">Delete</button>
//                     <button className="action-button">Export</button>
//                   </td>
//                 </tr>
//               ))
//             ) : (
//               <tr>
//                 <td colSpan="3">You have no scan history.</td>
//               </tr>
//             )}
//           </tbody>
//         </table>
//       </div>
      
//       {/* As requested, we are not implementing the Pill ID section */}
//     </div>
//   );
// }
// frontend/src/HistoryPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getScanHistory, deleteScanHistory } from './services/api';
import { useAuth } from './context/AuthContext';
import './HistoryPage.css'; // Ensure you have this CSS file

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  // Fetch history when the component mounts
  useEffect(() => {
    if (!isAuthenticated) {
      setError('You must be logged in to view this page.');
      setLoading(false);
      return;
    }

    const fetchHistory = async () => {
      try {
        setLoading(true);
        const data = await getScanHistory();
        setHistory(data);
        setError(null);
      } catch (err) {
        console.error("History fetch error:", err);
        setError('Could not fetch history. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [isAuthenticated]);

  // --- ACTION HANDLERS ---

  const handleDelete = async (scanId) => {
    // 1. Confirm user intent
    if (!window.confirm("Are you sure you want to delete this scan record?")) {
      return;
    }

    // 2. Optimistic UI update (remove it immediately so it feels fast)
    const previousHistory = [...history];
    setHistory(history.filter(item => item.id !== scanId));

    try {
      // 3. Call API
      await deleteScanHistory(scanId);
    } catch (err) {
      // 4. Revert if API fails
      alert("Failed to delete: " + err.message);
      setHistory(previousHistory);
    }
  };

  const handleReopen = (scan) => {
    // Pass the SAVED results back to the CheckPage
    navigate('/check', { 
      state: { 
        previousResults: scan.scan_results,
        reopenedDate: scan.created_at 
      } 
    });
  };

  // --- HELPERS ---

  const formatDate = (dateString) => {
    if (!dateString) return "Unknown Date";
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // --- RENDER ---

  if (loading) {
    return <div className="container loading-text">Loading your history...</div>;
  }

  if (error) {
    return <div className="container error-message">{error}</div>;
  }

  return (
    <div className="container history-page">
      <div className="history-header">
        <h2>Scan History</h2>
        <p>Review your past drug interaction checks.</p>
      </div>
      
      <div className="history-section">
        {history.length > 0 ? (
          <div className="table-responsive">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Drugs Detected</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {history.map((scan) => (
                  <tr key={scan.id}>
                    <td className="date-cell">{formatDate(scan.created_at)}</td>
                    <td className="drugs-cell">
                      {/* Handle case where drug_names might be simple strings or objects */}
                      {Array.isArray(scan.drug_names) 
                        ? scan.drug_names.join(', ') 
                        : "Unknown Drugs"}
                    </td>
                    <td className="history-actions text-right">
                      <button 
                        onClick={() => handleReopen(scan)} 
                        className="action-button reopen"
                        title="View these results again"
                      >
                        Reopen
                      </button>
                      <button 
                        onClick={() => handleDelete(scan.id)} 
                        className="action-button delete"
                        title="Delete this record"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-history">
            <p>You haven't scanned any drugs yet.</p>
            <button onClick={() => navigate('/check')} className="primary-button">
              Start a New Scan
            </button>
          </div>
        )}
      </div>
    </div>
  );
}