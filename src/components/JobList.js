import React from 'react';
import { useProcess } from '../context/ProcessContext';

function JobList() {
  const { jobs, openDirectory } = useProcess();
  
  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <svg className="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <h3 className="text-lg font-medium text-gray-900 mb-1">No jobs yet</h3>
        <p className="text-gray-500">Process files to see jobs appear here</p>
      </div>
    );
  }
  
  return (
    <div>
      <h2 className="text-xl font-semibold mb-6">Processing Jobs</h2>
      
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white">
          <thead>
            <tr>
              <th className="py-2 px-4 bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Job ID
              </th>
              <th className="py-2 px-4 bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="py-2 px-4 bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Progress
              </th>
              <th className="py-2 px-4 bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Details
              </th>
              <th className="py-2 px-4 bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {jobs.map(job => (
              <tr key={job.job_id}>
                <td className="py-4 px-4 text-sm text-gray-500 whitespace-nowrap">
                  <span className="font-mono">{job.job_id.substring(0, 8)}...</span>
                </td>
                <td className="py-4 px-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    job.status === 'completed' 
                      ? 'bg-green-100 text-green-800'
                      : job.status === 'failed'
                      ? 'bg-red-100 text-red-800'
                      : job.status === 'processing'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {job.status}
                  </span>
                </td>
                <td className="py-4 px-4 whitespace-nowrap">
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div 
                      className={`h-2.5 rounded-full ${
                        job.status === 'completed' 
                          ? 'bg-green-600' 
                          : job.status === 'failed'
                          ? 'bg-red-600'
                          : 'bg-blue-600'
                      }`}
                      style={{ width: `${job.progress * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-500">
                    {Math.round(job.progress * 100)}%
                  </span>
                </td>
                <td className="py-4 px-4 text-sm text-gray-500">
                  {job.status === 'completed' && job.result && (
                    <div>
                      <p>Processed: {job.result.processed_files}/{job.result.total_files} files</p>
                    </div>
                  )}
                  {job.status === 'failed' && job.error && (
                    <p className="text-red-500">{job.error}</p>
                  )}
                </td>
                <td className="py-4 px-4 whitespace-nowrap text-sm font-medium">
                  {job.status === 'completed' && job.result && job.result.output_dir && (
                    <button 
                      onClick={() => openDirectory(job.result.output_dir)}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      Open Folder
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default JobList;