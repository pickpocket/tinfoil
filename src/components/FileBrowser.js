import React from 'react';

function FileBrowser({ 
  label, 
  path, 
  placeholder = 'Select a path...', 
  onBrowse, 
  readOnly = true,
  helperText 
}) {
  return (
    <div>
      <label className="block text-gray-700 text-sm font-bold mb-2">
        {label}
      </label>
      <div className="flex">
        <input
          type="text"
          value={path}
          readOnly={readOnly}
          className="shadow appearance-none border rounded-l py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline flex-1"
          placeholder={placeholder}
        />
        <button
          onClick={onBrowse}
          className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-r"
        >
          Browse
        </button>
      </div>
      {helperText && (
        <p className="text-gray-600 text-xs italic mt-1">{helperText}</p>
      )}
    </div>
  );
}

export default FileBrowser;