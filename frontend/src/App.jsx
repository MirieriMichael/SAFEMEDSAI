// frontend/src/App.jsx
import React, { useState, useRef, useCallback, useEffect } from 'react';
// We are adding DIAGNOSTIC_MESSAGE to the import list
import { checkInteractions, analyzeImages, DIAGNOSTIC_MESSAGE } from './services/api';
import CollapsibleCard from './CollapsibleCard';
import './App.css';

const FeatureIcon = ({ path }) => (
  <svg className="feature-icon" viewBox="0 0 24 24" fill="currentColor">
    <path d={path}></path>
  </svg>
);

function App() {
  // --- DIAGNOSTIC TEST ---
  useEffect(() => {
    // This will run once when the component first loads.
    console.log(DIAGNOSTIC_MESSAGE);
  }, []);

  const [selectedFiles, setSelectedFiles] = useState([]);
  const [drugInput, setDrugInput] = useState('');
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef(null);

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

  const handleScan = useCallback(async () => {
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
  }, [selectedFiles]);

  return (
    <div className="App">
      <nav className="app-nav">
        <div className="nav-logo">SafeMedsAI</div>
        <div className="nav-links">
          <a href="#interactions">Check Interactions</a>
          <a href="#features">Features</a>
        </div>
        <div className="nav-auth">
          <button className="signup-button">Sign Up</button>
          <button className="login-button">Login</button>
        </div>
      </nav>

      <main className="app-main">
        {/* The rest of your JSX is identical */}
        <section id="interactions" className="hero-section">
          <h1>Your Medication Safety Net</h1>
          <p className="subtitle">Effortlessly check drug interactions, identify pills by sight, and keep track of your medications for your peace of mind.</p>
          <div className="input-container">
            <div className="input-section">
              <h2>Check by Scanning a Label</h2>
              <button onClick={handleUploadClick} className="upload-button">
                {selectedFiles.length > 0 ? `Add more images... (${selectedFiles.length} selected)` : 'Upload Image(s)'}
              </button>
              {selectedFiles.length > 0 && ( <button onClick={clearSelection} className="clear-button"> Clear Selection </button> )}
              <input type="file" accept="image/*" multiple ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
              <button onClick={handleScan} disabled={selectedFiles.length === 0 || isLoading} className="submit-button"> {isLoading ? 'Analyzing...' : 'Analyze Images'} </button>
            </div>
            <div className="input-section">
              <h2>Check by Manual Entry</h2>
              <input type="text" value={drugInput} onChange={(e) => setDrugInput(e.target.value)} placeholder="e.g., Aspirin, Warfarin" />
              <button onClick={handleCheck} disabled={isLoading || !drugInput} className="submit-button"> Check Interactions </button>
            </div>
          </div>
        </section>
        {isLoading && <div className="loader"></div>}
        {results && (
          <section className="results-section">
            <h2>Analysis Report</h2>
            {results.found_drugs && ( <div className="card info"> <p><strong>Drugs found in image:</strong> {results.found_drugs.join(', ')}</p> </div> )}
            <div className="results-grid">
              <div className="interactions-column">
                <h3>Potential Interactions</h3>
                {results.interactions?.length > 0 ? (
                  results.interactions.map((interaction, index) => (
                    <div key={index} className={`card ${interaction.severity.toLowerCase()}`}>
                      <h4>{interaction.drug_a.name} & {interaction.drug_b.name}</h4>
                      <p><strong>Severity:</strong> {interaction.severity}</p>
                      <CollapsibleCard title="Interaction Details" content={interaction.description} />
                    </div>
                  ))
                ) : ( <div className="card info"><p>No interactions found between the selected drugs.</p></div> )}
              </div>
              <div className="details-column">
                <h3>Drug Details</h3>
                {results.drug_details?.map((detail, index) => (
                  <div key={index} className="card info">
                    <h4>{detail.name}</h4>
                    <CollapsibleCard title="Administration" content={detail.druginfo?.administration} />
                    <CollapsibleCard title="Side Effects" content={detail.druginfo?.side_effects} />
                    <CollapsibleCard title="Warnings" content={detail.druginfo?.warnings} />
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </main>
      <footer className="app-footer">
        <p>Disclaimer: This tool is for informational purposes only and is not a substitute for professional medical advice.</p>
        <p>&copy; {new Date().getFullYear()} SafeMedsAI. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;