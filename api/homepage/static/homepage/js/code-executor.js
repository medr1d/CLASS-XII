// Code Execution Module
// Handles running Python code in Pyodide

async function executeUserCode(code, pyodide, updateTerminal) {
    if (!code || !code.trim()) {
        updateTerminal("No code to execute\n");
        return;
    }
    
    updateTerminal("\n>>> Executing code...\n");
    
    try {
        // Setup output capture
        await pyodide.runPythonAsync(`
import sys
from io import StringIO
sys.stdout = StringIO()
sys.stderr = StringIO()
`);
        
        // Show input() notification
        if (code.includes('input(')) {
            updateTerminal("Code contains input() - dialogs will appear\n");
        }
        
        // Execute the code
        try {
            await pyodide.runPythonAsync(code);
        } catch (execError) {
            if (execError.name === 'PythonError') {
                updateTerminal("Error: " + execError.message + "\n", true);
            } else {
                updateTerminal("Error: " + execError.toString() + "\n", true);
            }
        }
        
        // Get output
        const stdout = await pyodide.runPythonAsync("sys.stdout.getvalue()");
        const stderr = await pyodide.runPythonAsync("sys.stderr.getvalue()");
        
        // Restore streams
        await pyodide.runPythonAsync(`
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
`);
        
        // Display results
        if (stdout) {
            updateTerminal(stdout);
        }
        if (stderr) {
            updateTerminal(stderr, true);
        }
        
        if (!stdout && !stderr) {
            updateTerminal("Code executed successfully (no output)\n");
        }
        
    } catch (error) {
        updateTerminal("Execution error: " + error.toString() + "\n", true);
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { executeUserCode };
}
