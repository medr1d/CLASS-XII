"""
Matplotlib configuration for Pyodide environment
This module sets up matplotlib to work in the browser
"""

import matplotlib
import matplotlib.pyplot as plt
import io
import base64
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
matplotlib.use('Agg')

def show_plot():
    """Custom show function that outputs plots as base64 images"""
    try:
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=96)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        buf.close()
        print(f'<img src="data:image/png;base64,{img_str}" style="max-width:100%;height:auto;"/>')
        plt.close()
    except Exception as err:
        print(f'Plot error: {err}')
        plt.close()

# Replace the default show function
plt.show = show_plot
