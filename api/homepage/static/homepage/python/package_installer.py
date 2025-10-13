"""
Package installer for Pyodide environment
Provides easy package installation via micropip
"""

import micropip

async def install_package(package_name):
    """
    Install a Python package via micropip
    
    Args:
        package_name: Name of the package to install
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f'Installing {package_name}...')
        await micropip.install(package_name)
        print(f'✓ {package_name} installed')
        return True
    except Exception as err:
        print(f'✗ {package_name} failed: {err}')
        return False
