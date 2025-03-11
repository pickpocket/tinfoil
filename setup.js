const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Setup the readline interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Paths
const PYTHON_DIR = path.join(__dirname, 'python');
const VENV_DIR = path.join(PYTHON_DIR, 'venv');

console.log('Tinfoil Electron Setup');
console.log('======================');

// Check if Python is installed
function checkPython() {
  try {
    const version = execSync('python --version').toString().trim();
    console.log(`Python detected: ${version}`);
    return true;
  } catch (error) {
    try {
      const version = execSync('python3 --version').toString().trim();
      console.log(`Python detected: ${version}`);
      return true;
    } catch (err) {
      console.error('Python not found. Please install Python 3.8 or later.');
      return false;
    }
  }
}

// Check if virtual environment exists
function checkVenv() {
  return fs.existsSync(VENV_DIR);
}

// Create virtual environment
function createVenv() {
  console.log('Creating Python virtual environment...');
  try {
    execSync('python -m venv venv', { cwd: PYTHON_DIR });
    return true;
  } catch (error) {
    try {
      execSync('python3 -m venv venv', { cwd: PYTHON_DIR });
      return true;
    } catch (err) {
      console.error(`Failed to create virtual environment: ${err.message}`);
      return false;
    }
  }
}

// Install Python dependencies
function installDependencies() {
  console.log('Installing Python dependencies...');
  try {
    // Determine pip path based on OS
    const pipCmd = process.platform === 'win32' ? 
      path.join(VENV_DIR, 'Scripts', 'pip') : 
      path.join(VENV_DIR, 'bin', 'pip');
    
    execSync(`"${pipCmd}" install -r requirements.txt`, { cwd: PYTHON_DIR });
    console.log('Dependencies installed successfully.');
    return true;
  } catch (error) {
    console.error(`Failed to install dependencies: ${error.message}`);
    return false;
  }
}

// Check for fpcalc (Chromaprint)
function checkFpcalc() {
  console.log('Checking for fpcalc (Chromaprint)...');
  
  try {
    // Try to run fpcalc
    execSync('fpcalc -version');
    console.log('fpcalc found in PATH.');
    return true;
  } catch (error) {
    // Check common installation locations
    let fpcalcPath = null;
    
    if (process.platform === 'win32') {
      const programFiles = process.env['ProgramFiles'] || 'C:\\Program Files';
      const programFilesX86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
      
      const paths = [
        path.join(programFiles, 'Chromaprint', 'fpcalc.exe'),
        path.join(programFilesX86, 'Chromaprint', 'fpcalc.exe')
      ];
      
      for (const p of paths) {
        if (fs.existsSync(p)) {
          fpcalcPath = p;
          break;
        }
      }
    } else if (process.platform === 'darwin') {
      // macOS paths
      const paths = [
        '/usr/local/bin/fpcalc',
        '/opt/homebrew/bin/fpcalc'
      ];
      
      for (const p of paths) {
        if (fs.existsSync(p)) {
          fpcalcPath = p;
          break;
        }
      }
    } else {
      // Linux paths
      const paths = [
        '/usr/bin/fpcalc',
        '/usr/local/bin/fpcalc'
      ];
      
      for (const p of paths) {
        if (fs.existsSync(p)) {
          fpcalcPath = p;
          break;
        }
      }
    }
    
    if (fpcalcPath) {
      console.log(`fpcalc found at: ${fpcalcPath}`);
      return true;
    } else {
      console.warn('fpcalc (Chromaprint) not found. Audio fingerprinting will not work.');
      console.warn('Please install Chromaprint:');
      
      if (process.platform === 'win32') {
        console.warn('  - Windows: Download from https://acoustid.org/chromaprint');
      } else if (process.platform === 'darwin') {
        console.warn('  - macOS: brew install chromaprint');
      } else {
        console.warn('  - Linux: sudo apt install libchromaprint-tools');
      }
      
      return false;
    }
  }
}

// Ask for AcoustID API key
function promptForApiKey() {
  return new Promise((resolve) => {
    rl.question('Enter your AcoustID API key (or press Enter to skip): ', (answer) => {
      if (answer.trim()) {
        // Save API key to environment file
        const envFile = path.join(PYTHON_DIR, '.env');
        fs.writeFileSync(envFile, `ACOUSTID_API_KEY=${answer.trim()}\n`);
        console.log('API key saved.');
      } else {
        console.warn('No API key provided. You can add it later in the app settings.');
      }
      resolve();
    });
  });
}

// Main setup function
async function setup() {
  console.log('Checking requirements...');
  
  // Check Python
  if (!checkPython()) {
    console.error('Setup failed: Python is required.');
    process.exit(1);
  }
  
  // Check/create virtual environment
  if (!checkVenv()) {
    console.log('Virtual environment not found.');
    if (!createVenv()) {
      console.error('Setup failed: Could not create virtual environment.');
      process.exit(1);
    }
  } else {
    console.log('Virtual environment already exists.');
  }
  
  // Install dependencies
  if (!installDependencies()) {
    console.error('Setup failed: Could not install dependencies.');
    process.exit(1);
  }
  
  // Check fpcalc
  checkFpcalc();
  
  // Ask for API key
  await promptForApiKey();
  
  console.log('\nSetup completed successfully!');
  console.log('You can now start the app with: npm start');
  
  rl.close();
}

// Run setup
setup();