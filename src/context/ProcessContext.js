import React, { createContext, useState, useContext, useEffect } from 'react';

const ProcessContext = createContext();

export function useProcess() {
  return useContext(ProcessContext);
}

export function ProcessProvider({ children }) {
  // Configuration states
  const [inputPath, setInputPath] = useState('');
  const [outputPath, setOutputPath] = useState('');
  const [forceUpdate, setForceUpdate] = useState(false);
  const [outputPattern, setOutputPattern] = useState('{artist}/{year} - {album}/{track:02d} - {title}');
  const [lyricsSource, setLyricsSource] = useState('genius');
  const [tagFallback, setTagFallback] = useState(true);
  const [apiKey, setApiKey] = useState('');

  // Processing states
  const [processing, setProcessing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [jobs, setJobs] = useState([]);
  
  // Function to add a log entry
  const addLog = (message, type = 'info') => {
    setLogs(prev => [...prev, { message, type, timestamp: new Date() }]);
  };
  
  // Listen for Python logs
  useEffect(() => {
    if (window.api) {
      window.api.onPythonLog((data) => {
        addLog(data, 'info');
      });
      
      window.api.onPythonError((data) => {
        addLog(data, 'error');
      });
      
      window.api.onPythonExit((code) => {
        addLog(`Python process exited with code ${code}`, code === 0 ? 'info' : 'error');
      });
    }
  }, []);
  
  // Function to start processing
  const startProcessing = async () => {
    if (!inputPath || !outputPath) {
      addLog('Input and output paths are required', 'error');
      return;
    }
    
    setProcessing(true);
    addLog(`Processing started: ${inputPath} -> ${outputPath}`);
    
    try {
      // Make API call to the Python backend
      const response = await fetch('http://localhost:8000/process_directory', {
        method: 'POST',
        body: JSON.stringify({
          input_path: inputPath,
          output_path: outputPath,
          force_update: forceUpdate,
          output_pattern: outputPattern,
          lyrics_source: lyricsSource,
          tag_fallback: tagFallback,
          api_key: apiKey
        }),
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      if (data.job_id) {
        setJobs(prev => [...prev, data]);
        addLog(`Job created: ${data.job_id}`);
        
        // Poll for job status
        pollJobStatus(data.job_id);
      } else {
        addLog('Failed to create job', 'error');
      }
    } catch (error) {
      addLog(`Error: ${error.message}`, 'error');
    } finally {
      setProcessing(false);
    }
  };
  
  // Function to poll job status
  const pollJobStatus = async (jobId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/status/${jobId}`);
        const data = await response.json();
        
        setJobs(prev => 
          prev.map(job => 
            job.job_id === jobId ? { ...job, ...data } : job
          )
        );
        
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          addLog(`Job ${jobId} ${data.status}`, data.status === 'completed' ? 'success' : 'error');
        }
      } catch (error) {
        addLog(`Error polling job ${jobId}: ${error.message}`, 'error');
        clearInterval(interval);
      }
    }, 1000);
  };
  
  // Function to select input path
  const selectInputPath = async () => {
    try {
      const paths = await window.api.selectDirectory();
      if (paths && paths.length > 0) {
        setInputPath(paths[0]);
        addLog(`Input path set: ${paths[0]}`);
      }
    } catch (error) {
      addLog(`Error selecting input path: ${error.message}`, 'error');
    }
  };
  
  // Function to select output path
  const selectOutputPath = async () => {
    try {
      const paths = await window.api.selectOutputDirectory();
      if (paths && paths.length > 0) {
        setOutputPath(paths[0]);
        addLog(`Output path set: ${paths[0]}`);
      }
    } catch (error) {
      addLog(`Error selecting output path: ${error.message}`, 'error');
    }
  };
  
  // Function to open directory
  const openDirectory = async (dirPath) => {
    try {
      await window.api.openDirectory(dirPath);
    } catch (error) {
      addLog(`Error opening directory: ${error.message}`, 'error');
    }
  };
  
  // Function to validate setup
  const validateSetup = async () => {
    try {
      const response = await fetch(`http://localhost:8000/validate_setup?api_key=${apiKey}`);
      const data = await response.json();
      
      if (data.valid) {
        addLog('Setup validation successful', 'success');
      } else {
        Object.entries(data.validations).forEach(([key, valid]) => {
          if (!valid) {
            addLog(`Validation failed for ${key}`, 'error');
          }
        });
      }
      
      return data;
    } catch (error) {
      addLog(`Error validating setup: ${error.message}`, 'error');
      return { valid: false };
    }
  };
  
  const value = {
    inputPath, setInputPath,
    outputPath, setOutputPath,
    forceUpdate, setForceUpdate,
    outputPattern, setOutputPattern,
    lyricsSource, setLyricsSource,
    tagFallback, setTagFallback,
    processing, setProcessing,
    logs, addLog, setLogs,
    jobs, setJobs,
    apiKey, setApiKey,
    startProcessing,
    selectInputPath,
    selectOutputPath,
    openDirectory,
    validateSetup
  };
  
  return (
    <ProcessContext.Provider value={value}>
      {children}
    </ProcessContext.Provider>
  );
}