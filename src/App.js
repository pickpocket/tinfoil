import React, { useState, useEffect } from 'react';

function App() {
  const [inputPath, setInputPath] = useState('');
  const [outputPath, setOutputPath] = useState('');
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [apiStatus, setApiStatus] = useState('unknown');
  
  // Add a log entry
  const addLog = (message, type = 'info') => {
    setLogs(prev => [...prev, { 
      id: Date.now(), 
      message, 
      type, 
      timestamp: new Date() 
    }]);
  };
  
  // Initialize and check API connection
  useEffect(() => {
    addLog('Application initialized');
    
    // Setup Python log listeners
    if (window.api) {
      window.api.onPythonLog((data) => {
        addLog(`Python: ${data}`, 'info');
      });
      
      window.api.onPythonError((data) => {
        addLog(`Python: ${data}`, 'error');
      });
    }
    
    // Check API connection
    checkApiConnection();
  }, []);
  
  // Check API connection
  const checkApiConnection = async () => {
    try {
      addLog('Checking Python API connection...');
      setApiStatus('checking');
      
      const response = await fetch('http://localhost:8000/config');
      const data = await response.json();
      
      addLog(`API connection successful! Tinfoil version: ${data.version}`, 'success');
      setApiStatus('connected');
    } catch (error) {
      addLog(`API connection failed: ${error.message}`, 'error');
      setApiStatus('error');
    }
  };
  
  // Select input directory
  const handleSelectInput = async () => {
    try {
      const paths = await window.api.selectDirectory();
      if (paths && paths.length > 0) {
        setInputPath(paths[0]);
        addLog(`Selected input directory: ${paths[0]}`, 'info');
      }
    } catch (error) {
      addLog(`Error selecting input directory: ${error.message}`, 'error');
    }
  };
  
  // Select output directory
  const handleSelectOutput = async () => {
    try {
      const paths = await window.api.selectOutputDirectory();
      if (paths && paths.length > 0) {
        setOutputPath(paths[0]);
        addLog(`Selected output directory: ${paths[0]}`, 'info');
      }
    } catch (error) {
      addLog(`Error selecting output directory: ${error.message}`, 'error');
    }
  };
  
  // Process files
  const handleProcess = async () => {
    if (!inputPath || !outputPath) {
      addLog('Please select input and output directories first', 'error');
      return;
    }
    
    try {
      setIsProcessing(true);
      addLog('Starting processing...', 'info');
      
      const response = await fetch('http://localhost:8000/process_directory', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          input_path: inputPath,
          output_path: outputPath,
          force_update: false,
          lyrics_source: 'genius'
        })
      });
      
      const data = await response.json();
      
      if (data.job_id) {
        addLog(`Processing job started: ${data.job_id}`, 'success');
        // In a full app, you would poll for job status here
      } else {
        addLog('Failed to start processing job', 'error');
      }
    } catch (error) {
      addLog(`Error processing files: ${error.message}`, 'error');
    } finally {
      setIsProcessing(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto p-4">
        {/* Header */}
        <header className="bg-white shadow-md rounded-lg p-4 mb-6">
          <h1 className="text-2xl font-bold text-gray-800">Tinfoil Audio Manager</h1>
          <p className="text-gray-600">FLAC Audio Fingerprinting and Metadata Management</p>
          
          <div className="mt-2">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              apiStatus === 'connected' ? 'bg-green-100 text-green-800' :
              apiStatus === 'error' ? 'bg-red-100 text-red-800' :
              'bg-yellow-100 text-yellow-800'
            }`}>
              API Status: {apiStatus}
            </span>
            {apiStatus !== 'connected' && (
              <button 
                onClick={checkApiConnection}
                className="ml-2 text-xs text-blue-600 hover:text-blue-800"
              >
                Retry
              </button>
            )}
          </div>
        </header>
        
        {/* Main Content */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* File Processing Form */}
          <div className="md:col-span-2">
            <div className="bg-white shadow-md rounded-lg p-4">
              <h2 className="text-xl font-semibold mb-4">Process Files</h2>
              
              <div className="space-y-4">
                {/* Input Directory */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Input Directory</label>
                  <div className="flex">
                    <input
                      type="text"
                      value={inputPath}
                      readOnly
                      className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-l-md bg-gray-50"
                      placeholder="Select input directory"
                    />
                    <button
                      onClick={handleSelectInput}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-r-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Browse
                    </button>
                  </div>
                </div>
                
                {/* Output Directory */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Output Directory</label>
                  <div className="flex">
                    <input
                      type="text"
                      value={outputPath}
                      readOnly
                      className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-l-md bg-gray-50"
                      placeholder="Select output directory"
                    />
                    <button
                      onClick={handleSelectOutput}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-r-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Browse
                    </button>
                  </div>
                </div>
                
                {/* Process Button */}
                <div className="pt-4">
                  <button
                    onClick={handleProcess}
                    disabled={isProcessing || !inputPath || !outputPath || apiStatus !== 'connected'}
                    className={`w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                      (isProcessing || !inputPath || !outputPath || apiStatus !== 'connected') ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    {isProcessing ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Processing...
                      </>
                    ) : (
                      'Process Files'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          {/* Logs Panel */}
          <div className="md:col-span-1">
            <div className="bg-white shadow-md rounded-lg p-4 h-full">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Logs</h2>
                <button 
                  onClick={() => setLogs([])}
                  className="text-xs text-gray-600 hover:text-gray-800"
                >
                  Clear
                </button>
              </div>
              
              <div className="bg-gray-900 rounded-md h-64 overflow-y-auto p-2 text-sm font-mono">
                {logs.length === 0 ? (
                  <p className="text-gray-500 text-xs">No logs yet.</p>
                ) : (
                  logs.map(log => (
                    <div key={log.id} className={`mb-1 ${
                      log.type === 'error' ? 'text-red-400' :
                      log.type === 'success' ? 'text-green-400' :
                      'text-gray-300'
                    }`}>
                      <span className="text-gray-500 text-xs select-none">
                        [{log.timestamp.toLocaleTimeString()}]
                      </span>{' '}
                      {log.message}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;