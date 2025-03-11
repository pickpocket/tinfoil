import React from 'react';

function ProgressBar({ progress, status }) {
  const barColor = 
    status === 'completed' 
      ? 'bg-green-600' 
      : status === 'failed'
      ? 'bg-red-600'
      : 'bg-blue-600';
  
  const percentage = Math.round(progress * 100);
  
  return (
    <div className="w-full">
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div 
          className={`h-2.5 rounded-full ${barColor}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
      <span className="text-xs text-gray-500 mt-1">
        {percentage}%
      </span>
    </div>
  );
}

export default ProgressBar;