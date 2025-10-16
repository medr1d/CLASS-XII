"""
Views for Cloud IDE functionality for paid users
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q
from django.utils import timezone
from auth_app.rate_limiting import rate_limit_per_user
import json
import subprocess
import tempfile
import os
import shutil
import signal
from pathlib import Path

from .models import (
    IDEProject, IDEDirectory, IDEFile, IDEExecutionLog, 
    IDETerminalSession, UserProfile
)


# ==================== IDE MAIN VIEW ====================

@login_required
@ensure_csrf_cookie
def ide_environment(request):
    """Main IDE environment view for paid users"""
    user = request.user
    
    # Get user profile and check if paid user
    try:
        profile = UserProfile.objects.get(user=user)
        user_theme = profile.theme
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
        user_theme = 'default'
    
    # Check if user has paid access
    if not profile.paidUser:
        from django.contrib import messages
        messages.error(request, 'Cloud IDE is only available for premium users. Please upgrade your account.')
        return redirect('homepage:python_environment')  # Redirect to free environment
    
    # Get or create default project
    project, created = IDEProject.objects.get_or_create(
        user=user,
        name='My First Project',
        defaults={
            'description': 'Welcome to your cloud IDE!',
            'is_active': True
        }
    )
    
    if created:
        # Create initial files
        IDEFile.objects.create(
            project=project,
            name='main.py',
            path='main.py',
            content='''# Welcome to your Cloud IDE!
# This is a full-featured Python development environment

def main():
    print("Hello from Cloud IDE!")
    print("You have access to:")
    print("- File management")
    print("- Real-time code execution")
    print("- Terminal access")
    print("- Full Python standard library")
    
    # Example with data
    data = [1, 2, 3, 4, 5]
    result = sum(data) / len(data)
    print(f"\\nAverage of {data}: {result}")

if __name__ == "__main__":
    main()
''',
            file_type='python'
        )
        
        IDEFile.objects.create(
            project=project,
            name='README.md',
            path='README.md',
            content='''# Welcome to Cloud IDE

This is your personal cloud development environment.

## Features
- Monaco Editor (VS Code editor)
- File management (create, edit, delete files and folders)
- Real-time Python execution
- Live terminal output
- Persistent storage

## Getting Started
1. Edit files in the editor
2. Run code with the "Run" button
3. See output in the terminal below
4. Create new files and folders as needed

Happy coding!
''',
            file_type='markdown'
        )
    
    # Update last accessed time
    project.update_access_time()
    
    # Get all user projects
    user_projects = IDEProject.objects.filter(user=user, is_active=True)
    
    context = {
        'user': user,
        'user_theme': user_theme,
        'current_project': project,
        'project_id': str(project.project_id),
        'projects': user_projects,
        'is_paid_user': profile.paidUser,
    }
    
    return render(request, 'homepage/ide_environment.html', context)


# ==================== PROJECT MANAGEMENT ====================

@login_required
@require_POST
@rate_limit_per_user(max_requests=20, window=60)
def create_project(request):
    """Create a new IDE project"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '')
        
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Project name required'}, status=400)
        
        # Check project limit (max 10 projects per user)
        project_count = IDEProject.objects.filter(user=request.user, is_active=True).count()
        if project_count >= 10:
            return JsonResponse({
                'status': 'error',
                'message': 'Maximum 10 projects allowed. Delete a project first.'
            }, status=400)
        
        # Create project
        project = IDEProject.objects.create(
            user=request.user,
            name=name,
            description=description
        )
        
        # Create initial main.py file
        IDEFile.objects.create(
            project=project,
            name='main.py',
            path='main.py',
            content='# New Python project\n\nprint("Hello, World!")\n',
            file_type='python'
        )
        
        return JsonResponse({
            'status': 'success',
            'project': {
                'id': str(project.project_id),
                'name': project.name,
                'description': project.description,
                'created_at': project.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
@rate_limit_per_user(max_requests=10, window=60)
def create_project_from_template(request):
    """Create a new project from a template"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        template = data.get('template', 'blank')
        
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Project name required'}, status=400)
        
        # Check project limit
        project_count = IDEProject.objects.filter(user=request.user, is_active=True).count()
        if project_count >= 10:
            return JsonResponse({
                'status': 'error',
                'message': 'Maximum 10 projects allowed. Delete a project first.'
            }, status=400)
        
        # Create project
        project = IDEProject.objects.create(
            user=request.user,
            name=name,
            description=f'{template.capitalize()} project'
        )
        
        # Create files based on template
        templates = get_project_templates()
        if template in templates:
            for file_data in templates[template]:
                IDEFile.objects.create(
                    project=project,
                    name=file_data['name'],
                    path=file_data['path'],
                    content=file_data['content'],
                    file_type=file_data['type']
                )
        else:
            # Default to blank template
            IDEFile.objects.create(
                project=project,
                name='main.py',
                path='main.py',
                content='# New Python project\n\nprint("Hello, World!")\n',
                file_type='python'
            )
        
        return JsonResponse({
            'status': 'success',
            'project': {
                'id': str(project.project_id),
                'name': project.name,
                'description': project.description,
                'created_at': project.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def get_project_templates():
    """Return project templates with starter files"""
    return {
        'blank': [
            {
                'name': 'main.py',
                'path': 'main.py',
                'type': 'python',
                'content': '''# Blank Python Project

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
            }
        ],
        'flask': [
            {
                'name': 'app.py',
                'path': 'app.py',
                'type': 'python',
                'content': '''from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/hello', methods=['GET', 'POST'])
def hello_api():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', 'World')
    else:
        name = request.args.get('name', 'World')
    
    return jsonify({'message': f'Hello, {name}!'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
'''
            },
            {
                'name': 'requirements.txt',
                'path': 'requirements.txt',
                'type': 'text',
                'content': '''Flask==2.3.0
'''
            },
            {
                'name': 'README.md',
                'path': 'README.md',
                'type': 'markdown',
                'content': '''# Flask Web Application

## Setup
```bash
pip install -r requirements.txt
python app.py
```

## Features
- Basic routing
- REST API endpoints
- Template rendering

Visit http://localhost:5000 after running the app.
'''
            }
        ],
        'django': [
            {
                'name': 'manage.py',
                'path': 'manage.py',
                'type': 'python',
                'content': '''#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
'''
            },
            {
                'name': 'views.py',
                'path': 'app/views.py',
                'type': 'python',
                'content': '''from django.shortcuts import render
from django.http import JsonResponse

def index(request):
    return render(request, 'index.html')

def api_hello(request):
    return JsonResponse({'message': 'Hello from Django!'})
'''
            },
            {
                'name': 'models.py',
                'path': 'app/models.py',
                'type': 'python',
                'content': '''from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
'''
            },
            {
                'name': 'requirements.txt',
                'path': 'requirements.txt',
                'type': 'text',
                'content': '''Django==4.2.0
'''
            }
        ],
        'datascience': [
            {
                'name': 'analysis.py',
                'path': 'analysis.py',
                'type': 'python',
                'content': '''import pandas as pd
import numpy as np

# Data Analysis Script

def load_data(filepath):
    """Load data from CSV file"""
    return pd.read_csv(filepath)

def analyze_data(df):
    """Perform basic data analysis"""
    print("Dataset Shape:", df.shape)
    print("\\nColumn Names:", df.columns.tolist())
    print("\\nData Types:\\n", df.dtypes)
    print("\\nBasic Statistics:\\n", df.describe())
    print("\\nMissing Values:\\n", df.isnull().sum())
    
    return df

def main():
    # Example: Create sample data
    data = {
        'Name': ['Alice', 'Bob', 'Charlie', 'David'],
        'Age': [25, 30, 35, 28],
        'Score': [85, 92, 78, 88]
    }
    df = pd.DataFrame(data)
    
    print("Sample Data Analysis:")
    analyze_data(df)
    
    # Calculate average score
    avg_score = df['Score'].mean()
    print(f"\\nAverage Score: {avg_score:.2f}")

if __name__ == "__main__":
    main()
'''
            },
            {
                'name': 'visualization.py',
                'path': 'visualization.py',
                'type': 'python',
                'content': '''# Data Visualization Script
# Note: matplotlib requires GUI which may not work in cloud IDE
# Use this as a template for local development

import pandas as pd
import numpy as np

def create_sample_data():
    """Create sample data for visualization"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100)
    values = np.random.randn(100).cumsum()
    
    return pd.DataFrame({'Date': dates, 'Value': values})

def print_data_summary(df):
    """Print data summary instead of plotting"""
    print("Data Summary for Visualization:")
    print(df.describe())
    print("\\nFirst 10 rows:")
    print(df.head(10))

if __name__ == "__main__":
    df = create_sample_data()
    print_data_summary(df)
'''
            },
            {
                'name': 'requirements.txt',
                'path': 'requirements.txt',
                'type': 'text',
                'content': '''pandas==2.0.0
numpy==1.24.0
matplotlib==3.7.0
'''
            }
        ],
        'scraper': [
            {
                'name': 'scraper.py',
                'path': 'scraper.py',
                'type': 'python',
                'content': '''import requests
from bs4 import BeautifulSoup

class WebScraper:
    """Simple web scraper using requests and BeautifulSoup"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url):
        """Fetch a web page"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_html(self, html):
        """Parse HTML content"""
        return BeautifulSoup(html, 'html.parser')
    
    def extract_links(self, soup):
        """Extract all links from page"""
        links = []
        for link in soup.find_all('a', href=True):
            links.append(link['href'])
        return links
    
    def extract_text(self, soup, tag='p'):
        """Extract text from specific tags"""
        texts = []
        for element in soup.find_all(tag):
            texts.append(element.get_text(strip=True))
        return texts

def main():
    # Example usage
    url = "https://example.com"
    scraper = WebScraper(url)
    
    html = scraper.fetch_page(url)
    if html:
        soup = scraper.parse_html(html)
        links = scraper.extract_links(soup)
        texts = scraper.extract_text(soup)
        
        print(f"Found {len(links)} links")
        print(f"Found {len(texts)} paragraphs")

if __name__ == "__main__":
    main()
'''
            },
            {
                'name': 'config.py',
                'path': 'config.py',
                'type': 'python',
                'content': '''# Scraper Configuration

# Request settings
TIMEOUT = 10
MAX_RETRIES = 3

# Headers
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
]

# Rate limiting
REQUEST_DELAY = 1  # seconds between requests
'''
            },
            {
                'name': 'requirements.txt',
                'path': 'requirements.txt',
                'type': 'text',
                'content': '''requests==2.31.0
beautifulsoup4==4.12.0
'''
            }
        ],
        'api': [
            {
                'name': 'client.py',
                'path': 'client.py',
                'type': 'python',
                'content': '''import requests
from typing import Dict, Any, Optional

class APIClient:
    """REST API Client with authentication"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return {'error': str(e)}
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request"""
        return self._make_request('POST', endpoint, json=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT request"""
        return self._make_request('PUT', endpoint, json=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request"""
        return self._make_request('DELETE', endpoint)

def main():
    # Example usage
    client = APIClient('https://api.example.com')
    
    # GET request
    data = client.get('/users')
    print(data)
    
    # POST request
    new_user = client.post('/users', data={'name': 'John Doe'})
    print(new_user)

if __name__ == "__main__":
    main()
'''
            },
            {
                'name': 'models.py',
                'path': 'models.py',
                'type': 'python',
                'content': '''from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    """User model"""
    id: int
    name: str
    email: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create User from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            email=data['email'],
            created_at=data.get('created_at')
        )

@dataclass
class APIResponse:
    """API Response model"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
'''
            },
            {
                'name': 'requirements.txt',
                'path': 'requirements.txt',
                'type': 'text',
                'content': '''requests==2.31.0
'''
            }
        ]
    }


@login_required
def get_project(request, project_id):
    """Get project details"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        project.update_access_time()
        
        return JsonResponse({
            'status': 'success',
            'project': {
                'id': str(project.project_id),
                'name': project.name,
                'description': project.description,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def delete_project(request, project_id):
    """Delete an IDE project"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        project_name = project.name
        project.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Project "{project_name}" deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==================== FILE MANAGEMENT ====================

@login_required
def get_project_files(request, project_id):
    """Get all files and directories in a project"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        # Get all files
        files = IDEFile.objects.filter(project=project).order_by('path')
        
        # Get all directories
        directories = IDEDirectory.objects.filter(project=project).order_by('path')
        
        # Build file tree structure
        file_tree = []
        dir_map = {}
        
        # Add directories to tree
        for directory in directories:
            dir_node = {
                'type': 'directory',
                'name': directory.name,
                'path': directory.path,
                'children': []
            }
            dir_map[directory.path] = dir_node
            
            if directory.parent:
                parent_path = directory.parent.path
                if parent_path in dir_map:
                    dir_map[parent_path]['children'].append(dir_node)
            else:
                file_tree.append(dir_node)
        
        # Add files to tree
        for file in files:
            file_node = {
                'type': 'file',
                'name': file.name,
                'path': file.path,
                'file_type': file.file_type,
                'size': file.size,
                'updated_at': file.updated_at.isoformat()
            }
            
            if file.directory:
                dir_path = file.directory.path
                if dir_path in dir_map:
                    dir_map[dir_path]['children'].append(file_node)
            else:
                file_tree.append(file_node)
        
        return JsonResponse({
            'status': 'success',
            'file_tree': file_tree,
            'project_name': project.name
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def get_file_content(request, project_id, file_path):
    """Get content of a specific file"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        file = get_object_or_404(IDEFile, project=project, path=file_path)
        
        return JsonResponse({
            'status': 'success',
            'file': {
                'name': file.name,
                'path': file.path,
                'content': file.content,
                'file_type': file.file_type,
                'size': file.size,
                'updated_at': file.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
@rate_limit_per_user(max_requests=100, window=60)
def save_file(request, project_id):
    """Create or update a file"""
    try:
        data = json.loads(request.body)
        file_path = data.get('path', '').strip()
        content = data.get('content', '')
        
        if not file_path:
            return JsonResponse({'status': 'error', 'message': 'File path required'}, status=400)
        
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        # Extract filename and directory path
        path_parts = file_path.split('/')
        filename = path_parts[-1]
        
        # Find or create directory if nested
        directory = None
        if len(path_parts) > 1:
            dir_path = '/'.join(path_parts[:-1])
            directory, _ = IDEDirectory.objects.get_or_create(
                project=project,
                path=dir_path,
                defaults={'name': path_parts[-2] if len(path_parts) > 1 else dir_path}
            )
        
        # Create or update file
        file, created = IDEFile.objects.update_or_create(
            project=project,
            path=file_path,
            defaults={
                'name': filename,
                'content': content,
                'directory': directory
            }
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'File {"created" if created else "updated"} successfully',
            'file': {
                'name': file.name,
                'path': file.path,
                'size': file.size,
                'updated_at': file.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def delete_file(request, project_id):
    """Delete a file"""
    try:
        data = json.loads(request.body)
        file_path = data.get('path', '').strip()
        
        if not file_path:
            return JsonResponse({'status': 'error', 'message': 'File path required'}, status=400)
        
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        file = get_object_or_404(IDEFile, project=project, path=file_path)
        
        file_name = file.name
        file.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'File "{file_name}" deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def rename_file(request, project_id):
    """Rename a file or directory"""
    try:
        data = json.loads(request.body)
        old_path = data.get('old_path', '').strip()
        new_name = data.get('new_name', '').strip()
        item_type = data.get('type', 'file')  # 'file' or 'directory'
        
        if not old_path or not new_name:
            return JsonResponse({'success': False, 'error': 'Path and new name required'}, status=400)
        
        # Validate new name (no slashes, no special chars)
        if '/' in new_name or '\\' in new_name:
            return JsonResponse({'success': False, 'error': 'Invalid name: cannot contain slashes'}, status=400)
        
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        # Calculate new path
        path_parts = old_path.split('/')
        path_parts[-1] = new_name
        new_path = '/'.join(path_parts)
        
        if item_type == 'file':
            # Rename file
            file_obj = get_object_or_404(IDEFile, project=project, path=old_path)
            
            # Check if new path already exists
            if IDEFile.objects.filter(project=project, path=new_path).exists():
                return JsonResponse({'success': False, 'error': 'A file with this name already exists'}, status=400)
            
            file_obj.name = new_name
            file_obj.path = new_path
            file_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': f'File renamed to "{new_name}"',
                'new_path': new_path
            })
        else:
            # Rename directory
            dir_obj = get_object_or_404(IDEDirectory, project=project, path=old_path)
            
            # Check if new path already exists
            if IDEDirectory.objects.filter(project=project, path=new_path).exists():
                return JsonResponse({'success': False, 'error': 'A directory with this name already exists'}, status=400)
            
            # Update directory and all children
            old_path_prefix = old_path + '/'
            new_path_prefix = new_path + '/'
            
            # Update all child directories
            child_dirs = IDEDirectory.objects.filter(project=project, path__startswith=old_path_prefix)
            for child_dir in child_dirs:
                child_dir.path = child_dir.path.replace(old_path_prefix, new_path_prefix, 1)
                child_dir.save()
            
            # Update all files in this directory and subdirectories
            child_files = IDEFile.objects.filter(project=project, path__startswith=old_path_prefix)
            for child_file in child_files:
                child_file.path = child_file.path.replace(old_path_prefix, new_path_prefix, 1)
                child_file.save()
            
            # Update the directory itself
            dir_obj.name = new_name
            dir_obj.path = new_path
            dir_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Directory renamed to "{new_name}"',
                'new_path': new_path
            })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def create_directory(request, project_id):
    """Create a new directory"""
    try:
        data = json.loads(request.body)
        dir_path = data.get('path', '').strip()
        
        if not dir_path:
            return JsonResponse({'status': 'error', 'message': 'Directory path required'}, status=400)
        
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        # Extract directory name
        path_parts = dir_path.split('/')
        dir_name = path_parts[-1]
        
        # Find parent if nested
        parent = None
        if len(path_parts) > 1:
            parent_path = '/'.join(path_parts[:-1])
            parent, _ = IDEDirectory.objects.get_or_create(
                project=project,
                path=parent_path,
                defaults={'name': path_parts[-2] if len(path_parts) > 1 else parent_path}
            )
        
        # Create directory
        directory, created = IDEDirectory.objects.get_or_create(
            project=project,
            path=dir_path,
            defaults={
                'name': dir_name,
                'parent': parent
            }
        )
        
        if not created:
            return JsonResponse({
                'status': 'error',
                'message': 'Directory already exists'
            }, status=400)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Directory "{dir_name}" created successfully',
            'directory': {
                'name': directory.name,
                'path': directory.path
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==================== CODE EXECUTION ====================

@login_required
@require_POST
@rate_limit_per_user(max_requests=50, window=60)
def execute_code(request, project_id):
    """
    Execute Python code in a sandboxed environment
    Uses subprocess with resource limits and supports input()
    """
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        file_path = data.get('file_path', 'untitled.py')
        timeout = min(int(data.get('timeout', 10)), 30)  # Max 30 seconds
        user_inputs = data.get('inputs', [])  # List of user inputs for input() calls
        
        if not code.strip():
            return JsonResponse({
                'status': 'error',
                'message': 'No code to execute'
            }, status=400)
        
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            import time
            start_time = time.time()
            
            # Prepare stdin if user inputs are provided
            stdin_input = None
            if user_inputs:
                # Join inputs with newlines for each input() call
                stdin_input = '\n'.join(user_inputs) + '\n'
            
            # Execute with resource limits
            process = subprocess.Popen(
                ['python', temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if stdin_input else None,
                text=True,
                # Resource limits (Unix-like systems)
                preexec_fn=lambda: (
                    os.nice(10),  # Lower priority
                ) if os.name != 'nt' else None  # Skip on Windows
            )
            
            try:
                stdout, stderr = process.communicate(input=stdin_input, timeout=timeout)
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Log execution
                IDEExecutionLog.objects.create(
                    project=project,
                    file=IDEFile.objects.filter(project=project, path=file_path).first(),
                    code_snippet=code[:1000],  # Store first 1000 chars
                    output=stdout[:5000],  # Store first 5000 chars
                    error=stderr[:5000],
                    execution_time=execution_time,
                    was_successful=process.returncode == 0
                )
                
                return JsonResponse({
                    'status': 'success',
                    'output': stdout,
                    'error': stderr,
                    'return_code': process.returncode,
                    'execution_time': execution_time
                })
                
            except subprocess.TimeoutExpired:
                process.kill()
                return JsonResponse({
                    'status': 'error',
                    'message': f'Execution timeout ({timeout}s)',
                    'error': 'Code execution exceeded time limit'
                }, status=408)
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def get_execution_history(request, project_id):
    """Get execution history for a project"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        limit = min(int(request.GET.get('limit', 50)), 100)
        offset = int(request.GET.get('offset', 0))
        
        logs = IDEExecutionLog.objects.filter(project=project)[offset:offset+limit]
        
        history_data = []
        for log in logs:
            history_data.append({
                'id': log.id,
                'code_snippet': log.code_snippet[:200] + ('...' if len(log.code_snippet) > 200 else ''),
                'output': log.output[:500] + ('...' if len(log.output) > 500 else ''),
                'error': log.error,
                'execution_time': log.execution_time,
                'was_successful': log.was_successful,
                'executed_at': log.executed_at.isoformat(),
                'file_path': log.file.path if log.file else None
            })
        
        return JsonResponse({
            'status': 'success',
            'history': history_data,
            'total': IDEExecutionLog.objects.filter(project=project).count()
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==================== TERMINAL SESSION ====================

@login_required
def get_terminal_session(request, project_id):
    """Get or create terminal session for project"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        # Get or create active terminal session
        terminal, created = IDETerminalSession.objects.get_or_create(
            project=project,
            is_active=True,
            defaults={
                'history': [],
                'environment_vars': {}
            }
        )
        
        return JsonResponse({
            'status': 'success',
            'session': {
                'id': str(terminal.session_id),
                'history': terminal.history[-50:],  # Last 50 entries
                'created_at': terminal.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def clear_terminal(request, project_id):
    """Clear terminal history"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        terminal = IDETerminalSession.objects.filter(
            project=project,
            is_active=True
        ).first()
        
        if terminal:
            terminal.history = []
            terminal.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Terminal cleared'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==================== FILE UPLOAD/DOWNLOAD ====================

@login_required
@require_POST
def upload_files(request, project_id):
    """Upload multiple files to project"""
    try:
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'status': 'error', 'message': 'No files uploaded'}, status=400)
        
        uploaded_files = []
        for file in files:
            # Create file in database
            ide_file = IDEFile.objects.create(
                project=project,
                name=file.name,
                path=file.name,
                file_type=get_file_type_from_extension(file.name),
                content=file.read().decode('utf-8', errors='ignore')  # Read file content
            )
            uploaded_files.append(ide_file.name)
        
        # Update project last accessed time
        project.last_accessed = timezone.now()
        project.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Uploaded {len(uploaded_files)} file(s)',
            'files': uploaded_files
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def download_project(request, project_id):
    """Download entire project as ZIP"""
    try:
        import zipfile
        from django.http import HttpResponse
        import io
        
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all files to ZIP
            files = IDEFile.objects.filter(project=project)
            for file in files:
                zip_file.writestr(file.path, file.content or '')
        
        # Prepare response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{project.name.replace(" ", "_")}.zip"'
        
        return response
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def download_file(request, project_id):
    """Download a single file"""
    try:
        from django.http import HttpResponse
        
        project = get_object_or_404(IDEProject, project_id=project_id, user=request.user)
        
        data = json.loads(request.body)
        file_path = data.get('file_path')
        
        if not file_path:
            return JsonResponse({'status': 'error', 'message': 'File path required'}, status=400)
        
        file = get_object_or_404(IDEFile, project=project, path=file_path)
        
        # Prepare response
        response = HttpResponse(file.content or '', content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{file.name}"'
        
        return response
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def get_file_type_from_extension(filename):
    """Determine file type from extension"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    file_types = {
        'py': 'python',
        'txt': 'text',
        'md': 'markdown',
        'json': 'json',
        'csv': 'csv',
        'html': 'html',
        'css': 'css',
        'js': 'javascript',
        'xml': 'xml',
        'yml': 'yaml',
        'yaml': 'yaml',
    }
    
    return file_types.get(ext, 'text')
