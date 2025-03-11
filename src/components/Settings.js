import React, { useEffect, useState } from 'react';
import { useProcess } from '../context/ProcessContext';

function Settings() {
  const { 
    apiKey, setApiKey,
    validateSetup, addLog
  } = useProcess();
  
  const [setupStatus, setSetupStatus] = useState({
    isValidating: false,
    validation: null
  });
  
  const checkSetup = async () => {
    setSetupStatus({ isValidating: true, validation: null });
    
    try {
      const result = await validateSetup();
      setSetupStatus({ isValidating: false, validation: result });
    } catch (error) {
      setSetupStatus({ isValidating: false, validation: { valid: false } });
      addLog(`Validation error: ${error.message}`, 'error');
    }
  };
  
  // Check setup when API key changes
  useEffect(() => {
    if (apiKey) {
      const timer = setTimeout(() => {
        checkSetup();
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [apiKey]);
  
  return (
    <div>
      <h2 className="text-xl font-semibold mb-6">Application Settings</h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">
            AcoustID API Key
          </label>
          <div className="flex">
            <input
              type="text"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              className="shadow appearance-none border rounded-l py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline flex-1"
              placeholder="Enter your AcoustID API key"
            />
            <button
              onClick={checkSetup}
              disabled={setupStatus.isValidating}
              className={`${
                setupStatus.isValidating 
                  ? 'bg-gray-300 cursor-not-allowed' 
                  : 'bg-gray-300 hover:bg-gray-400'
              } text-gray-800 font-bold py-2 px-4 rounded-r`}
            >
              {setupStatus.isValidating ? 'Checking...' : 'Check'}
            </button>
          </div>
          <p className="text-gray-600 text-xs mt-1">
            Get an API key from <a href="https://acoustid.org/login" target="_blank" rel="noopener noreferrer" className="text-primary-600">acoustid.org</a>
          </p>
          
          {setupStatus.validation && (
            <div className={`mt-3 p-3 rounded ${
              setupStatus.validation.valid
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {setupStatus.validation.valid ? (
                <p>✓ AcoustID API key is valid</p>
              ) : (
                <div>
                  <p>✗ AcoustID API key is invalid or setup has issues</p>
                  {setupStatus.validation.validations && (
                    <ul className="list-disc list-inside mt-1 text-sm">
                      {Object.entries(setupStatus.validation.validations).map(([key, valid]) => (
                        <li key={key}>
                          {key}: {valid ? 'Valid' : 'Invalid'}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className="pt-4 border-t border-gray-200">
          <h3 className="text-lg font-semibold mb-2">About Tinfoil</h3>
          <p className="text-gray-700">
            Tinfoil is a powerful FLAC audio fingerprinting and metadata management application 
            that automatically identifies, tags, and organizes your music library. It uses acoustic 
            fingerprinting to identify tracks, fetches rich metadata from multiple sources, and 
            organizes files into a customizable directory structure.
          </p>
          
          <h4 className="font-semibold mt-4 mb-2">Features</h4>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>Acoustic Fingerprinting via Chromaprint/AcoustID</li>
            <li>Tag-Based Fallback when fingerprinting fails</li>
            <li>Rich Metadata from MusicBrainz</li>
            <li>Cover Art from the Cover Art Archive</li>
            <li>Multiple Lyrics Sources (Genius, LRCLIB, NetEase)</li>
            <li>Customizable File Organization</li>
          </ul>
          
          <h4 className="font-semibold mt-4 mb-2">Required Dependencies</h4>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>Python 3.8+</li>
            <li>Chromaprint (<code className="bg-gray-100 p-1 rounded">fpcalc</code> executable)</li>
            <li>AcoustID API key</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Settings;