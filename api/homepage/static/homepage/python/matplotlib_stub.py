"""
Matplotlib stub for when matplotlib fails to load
Provides a fallback that won't crash the environment
"""

import sys

class MatplotlibStub:
    """Stub class that mimics matplotlib behavior"""
    
    def __getattr__(self, name):
        """Return a callable for any attribute access"""
        return lambda *args, **kwargs: self
    
    def __call__(self, *args, **kwargs):
        """Make the stub itself callable"""
        return self

# Install the stub in place of matplotlib
sys.modules['matplotlib'] = MatplotlibStub()
sys.modules['matplotlib.pyplot'] = MatplotlibStub()
