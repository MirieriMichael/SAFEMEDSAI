// import React, { useState, useEffect } from 'react';
// import { useNavigate } from 'react-router-dom';
// import { 
//   getUserProfile, updateUserProfile, deleteUserAccount, 
//   clearUserHistory, getNotifications, markNotificationsRead,
//   setup2FA, verify2FA, disable2FA, sendEmailOTP
// } from './services/api';
// import { useAuth } from './context/AuthContext';
// import './AuthPage.css'; 

// export default function ProfilePage() {
//   const [profile, setProfile] = useState(null);
//   const [notifications, setNotifications] = useState([]);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState(null);
  
//   const [allergyInput, setAllergyInput] = useState("");
//   const [conditionInput, setConditionInput] = useState("");

//   // 2FA State
//   const [twoFaStep, setTwoFaStep] = useState(0); // 0 = hidden, 1 = choice, 2 = QR, 3 = Email
//   const [qrCode, setQrCode] = useState(null);
//   const [otpCode, setOtpCode] = useState("");
//   const [is2FAEnabled, setIs2FAEnabled] = useState(false); 

//   const { logout, user } = useAuth(); 
//   const navigate = useNavigate();

//   const loadData = async () => {
//     try {
//       setLoading(true);
//       const [profileData, notifData] = await Promise.all([
//         getUserProfile(), getNotifications()
//       ]);
//       setProfile(profileData);
//       setNotifications(notifData);
//       setIs2FAEnabled(profileData.is_2fa_enabled || false); 
//       setError(null);
//     } catch (err) {
//       console.error(err);
//       setError("Failed to load profile data.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => { loadData(); }, []);

//   // --- HANDLERS ---
//   const handleAvatarUpload = async (e) => {
//     const file = e.target.files[0];
//     if (!file) return;

//     const formData = new FormData();
//     formData.append('avatar', file);

//     try {
//       setLoading(true);
//       const updatedProfile = await updateUserProfile(formData);
//       setProfile(prev => ({...prev, ...updatedProfile}));
//     } catch (err) {
//       alert("Failed to upload image. Please try again.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleAddTag = async (type, value) => {
//     if (!value.trim()) return;
//     const currentList = type === 'allergies' ? profile.allergies : profile.conditions;
//     const newList = [...currentList, value.trim()];
    
//     setProfile({ ...profile, [type]: newList }); // Optimistic update
//     if (type === 'allergies') setAllergyInput(""); 
//     else setConditionInput("");

//     try {
//       await updateUserProfile({ [type]: newList });
//     } catch (err) { 
//       alert("Failed to save tag."); 
//       loadData(); 
//     }
//   };

//   const handleRemoveTag = async (type, indexToRemove) => {
//     const currentList = type === 'allergies' ? profile.allergies : profile.conditions;
//     const newList = currentList.filter((_, i) => i !== indexToRemove);
    
//     setProfile({ ...profile, [type]: newList }); // Optimistic update
    
//     try {
//       await updateUserProfile({ [type]: newList });
//     } catch (err) { 
//       alert("Failed to delete tag."); 
//       loadData(); 
//     }
//   };

//   const handleClearHistory = async () => {
//     if (window.confirm("Are you sure you want to delete your entire scan history?")) {
//       try {
//         await clearUserHistory();
//         setProfile({ ...profile, scan_count: 0 });
//         alert("History cleared.");
//       } catch (err) { alert("Error clearing history."); }
//     }
//   };

//   const handleDeleteAccount = async () => {
//     if (window.confirm("WARNING: Are you sure you want to permanently delete your account?")) {
//       try {
//         await deleteUserAccount();
//         logout();
//         navigate('/');
//       } catch (err) { alert("Failed to delete account."); }
//     }
//   };

//   const handleMarkRead = async () => {
//     try {
//       await markNotificationsRead();
//       setNotifications(notifications.map(n => ({ ...n, is_read: true })));
//     } catch (err) { console.error("Failed to mark read"); }
//   };

//   // --- 2FA HANDLERS ---
//   const handleSetupEmail2FA = async () => {
//     try {
//       await sendEmailOTP(); 
//       setTwoFaStep(3); // Go to "Enter Email Code"
//     } catch (err) {
//       alert("Failed to send code. Please try again.");
//     }
//   };

//   const handleSetupQR2FA = async () => {
//     try {
//       const data = await setup2FA(); 
//       setQrCode(data.qr_code); 
//       setTwoFaStep(2); // Go to "Scan QR"
//     } catch (err) {
//       alert("Failed to start QR setup.");
//     }
//   };

//   const handleConfirm2FA = async () => {
//     try {
//       await verify2FA(otpCode);
//       alert("2FA Enabled Successfully!");
//       setTwoFaStep(0);
//       setQrCode(null);
//       setOtpCode("");
//       setIs2FAEnabled(true);
//     } catch (err) {
//       alert("Invalid Code. Please try again.");
//     }
//   };

//   const handleDisable2FA = async () => {
//     if (window.confirm("Are you sure you want to disable 2FA?")) {
//       try {
//         await disable2FA();
//         setIs2FAEnabled(false);
//       } catch (err) { alert("Failed to disable."); }
//     }
//   };

//   // --- RENDER HELPERS ---
//   const TagList = ({ items, type }) => (
//     <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
//       {items?.map((item, idx) => (
//         <span key={idx} className="profile-tag" style={{ 
//            background: '#374151', padding: '6px 12px', borderRadius: '20px', fontSize: '0.9rem',
//            display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid #4b5563'
//         }}>
//           {item}
//           <button 
//             onClick={() => handleRemoveTag(type, idx)}
//             style={{ background: 'none', border: 'none', color: '#ff6b6b', cursor: 'pointer', padding: 0, fontSize: '1.1rem', lineHeight: 1 }}
//           > &times; </button>
//         </span>
//       ))}
//     </div>
//   );

//   if (loading && !profile) return <div className="auth-container" style={{textAlign:'center', marginTop:'50px'}}>Loading profile...</div>;
//   if (error) return <div className="auth-container error-banner" style={{maxWidth: '800px'}}>{error}</div>;
//   if (!profile) return <div className="auth-container" style={{textAlign:'center', marginTop:'50px'}}>Could not load profile.</div>;

//   const unreadCount = notifications.filter(n => !n.is_read).length;

//   return (
//     <div className="auth-container" style={{ maxWidth: '900px' }}>
      
//       {/* --- HEADER & AVATAR --- */}
//       <div style={{ display: 'flex', alignItems: 'center', gap: '30px', borderBottom: '1px solid #444', paddingBottom: '30px' }}>
//         <div style={{ position: 'relative' }}>
//           <img 
//             src={profile.avatar_url ? `${profile.avatar_url}` : "https://placehold.co/100x100/374151/FFF/png?text=User"} 
//             alt="Profile" 
//             style={{ 
//                width: '100px', height: '100px', borderRadius: '50%', 
//                objectFit: 'cover', border: '3px solid #1193d4', background: '#1e293b'
//             }}
//           />
//           <label htmlFor="avatar-upload" style={{
//              position: 'absolute', bottom: 0, right: 0, background: '#1e293b', 
//              borderRadius: '50%', padding: '8px', cursor: 'pointer', border: '1px solid #444'
//           }}>
//             <span className="material-symbols-outlined" style={{ fontSize: '18px', color: '#fff' }}>photo_camera</span>
//           </label>
//           <input type="file" id="avatar-upload" onChange={handleAvatarUpload} style={{ display: 'none' }} accept="image/*"/>
//         </div>
        
//         <div>
//           <h2 style={{ margin: 0, fontSize: '2rem' }}>{user?.username || profile.username}</h2>
//           <p style={{ color: '#aaa', margin: '5px 0 0 0' }}>{profile.email}</p>
//           <span style={{ display:'inline-block', marginTop:'10px', background:'#374151', padding:'4px 10px', borderRadius:'4px', fontSize:'0.8rem' }}>
//              Member since {new Date(profile.date_joined).getFullYear()}
//           </span>
//         </div>
        
//         <div style={{ marginLeft: 'auto', textAlign: 'center', background: '#1f2937', padding: '15px', borderRadius: '8px', border: '1px solid #374151' }}>
//           <span style={{ display: 'block', fontSize: '2rem', fontWeight: 'bold', color: '#1193d4' }}>{profile.scan_count}</span>
//           <span style={{ fontSize: '0.9rem', color: '#aaa' }}>Scans Performed</span>
//         </div>
//       </div>

//       {/* --- TWO COLUMN GRID --- */}
//       <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', marginTop: '30px' }}>
        
//         {/* --- LEFT COLUMN: HEALTH PROFILE --- */}
//         <div style={{ background: '#1f2937', padding: '20px', borderRadius: '8px', border: '1px solid #374151' }}>
//           <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid #374151', paddingBottom: '10px', marginBottom: '20px' }}>
//             <span className="material-symbols-outlined" style={{ color: '#1193d4' }}>health_and_safety</span>
//             Health Profile
//           </h3>
          
//           <div className="form-group">
//             <label>My Allergies</label>
//             <div style={{ display: 'flex', gap: '10px' }}>
//               <input 
//                 type="text" 
//                 placeholder="e.g., Penicillin" 
//                 value={allergyInput} 
//                 onChange={(e) => setAllergyInput(e.target.value)}
//               />
//               <button className="auth-button" style={{ width: 'auto', padding: '0 15px' }} onClick={() => handleAddTag('allergies', allergyInput)}>+</button>
//             </div>
//             <TagList items={profile.allergies} type="allergies" />
//           </div>

//           <div className="form-group" style={{ marginTop: '20px' }}>
//             <label>Medical Conditions</label>
//             <div style={{ display: 'flex', gap: '10px' }}>
//               <input 
//                 type="text" 
//                 placeholder="e.g., High Blood Pressure" 
//                 value={conditionInput} 
//                 onChange={(e) => setConditionInput(e.target.value)}
//               />
//               <button className="auth-button" style={{ width: 'auto', padding: '0 15px' }} onClick={() => handleAddTag('conditions', conditionInput)}>+</button>
//             </div>
//             <TagList items={profile.conditions} type="conditions" />
//           </div>
//         </div>

//         {/* --- RIGHT COLUMN: INBOX, SECURITY, ACTIONS --- */}
//         <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
//           {/* Inbox */}
//           <div>
//             <h3 style={{ color: '#fff', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '10px' }}>
//               <span className="material-symbols-outlined" style={{ color: '#facc15' }}>inbox</span>
//               Inbox
//               {unreadCount > 0 && <span style={{ background: '#ef4444', color: 'white', fontSize: '0.7rem', padding: '2px 6px', borderRadius: '10px' }}>{unreadCount}</span>}
//             </h3>
            
//             <div style={{ maxHeight: '200px', overflowY: 'auto', background: '#111827', padding: '10px', borderRadius: '8px', border: '1px solid #374151' }}>
//               {notifications.length > 0 ? notifications.map(n => (
//                 <div key={n.id} style={{ padding: '10px', borderBottom: '1px solid #333', opacity: n.is_read ? 0.6 : 1 }}>
//                   <strong style={{ display: 'block', color: '#1193d4' }}>{n.title}</strong>
//                   <p style={{ margin: '5px 0', fontSize: '0.9rem' }}>{n.message}</p>
//                   <small style={{ color: '#666' }}>{new Date(n.created_at).toLocaleDateString()}</small>
//                 </div>
//               )) : (
//                 <p style={{textAlign: 'center', color: '#888'}}>No notifications.</p>
//               )}
//             </div>
//             {unreadCount > 0 && (
//               <button onClick={handleMarkRead} className="auth-button" style={{ background: 'transparent', border: '1px solid #4b5563', width: '100%', marginTop: '10px' }}>
//                 Mark All as Read
//               </button>
//             )}
//           </div>

//           {/* Security */}
//           <div style={{ borderTop: '1px solid #374151', paddingTop: '20px' }}>
//             <h3 style={{ color: '#fff', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '10px' }}>
//               <span className="material-symbols-outlined" style={{ color: '#4ade80' }}>security</span>
//               Security
//             </h3>
//             {is2FAEnabled ? (
//               <button onClick={handleDisable2FA} className="auth-button" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#ef4444', width: '100%' }}>
//                 Disable Two-Factor Authentication
//               </button>
//             ) : (
//               <button onClick={() => setTwoFaStep(1)} className="auth-button" style={{ background: '#374151', border: '1px solid #4b5563', width: '100%' }}>
//                 Enable Two-Factor Authentication (2FA)
//               </button>
//             )}
//           </div>

//           {/* Account Actions */}
//           <div style={{ borderTop: '1px solid #374151', paddingTop: '20px' }}>
//             <h3 style={{ color: '#fff', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '10px' }}>
//               <span className="material-symbols-outlined" style={{color: '#f87171'}}>settings</span>
//               Account Actions
//             </h3>
//             <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
//               <button onClick={handleClearHistory} className="auth-button" style={{ background: '#374151', border: '1px solid #4b5563' }}>Clear Scan History</button>
//               <button onClick={handleDeleteAccount} className="auth-button" style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#ef4444' }}>Delete Entire Account</button>
//             </div>
//           </div>
//         </div>
//       </div>

//       {/* --- 2FA WIZARD MODAL --- */}
//       {twoFaStep > 0 && (
//         <div className="modal-backdrop" onClick={() => setTwoFaStep(0)}>
//           <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ textAlign: 'center', maxWidth: '400px', background: '#1e293b', padding: '30px', borderRadius: '12px', border: '1px solid #4b5563' }}>
            
//             {/* Step 1: Choose Method */}
//             {twoFaStep === 1 && (
//               <>
//                 <h3 style={{ marginTop: 0, color: 'white' }}>Choose 2FA Method</h3>
//                 <p style={{ color: '#aaa' }}>Select your preferred method for verification.</p>
//                 <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px' }}>
//                   <button onClick={handleSetupEmail2FA} className="auth-button" style={{ background: '#1193d4' }}>
//                     Email Me a Code
//                   </button>
//                   <button onClick={handleSetupQR2FA} className="auth-button" style={{ background: '#374151' }}>
//                     Use Authenticator App
//                   </button>
//                   <button onClick={() => setTwoFaStep(0)} className="auth-button" style={{ background: 'transparent', border: '1px solid #444', marginTop: '10px' }}>Cancel</button>
//                 </div>
//               </>
//             )}

//             {/* Step 2: Scan QR Code */}
//             {twoFaStep === 2 && (
//               <>
//                 <h3 style={{ marginTop: 0, color: 'white' }}>Use Authenticator App</h3>
//                 <p style={{ color: '#aaa' }}>Scan this with Google Authenticator or Authy.</p>
//                 {qrCode ? (
//                     <img src={qrCode} alt="2FA QR Code" style={{ margin: '20px auto', borderRadius: '8px', display: 'block', border: '5px solid white' ,// --- ADD THIS STYLE ---
//             maxWidth: '200px'}} />
//                 ) : (
//                     <p>Loading QR Code...</p>
//                 )}
//               </>
//             )}

//             {/* Step 3 (Alternate): Check Email */}
//             {twoFaStep === 3 && (
//               <>
//                 <h3 style={{ marginTop: 0, color: 'white' }}>Check Your Email</h3>
//                 <p style={{ color: '#aaa' }}>We sent a 6-digit code to {profile.email}.</p>
//               </>
//             )}

//             {/* Final Step: Verify Code (for both methods) */}
//             {(twoFaStep === 2 || twoFaStep === 3) && (
//               <>
//                 <input 
//                   type="text" 
//                   placeholder="Enter 6-digit Code" 
//                   value={otpCode}
//                   onChange={(e) => setOtpCode(e.target.value)}
//                   style={{ 
//                     display: 'block', width: '100%', margin: '15px 0', padding: '12px', 
//                     textAlign: 'center', fontSize: '1.2rem', letterSpacing: '5px', 
//                     borderRadius: '6px', border: '1px solid #4b5563', background: '#1f2937', color: 'white' 
//                   }}
//                 />
//                 <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
//                   <button onClick={handleConfirm2FA} className="auth-button">Verify & Enable</button>
//                   <button onClick={() => setTwoFaStep(0)} className="auth-button" style={{ background: '#444' }}>Cancel</button>
//                 </div>
//               </>
//             )}
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }
// frontend/src/ProfilePage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  getUserProfile, updateUserProfile, deleteUserAccount, 
  clearUserHistory, getNotifications, markNotificationsRead,
  setup2FA, verify2FA, disable2FA, sendEmailOTP,
  changePassword  // <--- 1. IMPORTED NEW FUNCTION
} from './services/api';
import { useAuth } from './context/AuthContext';
import './AuthPage.css'; 

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [allergyInput, setAllergyInput] = useState("");
  const [conditionInput, setConditionInput] = useState("");

  // 2FA State
  const [twoFaStep, setTwoFaStep] = useState(0); // 0 = hidden, 1 = choice, 2 = QR, 3 = Email
  const [qrCode, setQrCode] = useState(null);
  const [otpCode, setOtpCode] = useState("");
  const [is2FAEnabled, setIs2FAEnabled] = useState(false); 

  // --- 2. ADDED PASSWORD STATES ---
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    old_password: '',
    new_password: '',
    confirm_new_password: ''
  });
  const [passwordError, setPasswordError] = useState('');
  // ------------------------------

  const { logout, user } = useAuth(); 
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      setLoading(true);
      const [profileData, notifData] = await Promise.all([
        getUserProfile(), getNotifications()
      ]);
      setProfile(profileData);
      setNotifications(notifData);
      setIs2FAEnabled(profileData.is_2fa_enabled || false); 
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to load profile data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  // --- HANDLERS (Existing) ---
  const handleAvatarUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('avatar', file);
    try {
      setLoading(true);
      const updatedProfile = await updateUserProfile(formData);
      setProfile(prev => ({...prev, ...updatedProfile}));
    } catch (err) {
      alert("Failed to upload image. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async (type, value) => {
    if (!value.trim()) return;
    const currentList = type === 'allergies' ? profile.allergies : profile.conditions;
    const newList = [...currentList, value.trim()];
    setProfile({ ...profile, [type]: newList }); 
    if (type === 'allergies') setAllergyInput(""); 
    else setConditionInput("");
    try {
      await updateUserProfile({ [type]: newList });
    } catch (err) { 
      alert("Failed to save tag."); 
      loadData(); 
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
    if (window.confirm("Are you sure you want to delete your entire scan history?")) {
      try {
        await clearUserHistory();
        setProfile({ ...profile, scan_count: 0 });
        alert("History cleared.");
      } catch (err) { alert("Error clearing history."); }
    }
  };

  const handleDeleteAccount = async () => {
    if (window.confirm("WARNING: Are you sure you want to permanently delete your account?")) {
      try {
        await deleteUserAccount();
        logout();
        navigate('/');
      } catch (err) { alert("Failed to delete account."); }
    }
  };

  const handleMarkRead = async () => {
    try {
      await markNotificationsRead();
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (err) { console.error("Failed to mark read"); }
  };

  // --- 2FA HANDLERS (Existing) ---
  const handleSetupEmail2FA = async () => {
    try {
      await sendEmailOTP(); 
      setTwoFaStep(3); // Go to "Enter Email Code"
    } catch (err) {
      alert("Failed to send code. Please try again.");
    }
  };

  const handleSetupQR2FA = async () => {
    try {
      const data = await setup2FA(); 
      setQrCode(data.qr_code); 
      setTwoFaStep(2); // Go to "Scan QR"
    } catch (err) {
      alert("Failed to start QR setup.");
    }
  };

  const handleConfirm2FA = async () => {
    try {
      await verify2FA(otpCode);
      alert("2FA Enabled Successfully!");
      setTwoFaStep(0);
      setQrCode(null);
      setOtpCode("");
      setIs2FAEnabled(true);
    } catch (err) {
      alert("Invalid Code. Please try again.");
    }
  };

  const handleDisable2FA = async () => {
    if (window.confirm("Are you sure you want to disable 2FA?")) {
      try {
        await disable2FA();
        setIs2FAEnabled(false);
      } catch (err) { alert("Failed to disable."); }
    }
  };

  // --- 3. ADDED PASSWORD HANDLERS ---
  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError('');
    
    if (passwordForm.new_password !== passwordForm.confirm_new_password) {
      setPasswordError("New passwords do not match.");
      return;
    }
    
    try {
      await changePassword(
        passwordForm.old_password,
        passwordForm.new_password,
        passwordForm.confirm_new_password
      );
      alert("Password changed successfully!");
      setShowPasswordModal(false);
      setPasswordForm({ old_password: '', new_password: '', confirm_new_password: '' });
    } catch (err) {
      setPasswordError(err.message || "An unknown error occurred.");
    }
  };

  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target;
    setPasswordForm(prev => ({ ...prev, [name]: value }));
  };
  // ---------------------------------

  // --- RENDER HELPERS ---
  const TagList = ({ items, type }) => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
      {items?.map((item, idx) => (
        <span key={idx} className="profile-tag" style={{ 
           background: '#374151', padding: '6px 12px', borderRadius: '20px', fontSize: '0.9rem',
           display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid #4b5563'
        }}>
          {item}
          <button 
            onClick={() => handleRemoveTag(type, idx)}
            style={{ background: 'none', border: 'none', color: '#ff6b6b', cursor: 'pointer', padding: 0, fontSize: '1.1rem', lineHeight: 1 }}
          > &times; </button>
        </span>
      ))}
    </div>
  );

  if (loading && !profile) return <div className="auth-container" style={{textAlign:'center', marginTop:'50px'}}>Loading profile...</div>;
  if (error) return <div className="auth-container error-banner" style={{maxWidth: '800px'}}>{error}</div>;
  if (!profile) return <div className="auth-container" style={{textAlign:'center', marginTop:'50px'}}>Could not load profile.</div>;

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="auth-container" style={{ maxWidth: '900px' }}>
      
      {/* --- HEADER & AVATAR --- */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '30px', borderBottom: '1px solid #444', paddingBottom: '30px' }}>
        <div style={{ position: 'relative' }}>
          <img 
            src={profile.avatar_url || "https://placehold.co/128x128/374151/FFF/png?text=User"} 
            alt="Profile" 
            style={{ 
               width: '128px', height: '128px', borderRadius: '50%', 
               objectFit: 'cover', border: '3px solid #1193d4', background: '#1e293b'
            }}
            onError={(e) => {
              e.target.src = "https://placehold.co/128x128/374151/FFF/png?text=User";
            }}
          />
          <label htmlFor="avatar-upload" style={{
             position: 'absolute', bottom: 0, right: 0, background: '#1e293b', 
             borderRadius: '50%', padding: '8px', cursor: 'pointer', border: '1px solid #444'
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: '18px', color: '#fff' }}>photo_camera</span>
          </label>
          <input type="file" id="avatar-upload" onChange={handleAvatarUpload} style={{ display: 'none' }} accept="image/*"/>
        </div>
        
        <div>
          <h2 style={{ margin: 0, fontSize: '2rem' }}>{user?.username || profile.username}</h2>
          <p style={{ color: '#aaa', margin: '5px 0 0 0' }}>{profile.email}</p>
          <span style={{ display:'inline-block', marginTop:'10px', background:'#374151', padding:'4px 10px', borderRadius:'4px', fontSize:'0.8rem' }}>
             Member since {new Date(profile.date_joined).getFullYear()}
          </span>
        </div>
        
        <div style={{ marginLeft: 'auto', textAlign: 'center', background: '#1f2937', padding: '15px', borderRadius: '8px', border: '1px solid #374151' }}>
          <span style={{ display: 'block', fontSize: '2rem', fontWeight: 'bold', color: '#1193d4' }}>{profile.scan_count}</span>
          <span style={{ fontSize: '0.9rem', color: '#aaa' }}>Scans Performed</span>
        </div>
      </div>

      {/* --- TWO COLUMN GRID --- */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', marginTop: '30px' }}>
        
        {/* --- LEFT COLUMN: HEALTH PROFILE --- */}
        <div style={{ background: '#1f2937', padding: '20px', borderRadius: '8px', border: '1px solid #374151' }}>
          <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid #374151', paddingBottom: '10px', marginBottom: '20px' }}>
            <span className="material-symbols-outlined" style={{ color: '#1193d4' }}>health_and_safety</span>
            Health Profile
          </h3>
          
          <div className="form-group">
            <label>My Allergies</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input 
                type="text" 
                placeholder="e.g., Penicillin" 
                value={allergyInput} 
                onChange={(e) => setAllergyInput(e.target.value)}
              />
              <button className="auth-button" style={{ width: 'auto', padding: '0 15px' }} onClick={() => handleAddTag('allergies', allergyInput)}>+</button>
            </div>
            <TagList items={profile.allergies} type="allergies" />
          </div>

          <div className="form-group" style={{ marginTop: '20px' }}>
            <label>Medical Conditions</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input 
                type="text" 
                placeholder="e.g., High Blood Pressure" 
                value={conditionInput} 
                onChange={(e) => setConditionInput(e.target.value)}
              />
              <button className="auth-button" style={{ width: 'auto', padding: '0 15px' }} onClick={() => handleAddTag('conditions', conditionInput)}>+</button>
            </div>
            <TagList items={profile.conditions} type="conditions" />
          </div>
        </div>

        {/* --- RIGHT COLUMN: INBOX, SECURITY, ACTIONS --- */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Inbox */}
          <div style={{ background: '#1f2937', padding: '20px', borderRadius: '8px', border: '1px solid #374151' }}>
            <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid #374151', paddingBottom: '10px', marginBottom: '20px' }}>
              <span className="material-symbols-outlined" style={{ color: '#facc15' }}>inbox</span>
              Inbox
              {unreadCount > 0 && <span style={{ background: '#ef4444', color: 'white', fontSize: '0.7rem', padding: '2px 6px', borderRadius: '10px' }}>{unreadCount}</span>}
            </h3>
            
            <div style={{ maxHeight: '200px', overflowY: 'auto', paddingRight: '10px' }}>
              {notifications.length > 0 ? notifications.map(n => (
                <div key={n.id} style={{ paddingBottom: '10px', borderBottom: '1px solid #333', opacity: n.is_read ? 0.6 : 1, marginBottom: '10px' }}>
                  <strong style={{ display: 'block', color: '#1193d4' }}>{n.title}</strong>
                  <p style={{ margin: '5px 0', fontSize: '0.9rem' }}>{n.message}</p>
                  <small style={{ color: '#666' }}>{new Date(n.created_at).toLocaleDateString()}</small>
                </div>
              )) : (
                <p style={{textAlign: 'center', color: '#888'}}>No notifications.</p>
              )}
            </div>
            {unreadCount > 0 && (
              <button onClick={handleMarkRead} className="auth-button" style={{ background: 'transparent', border: '1px solid #4b5563', width: '100%', marginTop: '10px' }}>
                Mark All as Read
              </button>
            )}
          </div>

          {/* --- 4. MODIFIED SECURITY CARD --- */}
          <div style={{ background: '#1f2937', padding: '20px', borderRadius: '8px', border: '1px solid #374151' }}>
            <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid #374151', paddingBottom: '10px', marginBottom: '20px' }}>
              <span className="material-symbols-outlined" style={{ color: '#4ade80' }}>security</span>
              Security
            </h3>
            
            <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
              {is2FAEnabled ? (
                <button onClick={handleDisable2FA} className="auth-button" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#ef4444', width: '100%' }}>
                  Disable Two-Factor Authentication
                </button>
              ) : (
                <button onClick={() => setTwoFaStep(1)} className="auth-button" style={{ background: '#374151', border: '1px solid #4b5563', width: '100%' }}>
                  Enable Two-Factor Authentication (2FA)
                </button>
              )}

              {/* --- ADDED THIS BUTTON --- */}
              <button 
                onClick={() => setShowPasswordModal(true)} 
                className="auth-button" 
                style={{ background: '#374151', border: '1px solid #4b5563', width: '100%' }}>
                Change Password
              </button>
            </div>
          </div>

          {/* Account Actions */}
          <div style={{ background: '#1f2937', padding: '20px', borderRadius: '8px', border: '1px solid #374151' }}>
            <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid #374151', paddingBottom: '10px', marginBottom: '20px' }}>
              <span className="material-symbols-outlined" style={{color: '#f87171'}}>settings</span>
              Account Actions
            </h3>
            <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
              <button onClick={handleClearHistory} className="auth-button" style={{ background: '#374151', border: '1px solid #4b5563' }}>Clear Scan History</button>
              <button onClick={handleDeleteAccount} className="auth-button" style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#ef4444' }}>Delete Entire Account</button>
            </div>
          </div>
        </div>
      </div>

      {/* --- 5. ADDED PASSWORD MODAL --- */}
      {showPasswordModal && (
        <div className="modal-backdrop" onClick={() => setShowPasswordModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ textAlign: 'left', maxWidth: '400px', background: '#1e293b', padding: '30px', borderRadius: '12px', border: '1px solid #4b5563' }}>
            <h3 style={{ marginTop: 0, color: 'white' }}>Change Password</h3>
            
            {passwordError && <div className="error-banner">{passwordError}</div>}
            
            <form onSubmit={handlePasswordChange}>
              <div className="form-group">
                <label>Old Password</label>
                <input
                  type="password"
                  name="old_password"
                  value={passwordForm.old_password}
                  onChange={handlePasswordInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>New Password</label>
                <input
                  type="password"
                  name="new_password"
                  value={passwordForm.new_password}
                  onChange={handlePasswordInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Confirm New Password</label>
                <input
                  type="password"
                  name="confirm_new_password"
                  value={passwordForm.confirm_new_password}
                  onChange={handlePasswordInputChange}
                  required
                />
              </div>
              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button type="submit" className="auth-button">Save Changes</button>
                <button type="button" className="auth-button" style={{ background: '#444' }} onClick={() => setShowPasswordModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* ----------------------------- */}


      {/* --- 2FA WIZARD MODAL (Existing) --- */}
      {twoFaStep > 0 && (
        <div className="modal-backdrop" onClick={() => setTwoFaStep(0)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ textAlign: 'center', maxWidth: '400px', background: '#1e293b', padding: '30px', borderRadius: '12px', border: '1px solid #4b5563' }}>
            
            {/* Step 1: Choose Method */}
            {twoFaStep === 1 && (
              <>
                <h3 style={{ marginTop: 0, color: 'white' }}>Choose 2FA Method</h3>
                <p style={{ color: '#aaa' }}>Select your preferred method for verification.</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px' }}>
                  <button onClick={handleSetupEmail2FA} className="auth-button" style={{ background: '#1193d4' }}>
                    Email Me a Code
                  </button>
                  <button onClick={handleSetupQR2FA} className="auth-button" style={{ background: '#374151' }}>
                    Use Authenticator App
                  </button>
                  <button onClick={() => setTwoFaStep(0)} className="auth-button" style={{ background: 'transparent', border: '1px solid #444', marginTop: '10px' }}>Cancel</button>
                </div>
              </>
            )}

            {/* Step 2: Scan QR Code */}
            {twoFaStep === 2 && (
              <>
                <h3 style={{ marginTop: 0, color: 'white' }}>Use Authenticator App</h3>
                <p style={{ color: '#aaa' }}>Scan this with Google Authenticator or Authy.</p>
                {qrCode ? (
                    <img src={qrCode} alt="2FA QR Code" style={{ margin: '20px auto', borderRadius: '8px', display: 'block', border: '5px solid white', maxWidth: '200px'}} />
                ) : (
                    <p>Loading QR Code...</p>
                )}
              </>
            )}

            {/* Step 3 (Alternate): Check Email */}
            {twoFaStep === 3 && (
              <>
                <h3 style={{ marginTop: 0, color: 'white' }}>Check Your Email</h3>
                <p style={{ color: '#aaa' }}>We sent a 6-digit code to {profile.email}.</p>
              </>
            )}

            {/* Final Step: Verify Code (for both methods) */}
            {(twoFaStep === 2 || twoFaStep === 3) && (
              <>
                <input 
                  type="text" 
                  placeholder="Enter 6-digit Code" 
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  style={{ 
                    display: 'block', width: '100%', margin: '15px 0', padding: '12px', 
                    textAlign: 'center', fontSize: '1.2rem', letterSpacing: '5px', 
                    borderRadius: '6px', border: '1px solid #4b5563', background: '#1f2937', color: 'white' 
                  }}
                />
                <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                  <button onClick={handleConfirm2FA} className="auth-button">Verify & Enable</button>
                  <button onClick={() => setTwoFaStep(0)} className="auth-button" style={{ background: '#444' }}>Cancel</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}