import React from 'react';

const STATUS_COLORS = {
  pending: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800'
  },
  processing: {
    bg: 'bg-blue-100',
    text: 'text-blue-800'
  },
  completed: {
    bg: 'bg-green-100',
    text: 'text-green-800'
  },
  failed: {
    bg: 'bg-red-100',
    text: 'text-red-800'
  }
};

function StatusBadge({ status }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.pending;
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
      {status}
    </span>
  );
}

export default StatusBadge;