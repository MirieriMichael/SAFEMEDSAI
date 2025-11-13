// // // frontend/src/ProfilePage.jsx
// // import React, { useState, useEffect } from 'react';
// // import { useNavigate } from 'react-router-dom';
// // import { getUserProfile, deleteUserAccount } from './services/api';
// // import { useAuth } from './context/AuthContext';
// // import './AuthPage.css'; // Reuse the auth styling for consistency

// // export default function ProfilePage() {
// //   const [profile, setProfile] = useState(null);
// //   const [loading, setLoading] = useState(true);
// //   const { logout } = useAuth();
// //   const navigate = useNavigate();

// //   useEffect(() => {
// //     const loadProfile = async () => {
// //       try {
// //         const data = await getUserProfile();
// //         setProfile(data);
// //       } catch (err) {
// //         console.error(err);
// //       } finally {
// //         setLoading(false);
// //       }
// //     };
// //     loadProfile();
// //   }, []);

// //   const handleDeleteAccount = async () => {
// //     if (window.confirm("Are you sure? This will permanently delete your account and all scan history.")) {
// //       try {
// //         await deleteUserAccount();
// //         logout();
// //         navigate('/');
// //       } catch (err) {
// //         alert("Failed to delete account.");
// //       }
// //     }
// //   };

// //   if (loading) return <div className="container" style={{textAlign:'center', marginTop:'50px'}}>Loading profile...</div>;

// //   return (
// //     <div className="auth-container" style={{ maxWidth: '600px' }}>
// //       <h2 style={{ borderBottom: '1px solid #444', paddingBottom: '10px' }}>My Profile</h2>
      
// //       <div className="profile-section" style={{ color: '#e0e0e0', marginTop: '20px' }}>
// //         <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '30px' }}>
// //           <div style={{ 
// //             width: '80px', height: '80px', borderRadius: '50%', 
// //             background: '#1e90ff', display: 'flex', alignItems: 'center', justifyContent: 'center',
// //             fontSize: '2rem', fontWeight: 'bold', color: 'white'
// //           }}>
// //             {profile?.username.charAt(0).toUpperCase()}
// //           </div>
// //           <div>
// //             <h3 style={{ margin: 0, fontSize: '1.5rem' }}>{profile?.username}</h3>
// //             <p style={{ margin: '5px 0', color: '#a0a0a0' }}>{profile?.email}</p>
// //           </div>
// //         </div>

// //         <div className="stat-box" style={{ background: '#3a3f47', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
// //           <h4 style={{ margin: '0 0 5px 0', color: '#1193d4' }}>Total Interactions Checked</h4>
// //           <p style={{ fontSize: '1.5rem', margin: 0, fontWeight: 'bold' }}>{profile?.scan_count}</p>
// //         </div>

// //         <div style={{ marginTop: '40px', paddingTop: '20px', borderTop: '1px solid #444' }}>
// //           <h4 style={{ color: '#ff4d4d' }}>Danger Zone</h4>
// //           <p style={{ fontSize: '0.9rem', color: '#aaa', marginBottom: '15px' }}>
// //             Once you delete your account, there is no going back. Please be certain.
// //           </p>
// //           <button 
// //             onClick={handleDeleteAccount} 
// //             className="auth-button" 
// //             style={{ background: 'transparent', border: '1px solid #ff4d4d', color: '#ff4d4d' }}
// //           >
// //             Delete Account
// //           </button>
// //         </div>
// //       </div>
// //     </div>
// //   );
// // }
// // frontend/src/ProfilePage.jsx
// import React, { useState, useEffect } from 'react';
// import { useNavigate } from 'react-router-dom';
// import { getUserProfile, deleteUserAccount, clearUserHistory, updateUserProfile } from './services/api';
// import { useAuth } from './context/AuthContext';
// import './AuthPage.css'; 

// export default function ProfilePage() {
//   const [profile, setProfile] = useState(null);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState(null);
  
//   // Local state for inputs
//   const [allergyInput, setAllergyInput] = useState("");
//   const [conditionInput, setConditionInput] = useState("");

//   const { logout } = useAuth();
//   const navigate = useNavigate();

//   const loadProfile = async () => {
//     try {
//       setLoading(true);
//       const data = await getUserProfile();
//       setProfile(data);
//     } catch (err) {
//       setError("Failed to load profile.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     loadProfile();
//   }, []);

//   // --- HANDLERS ---

//   const handleAddTag = async (type, value) => {
//     if (!value.trim()) return;
    
//     const currentList = type === 'allergies' ? profile.allergies : profile.conditions;
//     const newList = [...currentList, value.trim()];
    
//     // Optimistic Update
//     setProfile({ ...profile, [type]: newList });
    
//     // Save to Backend
//     try {
//       await updateUserProfile({ [type]: newList });
//       if (type === 'allergies') setAllergyInput(""); 
//       else setConditionInput("");
//     } catch (err) {
//       alert("Failed to save.");
//     }
//   };

//   const handleRemoveTag = async (type, indexToRemove) => {
//     const currentList = type === 'allergies' ? profile.allergies : profile.conditions;
//     const newList = currentList.filter((_, i) => i !== indexToRemove);
    
//     setProfile({ ...profile, [type]: newList });
//     try {
//       await updateUserProfile({ [type]: newList });
//     } catch (err) {
//       alert("Failed to save.");
//     }
//   };

//   const handleClearHistory = async () => {
//     if (window.confirm("Clear your entire scan history? This cannot be undone.")) {
//       try {
//         await clearUserHistory();
//         setProfile({ ...profile, scan_count: 0 }); // Reset counter visually
//         alert("History cleared.");
//       } catch (err) {
//         alert("Error clearing history.");
//       }
//     }
//   };

//   const handleDeleteAccount = async () => {
//     if (window.confirm("Are you sure? This will permanently delete your account.")) {
//       try {
//         await deleteUserAccount();
//         logout();
//         navigate('/');
//       } catch (err) {
//         alert("Failed to delete account.");
//       }
//     }
//   };

//   // --- RENDER HELPERS ---
//   const TagList = ({ items, type }) => (
//     <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
//       {items?.map((item, idx) => (
//         <span key={idx} style={{ 
//           background: '#3a3f47', padding: '5px 10px', borderRadius: '15px', fontSize: '0.9rem',
//           display: 'flex', alignItems: 'center', gap: '8px'
//         }}>
//           {item}
//           <button 
//             onClick={() => handleRemoveTag(type, idx)}
//             style={{ background: 'none', border: 'none', color: '#ff4d4d', cursor: 'pointer', fontSize: '1rem', padding: 0 }}
//           >
//             &times;
//           </button>
//         </span>
//       ))}
//     </div>
//   );

//   if (loading) return <div className="container" style={{textAlign:'center', marginTop:'50px'}}>Loading...</div>;
//   if (error) return <div className="container error-message">{error}</div>;

//   return (
//     <div className="auth-container" style={{ maxWidth: '700px' }}>
//       <h2 style={{ borderBottom: '1px solid #444', paddingBottom: '10px' }}>My Profile</h2>
      
//       <div className="profile-header" style={{ display: 'flex', alignItems: 'center', gap: '20px', marginTop: '20px' }}>
//         <div style={{ 
//           width: '70px', height: '70px', borderRadius: '50%', background: '#1e90ff', 
//           display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', fontWeight: 'bold', color: 'white'
//         }}>
//           {profile?.username.charAt(0).toUpperCase()}
//         </div>
//         <div>
//           <h3 style={{ margin: 0 }}>{profile?.username}</h3>
//           <p style={{ margin: '5px 0', color: '#a0a0a0' }}>{profile?.email}</p>
//         </div>
//       </div>

//       {/* --- STATS SECTION --- */}
//       <div style={{ display: 'flex', gap: '15px', marginTop: '30px' }}>
//         <div style={{ flex: 1, background: '#3a3f47', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
//           <h4 style={{ margin: 0, color: '#1193d4' }}>{profile?.scan_count}</h4>
//           <small>Interactions Checked</small>
//         </div>
//         <div style={{ flex: 1, background: '#3a3f47', padding: '15px', borderRadius: '8px', textAlign: 'center' }}>
//           <h4 style={{ margin: 0, color: '#1193d4' }}>{profile?.allergies?.length || 0}</h4>
//           <small>Allergies Listed</small>
//         </div>
//       </div>

//       {/* --- HEALTH PROFILE SECTION --- */}
//       <h3 style={{ marginTop: '40px', borderBottom: '1px solid #444', paddingBottom: '10px' }}>Health Profile</h3>
      
//       {/* Allergies Input */}
//       <div style={{ marginTop: '20px' }}>
//         <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>My Allergies</label>
//         <div style={{ display: 'flex', gap: '10px' }}>
//           <input 
//             type="text" 
//             placeholder="e.g. Peanuts, Penicillin (Press Enter)" 
//             value={allergyInput}
//             onChange={(e) => setAllergyInput(e.target.value)}
//             onKeyDown={(e) => e.key === 'Enter' && handleAddTag('allergies', allergyInput)}
//             style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #555', background: '#222', color: 'white' }}
//           />
//           <button onClick={() => handleAddTag('allergies', allergyInput)} className="submit-button" style={{ padding: '8px 15px' }}>Add</button>
//         </div>
//         <TagList items={profile?.allergies} type="allergies" />
//       </div>

//       {/* Conditions Input */}
//       <div style={{ marginTop: '20px' }}>
//         <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>Medical Conditions</label>
//         <div style={{ display: 'flex', gap: '10px' }}>
//           <input 
//             type="text" 
//             placeholder="e.g. Asthma, Hypertension (Press Enter)" 
//             value={conditionInput}
//             onChange={(e) => setConditionInput(e.target.value)}
//             onKeyDown={(e) => e.key === 'Enter' && handleAddTag('conditions', conditionInput)}
//             style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #555', background: '#222', color: 'white' }}
//           />
//           <button onClick={() => handleAddTag('conditions', conditionInput)} className="submit-button" style={{ padding: '8px 15px' }}>Add</button>
//         </div>
//         <TagList items={profile?.conditions} type="conditions" />
//       </div>

//       {/* --- DANGER ZONE --- */}
//       <div style={{ marginTop: '50px', paddingTop: '20px', borderTop: '1px solid #444' }}>
//         <h4 style={{ color: '#ff4d4d' }}>Account Management</h4>
//         <div style={{ display: 'flex', gap: '15px', marginTop: '15px' }}>
//           <button 
//             onClick={handleClearHistory}
//             className="auth-button" 
//             style={{ background: '#4b5563', border: 'none', flex: 1 }}
//           >
//             Clear History
//           </button>
//           <button 
//             onClick={handleDeleteAccount} 
//             className="auth-button" 
//             style={{ background: 'transparent', border: '1px solid #ff4d4d', color: '#ff4d4d', flex: 1 }}
//           >
//             Delete Account
//           </button>
//         </div>
//       </div>

//     </div>
//   );
// }
// frontend/src/ProfilePage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  getUserProfile, 
  updateUserProfile, 
  deleteUserAccount, 
  clearUserHistory,
  getNotifications,
  markNotificationsRead
} from './services/api';
import { useAuth } from './context/AuthContext';
import './AuthPage.css'; // Reuse auth styling

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Inputs state
  const [allergyInput, setAllergyInput] = useState("");
  const [conditionInput, setConditionInput] = useState("");

  const { logout } = useAuth();
  const navigate = useNavigate();

  // Helper to refresh data
  const loadData = async () => {
    try {
      setLoading(true);
      const [profileData, notifData] = await Promise.all([
        getUserProfile(),
        getNotifications()
      ]);
      setProfile(profileData);
      setNotifications(notifData);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to load profile data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // --- HANDLERS ---

  const handleAvatarUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('avatar', file);

    try {
      // Optimistic loading state
      setLoading(true);
      await updateUserProfile(formData);
      await loadData(); // Reload to get new avatar URL
    } catch (err) {
      alert("Failed to upload image.");
      setLoading(false);
    }
  };

  const handleAddTag = async (type, value) => {
    if (!value.trim()) return;
    const currentList = type === 'allergies' ? profile.allergies : profile.conditions;
    const newList = [...currentList, value.trim()];
    
    // Optimistic update
    setProfile({ ...profile, [type]: newList });
    
    try {
      await updateUserProfile({ [type]: newList });
      if (type === 'allergies') setAllergyInput(""); 
      else setConditionInput("");
    } catch (err) {
      alert("Failed to save tag.");
      loadData(); // Revert on error
    }
  };

  const handleRemoveTag = async (type, indexToRemove) => {
    const currentList = type === 'allergies' ? profile.allergies : profile.conditions;
    const newList = currentList.filter((_, i) => i !== indexToRemove);
    
    setProfile({ ...profile, [type]: newList });
    try {
      await updateUserProfile({ [type]: newList });
    } catch (err) {
      alert("Failed to delete tag.");
      loadData();
    }
  };

  const handleClearHistory = async () => {
    if (window.confirm("Are you sure you want to clear your entire scan history?")) {
      try {
        await clearUserHistory();
        setProfile({ ...profile, scan_count: 0 });
        alert("History cleared.");
      } catch (err) {
        alert("Error clearing history.");
      }
    }
  };

  const handleDeleteAccount = async () => {
    if (window.confirm("WARNING: This will permanently delete your account and data. This cannot be undone.")) {
      try {
        await deleteUserAccount();
        logout();
        navigate('/');
      } catch (err) {
        alert("Failed to delete account.");
      }
    }
  };

  const handleMarkRead = async () => {
    try {
      await markNotificationsRead();
      // Update local state to show as read
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error("Failed to mark read");
    }
  };

  // --- RENDER HELPERS ---

  const TagList = ({ items, type }) => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
      {items?.map((item, idx) => (
        <span key={idx} style={{ 
          background: '#374151', padding: '6px 12px', borderRadius: '20px', fontSize: '0.9rem',
          display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid #4b5563'
        }}>
          {item}
          <button 
            onClick={() => handleRemoveTag(type, idx)}
            style={{ background: 'none', border: 'none', color: '#ff6b6b', cursor: 'pointer', padding: 0, fontSize: '1.1rem', lineHeight: 1 }}
          >
            &times;
          </button>
        </span>
      ))}
    </div>
  );

  if (loading && !profile) return <div className="container" style={{textAlign:'center', marginTop:'50px'}}>Loading...</div>;
  if (error) return <div className="container error-message">{error}</div>;

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="auth-container" style={{ maxWidth: '800px' }}>
      
      {/* --- HEADER & AVATAR --- */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '30px', borderBottom: '1px solid #444', paddingBottom: '30px' }}>
        <div style={{ position: 'relative' }}>
          {profile.avatar_url ? (
            <img 
              src={`http://127.0.0.1:8000${profile.avatar_url}`} 
              alt="Profile" 
              style={{ width: '100px', height: '100px', borderRadius: '50%', objectFit: 'cover', border: '3px solid #1193d4' }}
            />
          ) : (
            <div style={{ 
              width: '100px', height: '100px', borderRadius: '50%', background: '#1193d4', 
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '2.5rem', fontWeight: 'bold', color: 'white', border: '3px solid #1e293b'
            }}>
              {profile?.username.charAt(0).toUpperCase()}
            </div>
          )}
          
          {/* Upload Button Overlay */}
          <label htmlFor="avatar-upload" style={{
            position: 'absolute', bottom: 0, right: 0, 
            background: '#1e293b', borderRadius: '50%', padding: '8px', 
            cursor: 'pointer', border: '1px solid #444', display: 'flex'
          }} title="Change Profile Picture">
            <span className="material-symbols-outlined" style={{ fontSize: '18px', color: '#fff' }}>photo_camera</span>
          </label>
          <input type="file" id="avatar-upload" onChange={handleAvatarUpload} style={{ display: 'none' }} accept="image/*"/>
        </div>

        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0, fontSize: '2rem', color: 'white' }}>{profile?.username}</h2>
          <p style={{ margin: '5px 0', color: '#9ca3af' }}>{profile?.email}</p>
          <div style={{ marginTop: '10px' }}>
            <span style={{ background: '#374151', padding: '4px 10px', borderRadius: '4px', fontSize: '0.85rem', color: '#d1d5db' }}>
              Member since {new Date(profile?.date_joined).getFullYear()}
            </span>
          </div>
        </div>

        {/* Stat Box */}
        <div style={{ background: '#1e293b', padding: '15px 25px', borderRadius: '12px', textAlign: 'center', border: '1px solid #334155' }}>
          <h3 style={{ margin: 0, fontSize: '2rem', color: '#1193d4' }}>{profile?.scan_count}</h3>
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#9ca3af' }}>Scans Performed</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', marginTop: '30px' }}>
        
        {/* --- LEFT COL: MEDICAL PROFILE --- */}
        <div>
          <h3 style={{ color: '#fff', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className="material-symbols-outlined" style={{ color: '#1193d4' }}>medical_information</span>
            Health Profile
          </h3>
          
          <div style={{ marginBottom: '25px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: '#d1d5db', fontWeight: '500' }}>My Allergies</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input 
                type="text" 
                placeholder="Add allergy..." 
                value={allergyInput}
                onChange={(e) => setAllergyInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTag('allergies', allergyInput)}
                style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid #4b5563', background: '#1f2937', color: 'white' }}
              />
              <button onClick={() => handleAddTag('allergies', allergyInput)} className="submit-button" style={{ padding: '0 15px' }}>+</button>
            </div>
            <TagList items={profile?.allergies} type="allergies" />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: '#d1d5db', fontWeight: '500' }}>Medical Conditions</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input 
                type="text" 
                placeholder="Add condition..." 
                value={conditionInput}
                onChange={(e) => setConditionInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTag('conditions', conditionInput)}
                style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid #4b5563', background: '#1f2937', color: 'white' }}
              />
              <button onClick={() => handleAddTag('conditions', conditionInput)} className="submit-button" style={{ padding: '0 15px' }}>+</button>
            </div>
            <TagList items={profile?.conditions} type="conditions" />
          </div>
        </div>

        {/* --- RIGHT COL: NOTIFICATIONS & ACTIONS --- */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="material-symbols-outlined" style={{ color: '#fbbf24' }}>notifications</span>
              Inbox
              {unreadCount > 0 && <span style={{ background: '#ef4444', color: 'white', fontSize: '0.7rem', padding: '2px 8px', borderRadius: '10px', verticalAlign: 'middle' }}>{unreadCount} new</span>}
            </h3>
            {unreadCount > 0 && (
              <button onClick={handleMarkRead} style={{ background: 'none', border: 'none', color: '#1193d4', cursor: 'pointer', fontSize: '0.9rem' }}>
                Mark all read
              </button>
            )}
          </div>

          <div style={{ background: '#1f2937', borderRadius: '8px', border: '1px solid #374151', maxHeight: '300px', overflowY: 'auto' }}>
            {notifications.length > 0 ? (
              notifications.map((note) => (
                <div key={note.id} style={{ padding: '15px', borderBottom: '1px solid #374151', background: note.is_read ? 'transparent' : '#1e293b' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                    <strong style={{ color: note.is_read ? '#d1d5db' : '#fff' }}>{note.title}</strong>
                    <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{new Date(note.created_at).toLocaleDateString()}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: '#9ca3af' }}>{note.message}</p>
                </div>
              ))
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#6b7280' }}>No notifications</div>
            )}
          </div>

          {/* Danger Zone moved here */}
          <div style={{ marginTop: '40px' }}>
            <h4 style={{ color: '#ef4444', marginBottom: '15px', borderTop: '1px solid #374151', paddingTop: '20px' }}>Account Actions</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button 
                onClick={handleClearHistory}
                className="auth-button" 
                style={{ background: '#374151', border: '1px solid #4b5563' }}
              >
                Clear Scan History
              </button>
              <button 
                onClick={handleDeleteAccount} 
                className="auth-button" 
                style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#ef4444' }}
              >
                Delete Entire Account
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}