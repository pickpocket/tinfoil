import React, { useState } from 'react';
import ProcessForm from './ProcessForm';
import JobList from './JobList';
import LogViewer from './LogViewer';
import Settings from './Settings';

function MainContent() {
  const [activeTab, setActiveTab] = useState('process');
  
  return (
    <div className="flex-1 overflow-auto">
      <div className="p-6">
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button 
                onClick={() => setActiveTab('process')}
                className={`mr-8 py-4 px-6 ${
                  activeTab === 'process'
                    ? 'border-b-2 border-primary-500 text-primary-600 font-medium'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Process Files
              </button>
              <button 
                onClick={() => setActiveTab('jobs')}
                className={`mr-8 py-4 px-6 ${
                  activeTab === 'jobs'
                    ? 'border-b-2 border-primary-500 text-primary-600 font-medium'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Jobs
              </button>
              <button 
                onClick={() => setActiveTab('logs')}
                className={`mr-8 py-4 px-6 ${
                  activeTab === 'logs'
                    ? 'border-b-2 border-primary-500 text-primary-600 font-medium'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Logs
              </button>
              <button 
                onClick={() => setActiveTab('settings')}
                className={`py-4 px-6 ${
                  activeTab === 'settings'
                    ? 'border-b-2 border-primary-500 text-primary-600 font-medium'
                    : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Settings
              </button>
            </nav>
          </div>
          
          <div className="p-6">
            {activeTab === 'process' && <ProcessForm />}
            {activeTab === 'jobs' && <JobList />}
            {activeTab === 'logs' && <LogViewer />}
            {activeTab === 'settings' && <Settings />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MainContent;