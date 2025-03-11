import React from 'react';
import { useProcess } from '../context/ProcessContext';

function LogViewer() {
  const { logs, setLogs } = useProcess();
  
  const clearLogs = () => {
    setLogs([]);
  };
  
  // Create a reference for auto-scrolling
  const logEndRef = React.useRef(null);
  
  // Auto-scroll to bottom when logs update
  React.useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Application Logs</h2>
        <button
          onClick={clearLogs}
          className="bg-gray-200 hover:bg-gray-300 text-gray-800 text-sm py-1 px-3 rounded"
        >
          Clear Logs
        </button>
      </div>
      
      <div className="bg-gray-900 text-gray-300 p-4 rounded font-mono text-sm h-96 overflow-y-auto">
        {logs.length === 0 ? (
          <p className="text-gray-500">No logs yet. Start processing to see logs appear here.</p>
        ) : (
          logs.map((log, index) => (
            <div key={index} className={`mb-1 ${
              log.type === 'error' 
                ? 'text-red-400' 
                : log.type === 'success'
                ? 'text-green-400'
                : 'text-gray-300'
            }`}>
              <span className="text-gray-500 select-none">
                [{log.timestamp.toLocaleTimeString()}]
              </span>
              {' '}
              <span className={`${
                log.type === 'error' 
                  ? 'text-red-500 font-semibold' 
                  : log.type === 'success' 
                  ? 'text-green-500 font-semibold' 
                  : ''
              }`}>
                {log.type.toUpperCase()}:
              </span>
              {' '}
              {log.message}
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}

export default LogViewer;