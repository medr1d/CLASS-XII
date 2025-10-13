// Virtual File System Module
// Handles file operations for Pyodide

async function setupVirtualFileSystem(pyodide, updateProgress) {
    const defaultFiles = {
        'text.txt': `Hello from Python Environment!
This is your personal text file.
You can read and modify this file in your Python code.
Example: open('text.txt', 'r').read()`,
        
        'tester.csv': `name,age,city,score
Alice,25,NYC,85
Bob,30,LA,92
Carol,28,Chicago,78
David,35,Houston,95`,
        
        'binary.dat': 'Sample binary data for Python processing'
    };
    
    try {
        // Try to fetch user files from server
        let filesData = {};
        try {
            const response = await fetch('/python/get-files/');
            if (response.ok) {
                filesData = await response.json();
            }
        } catch (fetchError) {
            console.log('Using default files');
        }
        
        // Write files to Pyodide filesystem
        for (const [filename, defaultContent] of Object.entries(defaultFiles)) {
            const content = filename === 'text.txt' ? (filesData.text_content || defaultContent) :
                           filename === 'tester.csv' ? (filesData.csv_content || defaultContent) :
                           (filesData.binary_content || defaultContent);
            
            try {
                pyodide.FS.writeFile(filename, content);
            } catch (fsError) {
                console.warn(`Failed to write ${filename}:`, fsError);
            }
        }
        
        // Set global variables for file viewers
        if (typeof window !== 'undefined') {
            window.binaryContent = filesData.binary_content || defaultFiles['binary.dat'];
            window.binaryHexData = filesData.binary_hex || 'Binary data (hex view not available)';
            
            // Update file viewers if function exists
            if (typeof window.updateFileViewers === 'function') {
                window.updateFileViewers();
            }
        }
        
        return true;
        
    } catch (error) {
        console.error("File system setup failed:", error);
        
        // Fallback: write default files
        for (const [filename, content] of Object.entries(defaultFiles)) {
            try {
                pyodide.FS.writeFile(filename, content);
            } catch (fsError) {
                console.warn(`Fallback write failed for ${filename}`);
            }
        }
        
        return false;
    }
}

function getFileList(pyodide) {
    try {
        const files = pyodide.FS.readdir('/');
        return files.filter(f => f !== '.' && f !== '..' && !f.startsWith('.'));
    } catch (error) {
        console.error("Failed to read file list:", error);
        return [];
    }
}

function readFile(pyodide, filename) {
    try {
        const content = pyodide.FS.readFile(filename, { encoding: 'utf8' });
        return content;
    } catch (error) {
        console.error(`Failed to read ${filename}:`, error);
        return null;
    }
}

function writeFile(pyodide, filename, content) {
    try {
        pyodide.FS.writeFile(filename, content);
        return true;
    } catch (error) {
        console.error(`Failed to write ${filename}:`, error);
        return false;
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        setupVirtualFileSystem, 
        getFileList, 
        readFile, 
        writeFile 
    };
}
