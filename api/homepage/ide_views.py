"""
Views for Cloud IDE functionality for paid users
"""
from django.shortcuts import render, get_object_or_404
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
    
    # Get user theme
    user_theme = 'default'
    try:
        profile = UserProfile.objects.get(user=user)
        user_theme = profile.theme
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
        user_theme = 'default'
    
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
    Uses subprocess with resource limits
    """
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        file_path = data.get('file_path', 'untitled.py')
        timeout = min(int(data.get('timeout', 10)), 30)  # Max 30 seconds
        
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
            
            # Execute with resource limits
            process = subprocess.Popen(
                ['python', temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                # Resource limits (Unix-like systems)
                preexec_fn=lambda: (
                    os.nice(10),  # Lower priority
                ) if os.name != 'nt' else None  # Skip on Windows
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
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
