// // frontend/src/CheckPage.jsx
// import React, { useState, useRef, useCallback, useEffect } from 'react';
// import { checkInteractions, analyzeImages } from './services/api';
// import CollapsibleCard from './CollapsibleCard';

// // Import the new libraries for PDF export
// import jsPDF from 'jspdf';
// import html2canvas from 'html2canvas';

// // CSS is imported in App.jsx

// function CheckPage() {
//   // --- State and Refs ---
//   const [selectedFiles, setSelectedFiles] = useState([]);
//   const [drugInput, setDrugInput] = useState('');
//   const [results, setResults] = useState(null); // This now controls the page state
//   const [isLoading, setIsLoading] = useState(false);
//   const fileInputRef = useRef(null);
  
//   // Create a 'ref' to point to your results section
//   const resultsRef = useRef(null);

//   // --- Helper Functions ---
//   const handleFileChange = useCallback((event) => {
//     if (event.target.files.length > 0) {
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

//   const handleCheck = useCallback(async () => {
//     setIsLoading(true);
//     setResults(null); // Clear old results
//     const drugList = drugInput.split(',').map(drug => drug.trim()).filter(Boolean);

//     if (drugList.length < 2) {
//       alert("Please enter at least two drug names.");
//       setIsLoading(false);
//       return;
//     }
//     try {
//       const data = await checkInteractions(drugList);
//       setResults(data); // Set new results
//     } catch (error) {
//       alert(`Error: ${error.message}`);
//     } finally {
//       setIsLoading(false);
//     }
//   }, [drugInput]);

//   const handleScan = useCallback(async () => {
//     if (selectedFiles.length === 0) return;
//     setIsLoading(true);
//     setResults(null); // Clear old results

//     try {
//       const data = await analyzeImages(selectedFiles);
//       setResults(data); // Set new results
//     } catch (error) {
//       alert(`Error: ${error.message}`);
//     } finally {
//       setIsLoading(false);
//     }
//   }, [selectedFiles]);

//   // --- NEW: Function to reset the page back to the input state ---
//   const handleReset = () => {
//     setResults(null);
//     setSelectedFiles([]);
//     setDrugInput('');
//   };

//   // --- New PDF Download Function ---
//   const handleDownloadPDF = () => {
//     const reportElement = resultsRef.current;
//     if (!reportElement) return;

//     html2canvas(reportElement, { 
//       backgroundColor: '#1a262d',
//       scale: 2 
//     })
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
//         const yPos = (pdfHeight - imgHeight) / 2;

//         pdf.addImage(imgData, 'PNG', xPos, yPos, imgWidth, imgHeight);
//         pdf.save('SafeMedsAI_Interaction_Report.pdf');
//       });
//   };

//   return (
//     // --- THIS IS THE FIX ---
//     // This div gets the padding from App.css
//     <div className="checkpage-container">
      
//       {/* --- THIS IS THE NEW LOGIC --- */}
//       {/* If there are NO results (and not loading), show the input section */}
//       {!results && !isLoading && (
//         <section id="interactions" className="hero-section">
//           <h1>Your Medication Safety Net</h1>
//           <p className="subtitle">Upload drug labels or enter names to check for interactions.</p>
//           <div className="input-container">
//             <div className="input-section">
//               <h2>Check by Scanning a Label</h2>
//               <button onClick={handleUploadClick} className="upload-button">
//                 {selectedFiles.length > 0 ? `Add more images... (${selectedFiles.length} selected)` : 'Upload Image(s)'}
//               </button>
//               {selectedFiles.length > 0 && ( <button onClick={clearSelection} className="clear-button"> Clear Selection </button> )}
//               <input type="file" accept="image/*" multiple ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
//               <button onClick={handleScan} disabled={selectedFiles.length === 0 || isLoading} className="submit-button"> {isLoading ? 'Analyzing...' : 'Analyze Images'} </button>
//             </div>
//             <div className="input-section">
//               <h2>Check by Manual Entry</h2>
//               <input type="text" value={drugInput} onChange={(e) => setDrugInput(e.target.value)} placeholder="e.g., Aspirin, Warfarin" />
//               <button onClick={handleCheck} disabled={isLoading || !drugInput} className="submit-button"> Check Interactions </button>
//             </div>
//           </div>
//         </section>
//       )}
//       {/* --- END OF INPUT SECTION --- */}


//       {isLoading && <div className="loader"></div>}
      
//       {/* If there ARE results, show the results section */}
//       {results && (
//         <section className="results-section" ref={resultsRef}>
//           <h2>Analysis Report</h2>
//           <p className="summary-text">
//             This summary provides an overview of potential interactions between the medications you've listed. Please review the details carefully.
//           </p>
          
//           {results.found_drug_names && ( 
//             <div className="card info" style={{marginBottom: '40px'}}> 
//               <p><strong>Drugs Found:</strong> {results.found_drug_names.join(', ')}</p> 
//             </div> 
//           )}

//           <div className="severity-legend">
//             <h3>Severity Levels</h3>
//             <div className="severity-legend-grid">
//               <div className="severity-legend-item">
//                 <div className="severity-legend-icon major">dangerous</div>
//                 <div>
//                   <h4>Major</h4>
//                   <p>Significant health risks. Requires immediate attention.</p>
//                 </div>
//               </div>
//               <div className="severity-legend-item">
//                 <div className="severity-legend-icon moderate">warning</div>
//                 <div>
//                   <h4>Moderate</h4>
//                   <p>Could lead to health risks. May require adjustments.</p>
//                 </div>
//               </div>
//               <div className="severity-legend-item">
//                 <div className="severity-legend-icon minor">info</div>
//                 <div>
//                   <h4>Minor</h4>
//                   <p>Unlikely to cause harm but should be monitored.</p>
//                 </div>
//               </div>
//             </div>
//           </div>
            
//           <div className="results-grid">
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
//                   <p>No detailed drug information (like side effects or warnings) is available for these items in our database.</p>
//                 </div>
//               )}
//             </div>
//           </div>
          
//           {/* --- Add the Download Button --- */}
//           <div style={{textAlign: 'center', marginTop: '40px', borderTop: '1px solid #475569', paddingTop: '30px', display: 'flex', gap: '20px', justifyContent: 'center'}}>
//             <button onClick={handleDownloadPDF} className="submit-button" style={{backgroundColor: '#6b7280'}}>
//               Download Report
//             </button>
//             {/* --- NEW: Reset Button --- */}
//             <button onClick={handleReset} className="submit-button">
//               Check New Medications
//             </button>
//           </div>

//         </section>
//       )}
//       {/* --- END OF RESULTS SECTION --- */}

//     </div> 
//   );
// }

// export default CheckPage;
// frontend/src/CheckPage.jsx
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom'; // Added useLocation/useNavigate
import { checkInteractions, analyzeImages } from './services/api';
import CollapsibleCard from './CollapsibleCard';

// Import libraries for PDF export
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

// CSS is imported in App.jsx

function CheckPage() {
  const location = useLocation();
  const navigate = useNavigate();

  // --- State ---
  // 1. Initialize results from History if available (The "Reopen" fix)
  const [results, setResults] = useState(location.state?.previousResults || null);
  
  // 2. If files were passed from Home Page, capture them
  const [selectedFiles, setSelectedFiles] = useState(location.state?.files || []);
  
  const [drugInput, setDrugInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef(null);
  const resultsRef = useRef(null);

  // --- Auto-Run Logic ---
  // If we came from Home Page with files, but no results yet, run the scan automatically
  useEffect(() => {
    if (selectedFiles.length > 0 && !results && !isLoading) {
      handleScan();
    }
  }, []); // Run once on mount

  // --- Helper Functions ---
  const handleFileChange = useCallback((event) => {
    if (event.target.files.length > 0) {
      // If user picks files here, we add them
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
    // Clear the location state so refreshing doesn't re-trigger
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
      {/* Only show this if there are NO results yet */}
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

          {/* AI Summary */}
          {results.ai_summary && (
             <div className="card" style={{background: '#2a3b47', borderLeft: '4px solid #1193d4'}}>
                <h3>Summary</h3>
                <p>{results.ai_summary}</p>
             </div>
          )}

          {/* Results Grid */}
          <div className="results-grid" style={{marginTop: '30px'}}>
            
            {/* Interactions Column */}
            <div className="interactions-column">
              <h3>Potential Interactions</h3>
              {results.interactions?.length > 0 ? (
                results.interactions.map((interaction, index) => (
                  <div key={index} className={`card ${interaction.severity.toLowerCase()}`}>
                    <h4>{interaction.drug_1} & {interaction.drug_2}</h4>
                    <p><strong>Severity:</strong> {interaction.severity}</p>
                    <CollapsibleCard 
                      title="Interaction Details" 
                      content={interaction.description || "No description available."} 
                    />
                  </div>
                ))
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