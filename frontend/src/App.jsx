// frontend/src/App.jsx
import React, { useState,useEffect } from 'react';
import { getHealth } from './services/api';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [drugInput, setDrugInput] = useState('');
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState('Checking...');

  useEffect(() => {
    getHealth()
      .then(data => {
        if (data.status === 'ok') {
          setBackendStatus('Backend is healthy!');
        }
      })
      .catch(error => {
        console.error(error);
        setBackendStatus('Backend is unreachable.');
      });
  }, []); // The empty array ensures this runs only once
  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleScan = () => {
    // We will add the API call logic here later
    console.log('Scanning file:', selectedFile);
  };
  
  const handleCheck = () => {
    // We will add the API call logic here later
    console.log('Checking drugs:', drugInput);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>SafeMedsAI 🌿</h1>
       <p>Intelligent Drug Interaction Advisor</p>
        
        <div className="status-check">
          <p>Connection Status: {backendStatus}</p>
        </div>
        
        <div className="input-section">
          <h2>Check by Scanning a Label</h2>
          <input type="file" onChange={handleFileChange} />
          <button onClick={handleScan} disabled={!selectedFile || isLoading}>
            {isLoading ? 'Scanning...' : 'Scan Image'}
          </button>
        </div>

        <div className="input-section">
          <h2>Check by Manual Entry</h2>
          <input 
            type="text"
            value={drugInput}
            onChange={(e) => setDrugInput(e.target.value)}
            placeholder="e.g., Paracetamol, Metronidazole" 
          />
          <button onClick={handleCheck} disabled={!drugInput || isLoading}>
            {isLoading ? 'Checking...' : 'Check Interactions'}
          </button>
        </div>

        {results && (
          <div className="results-section">
            <h2>Interaction Results</h2>
            <pre>{JSON.stringify(results, null, 2)}</pre>
          </div>
        )}
      </header>
    </div>
  );
}

export default App;