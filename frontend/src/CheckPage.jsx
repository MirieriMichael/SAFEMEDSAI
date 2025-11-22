// // frontend/src/CheckPage.jsx
// import React, { useState, useRef, useCallback, useEffect } from 'react';
// import { useLocation, useNavigate } from 'react-router-dom'; // Added useLocation/useNavigate
// import { checkInteractions, analyzeImages } from './services/api';
// import CollapsibleCard from './CollapsibleCard';

// // Import libraries for PDF export
// import jsPDF from 'jspdf';
// import html2canvas from 'html2canvas';

// // CSS is imported in App.jsx

// function CheckPage() {
//   const location = useLocation();
//   const navigate = useNavigate();

//   // --- State ---
//   // 1. Initialize results from History if available (The "Reopen" fix)
//   const [results, setResults] = useState(location.state?.previousResults || null);
  
//   // 2. If files were passed from Home Page, capture them
//   const [selectedFiles, setSelectedFiles] = useState(location.state?.files || []);
  
//   const [drugInput, setDrugInput] = useState('');
//   const [isLoading, setIsLoading] = useState(false);
//   const fileInputRef = useRef(null);
//   const resultsRef = useRef(null);

//   // --- Auto-Run Logic ---
//   // If we came from Home Page with files, but no results yet, run the scan automatically
//   useEffect(() => {
//     if (selectedFiles.length > 0 && !results && !isLoading) {
//       handleScan();
//     }
//   }, []); // Run once on mount

//   // --- Helper Functions ---
//   const handleFileChange = useCallback((event) => {
//     if (event.target.files.length > 0) {
//       // If user picks files here, we add them
//       setSelectedFiles(prevFiles => [...prevFiles, ...Array.from(event.target.files)]);
//     }
//   }, []);

//   const handleUploadClick = useCallback(() => {
//     if (fileInputRef.current) {
//         fileInputRef.current.value = "";
//     }
//     fileInputRef.current.click();
//   }, []);

//   const clearSelection = useCallback(() => {
//     setSelectedFiles([]);
//   }, []);

//   // --- API Calls ---
//   const handleCheck = useCallback(async () => {
//     setIsLoading(true);
//     setResults(null);
//     const drugList = drugInput.split(',').map(drug => drug.trim()).filter(Boolean);

//     if (drugList.length < 2) {
//       alert("Please enter at least two drug names.");
//       setIsLoading(false);
//       return;
//     }
//     try {
//       const data = await checkInteractions(drugList);
//       setResults(data);
//     } catch (error) {
//       alert(`Error: ${error.message}`);
//     } finally {
//       setIsLoading(false);
//     }
//   }, [drugInput]);

//   const handleScan = async () => {
//     if (selectedFiles.length === 0) return;
//     setIsLoading(true);
//     setResults(null);

//     try {
//       const data = await analyzeImages(selectedFiles);
//       setResults(data);
//     } catch (error) {
//       alert(`Error: ${error.message}`);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleReset = () => {
//     setResults(null);
//     setSelectedFiles([]);
//     setDrugInput('');
//     // Clear the location state so refreshing doesn't re-trigger
//     navigate('/check', { replace: true, state: {} });
//   };

//   const handleDownloadPDF = () => {
//     const reportElement = resultsRef.current;
//     if (!reportElement) return;

//     html2canvas(reportElement, { backgroundColor: '#1a262d', scale: 2 })
//       .then((canvas) => {
//         const imgData = canvas.toDataURL('image/png');
//         const pdf = new jsPDF('p', 'mm', 'a4');
//         const pdfWidth = pdf.internal.pageSize.getWidth();
//         const pdfHeight = pdf.internal.pageSize.getHeight();
//         const canvasWidth = canvas.width;
//         const canvasHeight = canvas.height;
//         const ratio = Math.min(pdfWidth / canvasWidth, pdfHeight / canvasHeight);
//         const imgWidth = canvasWidth * ratio * 0.9;
//         const imgHeight = canvasHeight * ratio * 0.9;
//         const xPos = (pdfWidth - imgWidth) / 2;
//         const yPos = 10; 

//         pdf.addImage(imgData, 'PNG', xPos, yPos, imgWidth, imgHeight);
//         pdf.save('SafeMedsAI_Interaction_Report.pdf');
//       });
//   };

//   return (
//     <div className="checkpage-container">
      
//       {/* --- INPUT SECTION --- */}
//       {/* Only show this if there are NO results yet */}
//       {!results && !isLoading && (
//         <section id="interactions" className="hero-section">
//           <h1>Your Medication Safety Net</h1>
//           <p className="subtitle">Upload drug labels or enter names to check for interactions.</p>
          
//           <div className="input-container">
//             {/* Box 1: Upload */}
//             <div className="input-section">
//               <h2>Check by Scanning a Label</h2>
//               <button onClick={handleUploadClick} className="upload-button">
//                 {selectedFiles.length > 0 ? `Add more images... (${selectedFiles.length} selected)` : 'Upload Image(s)'}
//               </button>
              
//               {selectedFiles.length > 0 && (
//                  <div style={{marginTop: '10px'}}>
//                     {selectedFiles.map((f,i) => <div key={i} style={{fontSize:'0.8rem', color:'#ccc'}}>{f.name}</div>)}
//                     <button onClick={clearSelection} className="clear-button" style={{marginTop:'5px'}}> Clear Selection </button>
//                  </div>
//               )}
              
//               <input type="file" accept="image/*" multiple ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
//               <button onClick={handleScan} disabled={selectedFiles.length === 0} className="submit-button">Analyze Images</button>
//             </div>

//             {/* Box 2: Manual Entry */}
//             <div className="input-section">
//               <h2>Check by Manual Entry</h2>
//               <input 
//                 type="text" 
//                 value={drugInput} 
//                 onChange={(e) => setDrugInput(e.target.value)} 
//                 placeholder="e.g., Aspirin, Warfarin" 
//               />
//               <button onClick={handleCheck} disabled={!drugInput} className="submit-button">Check Interactions</button>
//             </div>
//           </div>
//         </section>
//       )}

//       {/* --- LOADING --- */}
//       {isLoading && (
//         <div className="loader-container" style={{textAlign: 'center', padding: '50px'}}>
//             <div className="loader"></div>
//             <p style={{marginTop: '20px', color: '#ccc'}}>Analyzing medications...</p>
//         </div>
//       )}
      
//       {/* --- RESULTS SECTION --- */}
//       {results && (
//         <section className="results-section" ref={resultsRef}>
//           <h2>Analysis Report</h2>
//           <p className="summary-text">
//             This summary provides an overview of potential interactions between the medications you've listed. Please review the details carefully.
//           </p>
          
//           {/* Drugs Found */}
//           {results.found_drug_names && ( 
//             <div className="card info" style={{marginBottom: '40px'}}> 
//               <p><strong>Drugs Found:</strong> {results.found_drug_names.join(', ')}</p> 
//             </div> 
//           )}

//           {/* AI Summary */}
//           {results.ai_summary && (
//              <div className="card" style={{background: '#2a3b47', borderLeft: '4px solid #1193d4'}}>
//                 <h3>Summary</h3>
//                 <p>{results.ai_summary}</p>
//              </div>
//           )}

//           {/* Results Grid */}
//           <div className="results-grid" style={{marginTop: '30px'}}>
            
//             {/* Interactions Column */}
//             <div className="interactions-column">
//               <h3>Potential Interactions</h3>
//               {results.interactions?.length > 0 ? (
//                 results.interactions.map((interaction, index) => (
//                   <div key={index} className={`card ${interaction.severity.toLowerCase()}`}>
//                     <h4>{interaction.drug_1} & {interaction.drug_2}</h4>
//                     <p><strong>Severity:</strong> {interaction.severity}</p>
//                     <CollapsibleCard 
//                       title="Interaction Details" 
//                       content={interaction.description || "No description available."} 
//                     />
//                   </div>
//                 ))
//               ) : ( 
//                 <div className="card info">
//                   <p>No interactions were found between the specified drugs in our database.</p>
//                 </div> 
//               )}
//             </div>

//             {/* Drug Details Column */}
//             <div className="details-column">
//               <h3>Drug Details</h3>
//               {results.drug_details?.length > 0 ? (
//                 results.drug_details.map((detail, index) => (
//                   <div key={index} className="card">
//                     <h4>{detail.name}</h4>
//                     {detail.druginfo?.administration && (
//                       <CollapsibleCard title="Administration" content={detail.druginfo.administration} />
//                     )}
//                     {detail.druginfo?.side_effects && (
//                       <CollapsibleCard title="Side Effects" content={detail.druginfo.side_effects} />
//                     )}
//                     {detail.druginfo?.warnings && (
//                       <CollapsibleCard title="Warnings" content={detail.druginfo.warnings} />
//                     )}
//                     {!detail.druginfo?.administration && !detail.druginfo?.side_effects && !detail.druginfo?.warnings && (
//                       <p style={{marginTop: '16px', paddingTop: '10px', borderTop: '1px solid #475569'}}>No detailed information available.</p>
//                     )}
//                   </div>
//                 ))
//               ) : (
//                 <div className="card unknown">
//                   <p>No detailed drug information is available for these items.</p>
//                 </div>
//               )}
//             </div>
//           </div>
          
//           {/* Footer Buttons */}
//           <div style={{textAlign: 'center', marginTop: '40px', borderTop: '1px solid #475569', paddingTop: '30px', display: 'flex', gap: '20px', justifyContent: 'center'}}>
//             <button onClick={handleDownloadPDF} className="submit-button" style={{backgroundColor: '#6b7280'}}>
//               Download Report
//             </button>
//             <button onClick={handleReset} className="submit-button">
//               Check New Medications
//             </button>
//           </div>

//         </section>
//       )}
//     </div> 
//   );
// }

// export default CheckPage;
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { checkInteractions, analyzeImages } from './services/api';
import CollapsibleCard from './CollapsibleCard';
import SafetyBadge from './components/SafetyBadge';

// Import libraries for PDF export
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

function CheckPage() {
  const location = useLocation();
  const navigate = useNavigate();

  // --- State ---
  const [results, setResults] = useState(location.state?.previousResults || null);
  const [selectedFiles, setSelectedFiles] = useState(location.state?.files || []);
  const [drugInput, setDrugInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef(null);
  const resultsRef = useRef(null);

  // --- Response normalization & debug logging ---
  const aiSummary = results?.ai_summary?.summary ?? results?.ai_summary ?? results?.summary ?? "";
  const foundDrugNames = results?.found_drug_names ?? results?.found_drugs ?? [];
  const drugDetails = Array.isArray(results?.drug_details)
    ? results.drug_details
    : (Array.isArray(results?.drugDetails) ? results.drugDetails : []);
  const interactions = Array.isArray(results?.interactions) ? results.interactions : [];

  // log whenever results changes (open browser console)
  useEffect(() => {
    if (results) {
      console.groupCollapsed("DEBUG: API results (CheckPage)");
      console.log("raw results:", results);
      console.log("aiSummary:", aiSummary);
      console.log("foundDrugNames:", foundDrugNames);
      console.log("drugDetails (count):", drugDetails.length);
      if (drugDetails[0]) console.log("drugDetails[0]:", drugDetails[0]);
      console.groupEnd();
    }
  }, [results]);


  // --- Auto-Run Logic ---
  useEffect(() => {
    if (selectedFiles.length > 0 && !results && !isLoading) {
      handleScan();
    }
  }, []); 

  // --- Helper Functions ---
  const handleFileChange = useCallback((event) => {
    if (event.target.files.length > 0) {
      setSelectedFiles(prevFiles => [...prevFiles, ...Array.from(event.target.files)]);
    }
  }, []);

  const handleUploadClick = useCallback(() => {
    if (fileInputRef.current) {
        fileInputRef.current.value = "";
    }
    fileInputRef.current.click();
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedFiles([]);
  }, []);

  // --- API Calls ---
  const handleCheck = useCallback(async () => {
    setIsLoading(true);
    setResults(null);
    const drugList = drugInput.split(',').map(drug => drug.trim()).filter(Boolean);

    if (drugList.length < 2) {
      alert("Please enter at least two drug names.");
      setIsLoading(false);
      return;
    }
    try {
      const data = await checkInteractions(drugList);
      setResults(data);
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [drugInput]);

  const handleScan = async () => {
    if (selectedFiles.length === 0) return;
    setIsLoading(true);
    setResults(null);

    try {
      const data = await analyzeImages(selectedFiles);
      setResults(data);
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResults(null);
    setSelectedFiles([]);
    setDrugInput('');
    navigate('/check', { replace: true, state: {} });
  };

  const handleDownloadPDF = () => {
    const reportElement = resultsRef.current;
    if (!reportElement) return;

    html2canvas(reportElement, { backgroundColor: '#1a262d', scale: 2 })
      .then((canvas) => {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('p', 'mm', 'a4');
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = pdf.internal.pageSize.getHeight();
        const canvasWidth = canvas.width;
        const canvasHeight = canvas.height;
        const ratio = Math.min(pdfWidth / canvasWidth, pdfHeight / canvasHeight);
        const imgWidth = canvasWidth * ratio * 0.9;
        const imgHeight = canvasHeight * ratio * 0.9;
        const xPos = (pdfWidth - imgWidth) / 2;
        const yPos = 10; 

        pdf.addImage(imgData, 'PNG', xPos, yPos, imgWidth, imgHeight);
        pdf.save('SafeMedsAI_Interaction_Report.pdf');
      });
  };

  return (
    <div className="checkpage-container">
      
      {/* --- INPUT SECTION --- */}
      {!results && !isLoading && (
        <section id="interactions" className="hero-section">
          <h1>Your Medication Safety Net</h1>
          <p className="subtitle">Upload drug labels or enter names to check for interactions.</p>
          
          <div className="input-container">
            {/* Box 1: Upload */}
            <div className="input-section">
              <h2>Check by Scanning a Label</h2>
              <button onClick={handleUploadClick} className="upload-button">
                {selectedFiles.length > 0 ? `Add more images... (${selectedFiles.length} selected)` : 'Upload Image(s)'}
              </button>
              
              {selectedFiles.length > 0 && (
                 <div style={{marginTop: '10px'}}>
                    {selectedFiles.map((f,i) => <div key={i} style={{fontSize:'0.8rem', color:'#ccc'}}>{f.name}</div>)}
                    <button onClick={clearSelection} className="clear-button" style={{marginTop:'5px'}}> Clear Selection </button>
                 </div>
              )}
              
              <input type="file" accept="image/*" multiple ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
              <button onClick={handleScan} disabled={selectedFiles.length === 0} className="submit-button">Analyze Images</button>
            </div>

            {/* Box 2: Manual Entry */}
            <div className="input-section">
              <h2>Check by Manual Entry</h2>
              <input 
                type="text" 
                value={drugInput} 
                onChange={(e) => setDrugInput(e.target.value)} 
                placeholder="e.g., Aspirin, Warfarin" 
              />
              <button onClick={handleCheck} disabled={!drugInput} className="submit-button">Check Interactions</button>
            </div>
          </div>
        </section>
      )}

      {/* --- LOADING --- */}
      {isLoading && (
        <div className="loader-container" style={{textAlign: 'center', padding: '50px'}}>
            <div className="loader"></div>
            <p style={{marginTop: '20px', color: '#ccc'}}>Analyzing medications...</p>
        </div>
      )}
      {/* DEBUG: raw JSON payload (remove in production) */}
      {results && (
        <details style={{marginBottom: '20px', color:'#ccc', padding: '10px', background: '#1a262d', border: '1px solid #475569', borderRadius: '4px'}}>
          <summary style={{cursor: 'pointer', fontWeight: '600', marginBottom: '8px'}}>🔍 DEBUG: Raw API Response (click to view)</summary>
          <pre style={{whiteSpace:'pre-wrap', maxHeight:'300px', overflow:'auto', color: '#e5e7eb', fontSize: '0.85rem', padding: '10px', background: '#0f172a', borderRadius: '4px'}}>{JSON.stringify(results, null, 2)}</pre>
        </details>
      )}

      {/* DEBUG: Test div to verify content visibility outside CollapsibleCard */}
      {results && results.drug_details && results.drug_details.length > 0 && results.drug_details[0].druginfo?.administration && (
        <div style={{marginBottom: '20px', padding: '10px', background: '#1e3a8a', border: '1px solid #3b82f6', borderRadius: '4px', color: '#e5e7eb'}}>
          <strong>🧪 DEBUG TEST:</strong> Direct render of administration text (should be visible):
          <div style={{marginTop: '8px', padding: '8px', background: '#0f172a', borderRadius: '4px'}}>
            {results.drug_details[0].druginfo.administration}
          </div>
        </div>
      )}

      {/* --- RESULTS SECTION --- */}
      {results && (
        <section className="results-section" ref={resultsRef}>
          <h2>Analysis Report</h2>
          <p className="summary-text">
            This summary provides an overview of potential interactions between the medications you've listed. Please review the details carefully.
          </p>
          
          {/* Drugs Found */}
          {results.found_drug_names && ( 
            <div className="card info" style={{marginBottom: '40px'}}> 
              <p><strong>Drugs Found:</strong> {results.found_drug_names.join(', ')}</p> 
            </div> 
          )}

          {/* AI Summary - FIXED SECTION */}
          {results.ai_summary?.summary && (
  <div className="card" style={{background: '#2a3b47', borderLeft: '4px solid #1193d4'}}>
      <h3>Summary</h3>
      <p>{results.ai_summary.summary}</p>
  </div>
)}


          {/* Results Grid */}
          <div className="results-grid" style={{marginTop: '30px'}}>
            
            {/* Interactions Column */}
            <div className="interactions-column">
              <h3>Potential Interactions</h3>
              {results.interactions?.length > 0 ? (
                results.interactions.map((interaction, index) => {
                  // Format severity for UI
                  const formatSeverity = (severity) => {
                    const severityUpper = (severity || '').toUpperCase();
                    if (severityUpper === 'LOW' || severityUpper === 'MINOR') {
                      return 'Low-level caution';
                    } else if (severityUpper === 'MODERATE') {
                      return 'Moderate interaction';
                    } else if (severityUpper === 'MAJOR' || severityUpper === 'HIGH') {
                      return 'Serious interaction';
                    }
                    return severity || 'Unknown';
                  };

                  // Clean description (remove technical jargon, make simple)
                  const cleanDescription = (desc) => {
                    if (!desc) return 'No description available.';
                    // Remove confidence/score/provenance mentions if present
                    let cleaned = desc
                      .replace(/confidence:\s*\d+\.?\d*/gi, '')
                      .replace(/score:\s*\d+\.?\d*/gi, '')
                      .replace(/provenance:\s*\w+/gi, '')
                      .trim();
                    // Ensure it ends with the disclaimer
                    if (!cleaned.endsWith('This tool does not replace professional medical advice.')) {
                      cleaned += ' This tool does not replace professional medical advice.';
                    }
                    return cleaned;
                  };

                  const formattedSeverity = formatSeverity(interaction.severity);
                  const cleanedDescription = cleanDescription(interaction.description);
                  
                  return (
                    <div key={index} className={`card ${(interaction.severity || '').toLowerCase()}`}>
                      <h4>{interaction.drug_1} & {interaction.drug_2}</h4>
                      <p><strong>Severity:</strong> {formattedSeverity}</p>
                      <CollapsibleCard 
                        title="Interaction Details" 
                        content={cleanedDescription} 
                      />
                    </div>
                  );
                })
              ) : ( 
                <div className="card info">
                  <p>No interactions were found between the specified drugs in our database.</p>
                </div> 
              )}
            </div>

            {/* Drug Details Column */}
            <div className="details-column">
              <h3>Drug Details</h3>
              {results.drug_details?.length > 0 ? (
                results.drug_details.map((detail, index) => (
                  <div key={index} className="card">
                    <h4>{detail.name}</h4>
                    {/* Safety Badge */}
                    <SafetyBadge safety={detail.safety_check || detail.druginfo?.safety_check} />
                    {detail.druginfo?.administration && (
                      <CollapsibleCard title="Administration" content={detail.druginfo.administration} />
                    )}
                    {detail.druginfo?.side_effects && (
                      <CollapsibleCard title="Side Effects" content={detail.druginfo.side_effects} />
                    )}
                    {detail.druginfo?.warnings && (
                      <CollapsibleCard title="Warnings" content={detail.druginfo.warnings} />
                    )}
                    {!detail.druginfo?.administration && !detail.druginfo?.side_effects && !detail.druginfo?.warnings && (
                      <p style={{marginTop: '16px', paddingTop: '10px', borderTop: '1px solid #475569'}}>No detailed information available.</p>
                    )}
                  </div>
                ))
              ) : (
                <div className="card unknown">
                  <p>No detailed drug information is available for these items.</p>
                </div>
              )}
            </div>
          </div>
          
          {/* Footer Buttons */}
          <div style={{textAlign: 'center', marginTop: '40px', borderTop: '1px solid #475569', paddingTop: '30px', display: 'flex', gap: '20px', justifyContent: 'center'}}>
            <button onClick={handleDownloadPDF} className="submit-button" style={{backgroundColor: '#6b7280'}}>
              Download Report
            </button>
            <button onClick={handleReset} className="submit-button">
              Check New Medications
            </button>
          </div>

        </section>
      )}
    </div> 
  );
}

export default CheckPage;