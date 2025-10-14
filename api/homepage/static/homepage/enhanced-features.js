// New features JavaScript for Python Environment
// Add this to python_environment.html

// Mobile toolbar setup
if (/Android|iPhone|iPad/i.test(navigator.userAgent)) {
    document.addEventListener('DOMContentLoaded', function() {
        document.getElementById('mobile-toolbar').style.display = 'flex';
    });
}

function insertText(text) {
    if (aceEditor) {
        aceEditor.session.insert(aceEditor.getCursorPosition(), text);
        aceEditor.focus();
    }
}

// History Modal Functions
function toggleHistory() {
    const modal = document.getElementById('history-modal');
    if (modal.style.display === 'none' || !modal.style.display) {
        loadExecutionHistory();
        modal.style.display = 'flex';
    } else {
        modal.style.display = 'none';
    }
}

function closeHistoryModal() {
    document.getElementById('history-modal').style.display = 'none';
}

async function loadExecutionHistory() {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = '<div style="text-align: center; padding: 40px; color: #888;">Loading...</div>';
    
    try {
        const response = await fetch('/python/get-history/?limit=20');
        const data = await response.json();
        
        if (data.status === 'success' && data.history.length > 0) {
            historyList.innerHTML = data.history.map(h => `
                <div class="history-item">
                    <div class="history-header">
                        <strong>${h.filename}</strong>
                        <span class="history-time">${new Date(h.executed_at).toLocaleString()}</span>
                    </div>
                    <div class="history-code">${escapeHtml(h.code_snippet)}</div>
                    ${h.output ? `<div class="history-output">${escapeHtml(h.output)}</div>` : ''}
                    ${h.error ? `<div class="history-output" style="color: #ff6b6b;">${escapeHtml(h.error)}</div>` : ''}
                    <div style="font-size: 0.85em; color: #888; margin-top: 5px;">
                        ⏱️ ${h.execution_time.toFixed(2)}ms
                        ${h.was_successful ? '✓ Success' : '✗ Error'}
                    </div>
                    <div class="history-actions">
                        <button onclick='loadCodeFromHistory(${JSON.stringify(h.full_code)})'>Load Code</button>
                        <button onclick='copyCode(${JSON.stringify(h.full_code)})'>Copy</button>
                    </div>
                </div>
            `).join('');
        } else {
            historyList.innerHTML = '<div style="text-align: center; padding: 40px; color: #888;">No execution history yet. Run some code to see it here!</div>';
        }
    } catch (error) {
        historyList.innerHTML = '<div style="text-align: center; padding: 40px; color: #ff6b6b;">Error loading history</div>';
        console.error('Error loading history:', error);
    }
}

function loadCodeFromHistory(code) {
    if (aceEditor) {
        aceEditor.setValue(code, -1);
        closeHistoryModal();
        updateStatus('Code loaded from history', 'success');
    }
}

function copyCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        updateStatus('Code copied to clipboard!', 'success');
    });
}

// Share Modal Functions
function shareCode() {
    document.getElementById('share-modal').style.display = 'flex';
    document.getElementById('share-result').style.display = 'none';
}

function closeShareModal() {
    document.getElementById('share-modal').style.display = 'none';
}

async function createShareLink() {
    const title = document.getElementById('share-title').value.trim() || 'Untitled';
    const description = document.getElementById('share-description').value.trim();
    const expires = document.getElementById('share-expires').value;
    const isPublic = document.getElementById('share-public').checked;
    const code = aceEditor ? aceEditor.getValue() : '';
    
    if (!code) {
        alert('Cannot share empty code!');
        return;
    }
    
    try {
        const response = await fetch('/python/share/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                title: title,
                code: code,
                description: description,
                is_public: isPublic,
                expires_days: expires || null
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('share-url').value = data.share_url;
            document.getElementById('share-result').style.display = 'block';
        } else {
            alert('Error creating share link: ' + data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function copyShareLink() {
    const url = document.getElementById('share-url').value;
    navigator.clipboard.writeText(url).then(() => {
        updateStatus('Share link copied!', 'success');
    });
}

// Settings Modal Functions
function toggleSettings() {
    const modal = document.getElementById('settings-modal');
    if (modal.style.display === 'none' || !modal.style.display) {
        loadUserSettings();
        modal.style.display = 'flex';
    } else {
        modal.style.display = 'none';
    }
}

function closeSettingsModal() {
    document.getElementById('settings-modal').style.display = 'none';
}

async function loadUserSettings() {
    try {
        const response = await fetch('/python/get-settings/');
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('settings-dark-plots').checked = data.settings.dark_mode_plots;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettings() {
    const darkPlots = document.getElementById('settings-dark-plots').checked;
    const fontSize = document.getElementById('settings-font-size').value;
    
    // Save plot theme
    try {
        await fetch('/python/update-plot-theme/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                dark_mode_plots: darkPlots
            })
        });
        
        // Update editor font size
        if (aceEditor) {
            aceEditor.setOptions({
                fontSize: fontSize + 'px'
            });
        }
        
        // Update plot theme in Pyodide
        if (pyodide && isInitialized) {
            await pyodide.runPythonAsync(`
import builtins
builtins.set_plot_theme('${darkPlots ? 'dark' : 'light'}')
            `);
        }
        
        updateStatus('Settings saved!', 'success');
        closeSettingsModal();
    } catch (error) {
        alert('Error saving settings: ' + error.message);
    }
}

// Font size slider
document.addEventListener('DOMContentLoaded', function() {
    const fontSizeSlider = document.getElementById('settings-font-size');
    const fontSizeDisplay = document.getElementById('font-size-display');
    
    if (fontSizeSlider && fontSizeDisplay) {
        fontSizeSlider.addEventListener('input', function() {
            fontSizeDisplay.textContent = this.value;
        });
    }
});

// Enhanced autocomplete for Ace editor
function setupEnhancedAutocomplete() {
    if (!aceEditor) return;
    
    const pythonCompletions = {
        'numpy': ['array', 'zeros', 'ones', 'arange', 'linspace', 'random', 'mean', 'std', 'sum', 'max', 'min'],
        'np': ['array', 'zeros', 'ones', 'arange', 'linspace', 'random', 'mean', 'std', 'sum', 'max', 'min'],
        'pandas': ['DataFrame', 'Series', 'read_csv', 'read_excel', 'read_json', 'concat', 'merge'],
        'pd': ['DataFrame', 'Series', 'read_csv', 'read_excel', 'read_json', 'concat', 'merge'],
        'matplotlib.pyplot': ['plot', 'scatter', 'bar', 'hist', 'show', 'xlabel', 'ylabel', 'title', 'legend', 'grid', 'figure', 'subplot'],
        'plt': ['plot', 'scatter', 'bar', 'hist', 'show', 'xlabel', 'ylabel', 'title', 'legend', 'grid', 'figure', 'subplot'],
        'builtins': ['print', 'input', 'len', 'range', 'sum', 'min', 'max', 'sorted', 'enumerate', 'zip', 'map', 'filter', 'list', 'dict', 'set', 'tuple']
    };
    
    const pythonKeywords = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 
                           'import', 'from', 'as', 'return', 'break', 'continue', 'pass', 'yield', 'with', 
                           'lambda', 'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None'];
    
    aceEditor.completers = [{
        getCompletions: function(editor, session, pos, prefix, callback) {
            const completions = [];
            const line = session.getLine(pos.row).substring(0, pos.column);
            
            // Check for method completion (after dot)
            const match = line.match(/(\w+)\.(\w*)$/);
            if (match) {
                const module = match[1];
                if (pythonCompletions[module]) {
                    pythonCompletions[module].forEach(method => {
                        completions.push({
                            caption: method,
                            value: method,
                            meta: module,
                            score: 1000
                        });
                    });
                }
            } else {
                // Keyword completion
                pythonKeywords.forEach(keyword => {
                    if (keyword.toLowerCase().startsWith(prefix.toLowerCase())) {
                        completions.push({
                            caption: keyword,
                            value: keyword,
                            meta: 'keyword',
                            score: 900
                        });
                    }
                });
                
                // Built-in functions
                pythonCompletions.builtins.forEach(func => {
                    if (func.toLowerCase().startsWith(prefix.toLowerCase())) {
                        completions.push({
                            caption: func,
                            value: func + '()',
                            meta: 'builtin',
                            score: 800
                        });
                    }
                });
            }
            
            callback(null, completions);
        }
    }];
    
    // Enable autocomplete features
    aceEditor.setOptions({
        enableBasicAutocompletion: true,
        enableLiveAutocompletion: true,
        enableSnippets: true
    });
}

// Save execution to history
async function saveExecutionToHistory(code, output, error, executionTime, wasSuccessful) {
    try {
        await fetch('/python/save-execution/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                code: code,
                output: output,
                error: error,
                execution_time: executionTime,
                filename: currentScript || 'untitled.py',
                was_successful: wasSuccessful
            })
        });
    } catch (error) {
        console.error('Error saving execution history:', error);
    }
}

// Helper functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

console.log('✓ Enhanced features loaded: History, Sharing, Settings, Autocomplete, Mobile Toolbar');
