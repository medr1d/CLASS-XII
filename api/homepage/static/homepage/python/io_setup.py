"""
Custom input/output configuration for Pyodide
Replaces built-in input() and open() with web-safe versions
"""

import builtins
import asyncio
import os

# Store original functions
original_open = builtins.open
original_input = builtins.input

async def async_web_input(prompt=""):
    """Async input function that works with the web interface"""
    import js
    from pyodide.ffi import create_proxy
    
    def create_promise():
        return js.Promise.new(create_proxy(
            lambda resolve, reject: js.showInputDialogAsync(prompt, resolve)
        ))
    
    result = await create_promise()
    return result if result else ""

def sync_web_input(prompt=""):
    """Synchronous wrapper for web input"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import js
            return js.showInputDialog(prompt) or ""
        return loop.run_until_complete(async_web_input(prompt))
    except Exception:
        import js
        return js.showInputDialog(prompt) or ""

def safe_open(filename, mode='r', *args, **kwargs):
    """Restricted open() that only allows specific files"""
    allowed_files = ['text.txt', 'tester.csv', 'binary.dat']
    allowed_paths = ['/lib/python3.11/', '/lib/python311.zip/', '/usr/', '<']
    
    basename = os.path.basename(filename)
    if basename in allowed_files:
        return original_open(filename, mode, *args, **kwargs)
    
    for path in allowed_paths:
        if filename.startswith(path) or path in filename:
            return original_open(filename, mode, *args, **kwargs)
    
    raise PermissionError(f'Cannot open: {filename}')

# Replace built-in functions
builtins.input = sync_web_input
builtins.open = safe_open
