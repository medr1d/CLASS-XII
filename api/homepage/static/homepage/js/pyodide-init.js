// Pyodide Initialization Module
// Loads Python modules from separate .py files

let pyodide = null;
let isInitialized = false;

// Helper function to load Python module from file
async function loadPythonModule(filename) {
    const response = await fetch(`/static/homepage/python/${filename}`);
    if (!response.ok) {
        throw new Error(`Failed to load ${filename}: ${response.statusText}`);
    }
    return await response.text();
}

async function initializePyodide(updateProgress, updateTerminal) {
    if (isInitialized) return pyodide;
    
    try {
        // Step 1: Load Pyodide
        updateProgress("Loading Pyodide...");
        pyodide = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/"
        });
        
        // Step 2: Load core packages
        updateProgress("Loading packages...");
        await pyodide.loadPackage(["numpy", "matplotlib", "pandas", "micropip"]);
        
        // Step 3: Setup matplotlib
        updateProgress("Configuring matplotlib...");
        try {
            const matplotlibSetup = await loadPythonModule('matplotlib_setup.py');
            await pyodide.runPythonAsync(matplotlibSetup);
            updateTerminal("Matplotlib configured\n");
        } catch (matplotError) {
            console.warn("Matplotlib failed, using stub:", matplotError);
            const matplotlibStub = await loadPythonModule('matplotlib_stub.py');
            await pyodide.runPythonAsync(matplotlibStub);
            updateTerminal("Matplotlib stub loaded\n");
        }
        
        // Step 4: Setup I/O
        updateProgress("Configuring input/output...");
        const ioSetup = await loadPythonModule('io_setup.py');
        await pyodide.runPythonAsync(ioSetup);
        updateTerminal("I/O configured\n");
        
        // Step 5: Setup package installer
        updateProgress("Setting up package installer...");
        try {
            const packageInstaller = await loadPythonModule('package_installer.py');
            await pyodide.runPythonAsync(packageInstaller);
            updateTerminal("Package installer ready\n");
        } catch (installerError) {
            console.warn("Package installer failed:", installerError);
        }
        
        isInitialized = true;
        updateTerminal("\n=== Python Environment Ready ===\n");
        updateTerminal("Packages: numpy, pandas, matplotlib\n");
        updateTerminal("Use plt.show() to display plots\n");
        updateTerminal("Use await install_package('name') for more\n\n");
        
        return pyodide;
        
    } catch (error) {
        console.error("Pyodide initialization failed:", error);
        updateTerminal("\nERROR: " + error.message + "\n");
        updateTerminal("Please refresh the page to try again\n");
        throw error;
    }
}

function getPyodide() {
    return pyodide;
}

function isPyodideReady() {
    return isInitialized;
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initializePyodide, getPyodide, isPyodideReady };
}
