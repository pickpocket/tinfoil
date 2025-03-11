import React from 'react';
import { useProcess } from '../context/ProcessContext';

function ProcessForm() {
  const {
    inputPath,
    outputPath,
    forceUpdate, setForceUpdate,
    outputPattern, setOutputPattern,
    lyricsSource, setLyricsSource,
    tagFallback, setTagFallback,
    processing,
    selectInputPath,
    selectOutputPath,
    startProcessing
  } = useProcess();
  
  return (
    <div>
      <h2 className="text-xl font-semibold mb-6">Process Audio Files</h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">
            Input Directory
          </label>
          <div className="flex">
            <input
              type="text"
              value={inputPath}
              readOnly
              className="shadow appearance-none border rounded-l py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline flex-1"
              placeholder="Select a directory containing FLAC files"
            />
            <button
              onClick={selectInputPath}
              className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-r"
            >
              Browse
            </button>
          </div>
        </div>
        
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">
            Output Directory
          </label>
          <div className="flex">
            <input
              type="text"
              value={outputPath}
              readOnly
              className="shadow appearance-none border rounded-l py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline flex-1"
              placeholder="Select where organized files will be saved"
            />
            <button
              onClick={selectOutputPath}
              className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-r"
            >
              Browse
            </button>
          </div>
        </div>
        
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">
            Output Pattern
          </label>
          <input
            type="text"
            value={outputPattern}
            onChange={e => setOutputPattern(e.target.value)}
            className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          />
          <p className="text-gray-600 text-xs italic mt-1">
            Example: {'{artist}/{year} - {album}/{track:02d} - {title}'}
          </p>
        </div>
        
        <div>
          <label className="block text-gray-700 text-sm font-bold mb-2">
            Lyrics Source
          </label>
          <select
            value={lyricsSource}
            onChange={e => setLyricsSource(e.target.value)}
            className="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          >
            <option value="genius">Genius (text-only lyrics)</option>
            <option value="lrclib">LRCLIB (synchronized lyrics)</option>
            <option value="netease">NetEase (synchronized lyrics)</option>
            <option value="none">None</option>
          </select>
        </div>
        
        <div className="flex flex-col space-y-2">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={forceUpdate}
              onChange={e => setForceUpdate(e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-gray-700">
              Force Update (reprocess files even if metadata exists)
            </span>
          </label>
          
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={tagFallback}
              onChange={e => setTagFallback(e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-gray-700">
              Tag-based Fallback (use existing tags if AcoustID fails)
            </span>
          </label>
        </div>
        
        <div className="pt-4 mt-4 border-t border-gray-200">
          <button
            onClick={startProcessing}
            disabled={processing || !inputPath || !outputPath}
            className={`w-full bg-primary-600 hover:bg-primary-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline ${
              (processing || !inputPath || !outputPath) ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {processing ? 'Processing...' : 'Start Processing'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ProcessForm;