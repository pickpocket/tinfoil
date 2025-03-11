import React, { useState, useEffect } from 'react';

const NOTIFICATION_TYPES = {
  success: {
    icon: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path>
      </svg>
    ),
    classes: 'bg-green-100 text-green-800 border-green-300'
  },
  error: {
    icon: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"></path>
      </svg>
    ),
    classes: 'bg-red-100 text-red-800 border-red-300'
  },
  warning: {
    icon: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"></path>
      </svg>
    ),
    classes: 'bg-yellow-100 text-yellow-800 border-yellow-300'
  },
  info: {
    icon: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path>
      </svg>
    ),
    classes: 'bg-blue-100 text-blue-800 border-blue-300'
  }
};

function Notification({ 
  type = 'info', 
  message, 
  title, 
  duration = 5000, 
  onClose 
}) {
  const [show, setShow] = useState(true);
  
  // Auto close after duration
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        setShow(false);
        if (onClose) onClose();
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);
  
  // Get notification styling
  const notificationStyle = NOTIFICATION_TYPES[type] || NOTIFICATION_TYPES.info;
  
  // Handle close button
  const handleClose = () => {
    setShow(false);
    if (onClose) onClose();
  };
  
  if (!show) return null;
  
  return (
    <div className={`border-l-4 p-4 mb-4 ${notificationStyle.classes}`}>
      <div className="flex justify-between items-start">
        <div className="flex">
          <div className="flex-shrink-0">
            {notificationStyle.icon}
          </div>
          <div className="ml-3">
            {title && <h3 className="text-sm font-medium">{title}</h3>}
            <div className="text-sm">{message}</div>
          </div>
        </div>
        <button 
          type="button" 
          onClick={handleClose}
          className="ml-auto -mx-1.5 -my-1.5 rounded-full p-1.5 hover:bg-opacity-20 hover:bg-gray-500 focus:outline-none"
        >
          <span className="sr-only">Dismiss</span>
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
          </svg>
        </button>
      </div>
    </div>
  );
}

export default Notification;