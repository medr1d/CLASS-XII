#!/usr/bin/env python
"""
Django server startup script for PyInstaller executable
"""
import os
import sys
import django
from django.core.management import execute_from_command_line
import webbrowser
import time
import threading

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:8000')

if __name__ == '__main__':
    # Set up Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mywebsite.settings')
    
    # Get the directory where the executable is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        application_path = sys._MEIPASS
    else:
        # Running as script
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the application directory
    os.chdir(application_path)
    
    # Setup Django
    django.setup()
    
    print("=" * 60)
    print("DJANGO SERVER STARTING")
    print("=" * 60)
    print(f"Application path: {application_path}")
    print(f"Database: {os.path.join(application_path, 'db.sqlite3')}")
    print("\nServer will be available at: http://127.0.0.1:8000")
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    
    # Open browser in background thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run migrations
    try:
        print("\nApplying database migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
    except Exception as e:
        print(f"Warning: Migration error: {e}")
    
    # Start the server
    sys.argv = ['manage.py', 'runserver', '127.0.0.1:8000', '--noreload']
    execute_from_command_line(sys.argv)
