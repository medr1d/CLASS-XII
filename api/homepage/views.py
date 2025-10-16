
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.db import models
from .models import PythonCodeSession, UserFiles, UserProfile
from auth_app.rate_limiting import rate_limit_per_user
import json
from django.conf import settings

def home(request):
    return render(request, 'homepage/index.html', {
        'user': request.user
    })

@login_required
def python_environment(request):
    user = request.user
    output = ""
    error = ""
    terminal_output = ""
    execution_success = False
    
    try:
        if request.method == "POST":
            code_content = request.POST.get('code_content', '')
            action = request.POST.get('action', '')
            filename = request.POST.get('filename', 'main.py')
            
            if action == 'execute':
                if code_content:
                    python_session, created = PythonCodeSession.objects.get_or_create(
                        user=user,
                        filename=filename,
                        defaults={'code_content': code_content}
                    )
                    if not created:
                        python_session.code_content = code_content
                        python_session.save()
                
                terminal_output = "Code execution is handled client-side. Use the browser console to see output."
                execution_success = True
            
            elif action == 'save_file':
                if filename and code_content is not None:
                    if not filename.endswith('.py'):
                        filename += '.py'
                    
                    # Check file limit (max 10 files per user)
                    existing_count = PythonCodeSession.objects.filter(user=user).count()
                    
                    try:
                        # Try to get existing file
                        python_session = PythonCodeSession.objects.get(user=user, filename=filename)
                        # File exists, update it
                        python_session.code_content = code_content
                        python_session.save()
                        terminal_output = f"File '{filename}' updated successfully"
                        execution_success = True
                    except PythonCodeSession.DoesNotExist:
                        # New file - check limit
                        if existing_count >= 10:
                            terminal_output = f"Error: Maximum 10 files allowed. Delete a file first."
                            execution_success = False
                        else:
                            # Create new file
                            try:
                                python_session = PythonCodeSession.objects.create(
                                    user=user,
                                    filename=filename,
                                    code_content=code_content
                                )
                                terminal_output = f"File '{filename}' saved to your account"
                                execution_success = True
                            except IntegrityError:
                                # Race condition - file was created by another request
                                terminal_output = f"Error: File '{filename}' already exists"
                                execution_success = False
            
            elif action == 'load_file':
                try:
                    python_session = PythonCodeSession.objects.get(user=user, filename=filename)
                    terminal_output = f"File '{filename}' loaded from your account"
                    execution_success = True
                except PythonCodeSession.DoesNotExist:
                    terminal_output = f"File '{filename}' not found in your account"
                    execution_success = False
            
            elif action == 'delete_file':
                try:
                    python_session = PythonCodeSession.objects.get(user=user, filename=filename)
                    python_session.delete()
                    terminal_output = f"File '{filename}' deleted from your account"
                    execution_success = True
                except PythonCodeSession.DoesNotExist:
                    terminal_output = f"File '{filename}' not found in your account"
                    execution_success = False
        
        current_filename = request.POST.get('filename', 'main.py')
        try:
            current_session = PythonCodeSession.objects.get(user=user, filename=current_filename)
            code_content = current_session.code_content
        except PythonCodeSession.DoesNotExist:
            code_content = f'''print("Hello, Python Terminal!")
print("This code runs in your browser using Pyodide!")
print(f"Welcome back, {user.username}!")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

print("\\nCreating a sample plot...")

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', linewidth=2, label='sin(x)')
plt.plot(x, np.cos(x), 'r--', linewidth=2, label='cos(x)')
plt.title('Trigonometric Functions')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

print("\\nReading files...")
try:
    with open('text.txt', 'r') as f:
        data = f.read()
        print("text.txt content:", data[:50] + "..." if len(data) > 50 else data)
except FileNotFoundError:
    print("text.txt not found")

try:
    df = pd.read_csv('tester.csv')
    print("\\nCSV Data Analysis:")
    print(df.head())
    print("\\nData Info:")
    print(df.describe())
except Exception as e:
    print(f"CSV error: {{e}}")

name = input("\\nWhat is your name? ")
print(f"Hello, {{name}}! Enjoy exploring Python with scientific libraries!")

print("\\nAvailable libraries: numpy, pandas, matplotlib, scipy, scikit-learn, seaborn")
print("Your Python files are saved to your account!")
'''
            PythonCodeSession.objects.create(
                user=user,
                filename=current_filename,
                code_content=code_content
            )
        
        saved_files = PythonCodeSession.objects.filter(user=user).values_list('filename', flat=True)
        
        system_files = ['text.txt', 'tester.csv', 'binary.dat']
        for system_file in system_files:
            user_file, created = UserFiles.objects.get_or_create(
                user=user,
                filename=system_file,
                defaults={
                    'is_system_file': True,
                    'file_type': 'text' if system_file.endswith('.txt') else 
                               'csv' if system_file.endswith('.csv') else 'binary'
                }
            )
            if created:
                if system_file == 'text.txt':
                    user_file.content = f"Hello {user.username}!\nThis is your personal text file.\nYou can modify this content and it will be saved to your account."
                elif system_file == 'tester.csv':
                    user_file.content = f"name,age,city,user\nJohn,25,NYC,{user.username}\nJane,30,LA,guest\nBob,35,Chicago,{user.username}"
                elif system_file == 'binary.dat':
                    user_file.content = f"Personal binary data for {user.username}"
                user_file.save()
        
        text_file = UserFiles.objects.get(user=user, filename='text.txt')
        csv_file = UserFiles.objects.get(user=user, filename='tester.csv')
        binary_file = UserFiles.objects.get(user=user, filename='binary.dat')
        
        text_content = text_file.content
        csv_content = csv_file.content
        binary_content = f"Personal binary data for {user.username}\nLength: {len(binary_file.content)} characters"
        binary_hex = "Your personal binary file (simplified view)"
        
        migration_needed = False
        
    except Exception as e:
        code_content = f'''print("Hello, {user.username}!")
print("Database setup required for full functionality")
print("Visit /migrate/ to initialize your personal data storage")

name = input("What is your name? ")
print(f"Hello, {{name}}!")
'''
        
        text_content = f"Database setup needed. Visit /migrate/ to initialize.\nWelcome {user.username}!"
        csv_content = "name,age,city\nSetup,Required,Migration"
        binary_content = "Migration needed"
        binary_hex = "Please run migrations"
        saved_files = []
        current_filename = 'main.py'
        migration_needed = True
        
        if not terminal_output:
            terminal_output = f"Database setup required. Please visit /migrate/ to initialize your account data."
    
    # Get user's theme preference
    user_theme = 'default'
    if hasattr(user, 'profile'):
        user_theme = user.profile.theme
    
    response = render(request, 'homepage/python_environment.html', {
        'terminal_output': terminal_output,
        'binary_content': binary_content,
        'csv_content': csv_content,
        'text_content': text_content,
        'binary_hex': binary_hex,
        'code_content': code_content,
        'saved_files': list(saved_files) if saved_files else [],
        'execution_success': execution_success,
        'current_filename': current_filename,
        'migration_needed': migration_needed,
        'user_theme': user_theme,
    })
    
    response['Cross-Origin-Opener-Policy'] = 'same-origin'
    response['Cross-Origin-Embedder-Policy'] = 'require-corp'
    
    return response

@login_required
def get_files(request):
    user = request.user
    
    try:
        text_file = UserFiles.objects.get(user=user, filename='text.txt')
        csv_file = UserFiles.objects.get(user=user, filename='tester.csv')
        binary_file = UserFiles.objects.get(user=user, filename='binary.dat')
        
        python_files = {}
        files_list = []
        for session in PythonCodeSession.objects.filter(user=user):
            python_files[session.filename] = session.code_content
            # Add file info for account page display
            files_list.append({
                'filename': session.filename,
                'updated_at': session.updated_at.isoformat(),
                'created_at': session.created_at.isoformat(),
                'size': len(session.code_content)
            })
        
        return JsonResponse({
            'text_content': text_file.content,
            'csv_content': csv_file.content,
            'binary_content': binary_file.content,
            'binary_hex': f"User file for {user.username}",
            'python_files': python_files,
            'saved_files': list(python_files.keys()),
            'files': files_list  # Added for account page
        })
        
    except UserFiles.DoesNotExist:
        return JsonResponse({
            'text_content': f"Welcome {user.username}! Your personal text file.",
            'csv_content': f"name,age,city,user\n{user.username},25,Home,active",
            'binary_content': f"Personal data for {user.username}",
            'python_files': {},
            'saved_files': [],
            'files': []  # Added for account page
        })

@login_required
@ensure_csrf_cookie
@rate_limit_per_user(max_requests=100, window=3600)  # 100 saves per hour
def save_user_data(request):
    """Save user data with CSRF protection and file limit enforcement."""
    # Only accept POST requests
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST requests are allowed'
        }, status=405)
    
    try:
        user_data = json.loads(request.body)
        user = request.user
        
        # Log what we're receiving
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"💾 Saving data for user {user.username}")
        logger.info(f"📝 Scripts to save: {list(user_data.get('scripts', {}).keys())}")
        
        # Check total file limit before saving
        existing_files = PythonCodeSession.objects.filter(user=user).count()
        files_saved = 0
        files_updated = 0
        files_skipped = 0
        
        # Save current code
        if user_data.get('currentCode'):
            try:
                session = PythonCodeSession.objects.get(user=user, filename='main.py')
                session.code_content = user_data['currentCode']
                session.save()
                files_updated += 1
                logger.info(f"✅ Updated main.py")
            except PythonCodeSession.DoesNotExist:
                if existing_files >= 10:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Maximum 10 files allowed. Delete some files first.'
                    }, status=400)
                try:
                    PythonCodeSession.objects.create(
                        user=user,
                        filename='main.py',
                        code_content=user_data['currentCode']
                    )
                    files_saved += 1
                    logger.info(f"✅ Created main.py")
                except IntegrityError:
                    # File was created by another request
                    pass
        
        # Save scripts with file limit check
        if user_data.get('scripts'):
            for key, content in user_data['scripts'].items():
                if key.startswith('python_script_'):
                    filename = key.replace('python_script_', '')
                    try:
                        session = PythonCodeSession.objects.get(user=user, filename=filename)
                        session.code_content = content
                        session.save()
                        files_updated += 1
                        logger.info(f"✅ Updated {filename}")
                    except PythonCodeSession.DoesNotExist:
                        # Check limit before creating
                        current_count = PythonCodeSession.objects.filter(user=user).count()
                        if current_count >= 10:
                            files_skipped += 1
                            logger.warning(f"⚠️ Skipped {filename} - file limit reached")
                            continue  # Skip this file
                        try:
                            PythonCodeSession.objects.create(
                                user=user,
                                filename=filename,
                                code_content=content
                            )
                            files_saved += 1
                            logger.info(f"✅ Created {filename}")
                        except IntegrityError:
                            logger.warning(f"⚠️ IntegrityError for {filename}")
                            pass  # File exists, skip
                            
                elif key.startswith('data_file_'):
                    filename = key.replace('data_file_', '')
                    try:
                        file_obj = UserFiles.objects.get(user=user, filename=filename)
                        file_obj.content = content
                        file_obj.save()
                        files_updated += 1
                        logger.info(f"✅ Updated data file {filename}")
                    except UserFiles.DoesNotExist:
                        try:
                            UserFiles.objects.create(
                                user=user,
                                filename=filename,
                                content=content,
                                is_system_file=False
                            )
                            files_saved += 1
                            logger.info(f"✅ Created data file {filename}")
                        except IntegrityError:
                            pass  # File exists, skip
        
        # Save notebook data
        if user_data.get('notebooks'):
            try:
                session = PythonCodeSession.objects.get(user=user, filename='_notebook_data.json')
                session.code_content = json.dumps(user_data['notebooks'])
                session.save()
            except PythonCodeSession.DoesNotExist:
                try:
                    PythonCodeSession.objects.create(
                        user=user,
                        filename='_notebook_data.json',
                        code_content=json.dumps(user_data['notebooks'])
                    )
                except IntegrityError:
                    pass
        
        logger.info(f"📊 Save complete: {files_saved} created, {files_updated} updated, {files_skipped} skipped")
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Data saved successfully',
            'stats': {
                'created': files_saved,
                'updated': files_updated,
                'skipped': files_skipped
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def load_user_data(request):
    try:
        user = request.user
        user_data = {
            'currentCode': '',
            'scripts': {},
            'notebooks': {},
            'settings': {
                'theme': 'monokai',
                'fontSize': 14,
                'lastLoaded': timezone.now().isoformat()
            }
        }
        
        # Load current code (main.py)
        try:
            main_session = PythonCodeSession.objects.get(user=user, filename='main.py')
            user_data['currentCode'] = main_session.code_content
        except PythonCodeSession.DoesNotExist:
            pass
        
        # Load all Python scripts
        for session in PythonCodeSession.objects.filter(user=user):
            if session.filename != 'main.py' and not session.filename.endswith('.json'):
                user_data['scripts'][f'python_script_{session.filename}'] = session.code_content
        
        # Load data files
        for file_obj in UserFiles.objects.filter(user=user, is_system_file=False):
            user_data['scripts'][f'data_file_{file_obj.filename}'] = file_obj.content
        
        # Load notebook data
        try:
            notebook_session = PythonCodeSession.objects.get(user=user, filename='_notebook_data.json')
            user_data['notebooks'] = json.loads(notebook_session.code_content)
        except (PythonCodeSession.DoesNotExist, json.JSONDecodeError):
            pass
        
        return JsonResponse(user_data)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def delete_file(request):
    """Delete a user's file from the database"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename', '')
        
        if not filename:
            return JsonResponse({'status': 'error', 'message': 'No filename provided'}, status=400)
        
        user = request.user
        deleted_count = 0
        
        # Try to delete from PythonCodeSession
        deleted_sessions = PythonCodeSession.objects.filter(user=user, filename=filename).delete()
        deleted_count += deleted_sessions[0]
        
        # Try to delete from UserFiles
        deleted_files = UserFiles.objects.filter(user=user, filename=filename, is_system_file=False).delete()
        deleted_count += deleted_files[0]
        
        if deleted_count > 0:
            print(f"✅ Deleted file '{filename}' for user {user.username}")
            return JsonResponse({
                'status': 'success',
                'message': f'File {filename} deleted successfully',
                'deleted_count': deleted_count
            })
        else:
            return JsonResponse({
                'status': 'warning',
                'message': f'File {filename} not found in database'
            })
            
    except Exception as e:
        print(f"❌ Error deleting file: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@rate_limit_per_user(max_requests=100, window=60)
def save_execution_history(request):
    """Save code execution history"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            output = data.get('output', '')
            error = data.get('error', '')
            execution_time = data.get('execution_time', 0)
            filename = data.get('filename', 'untitled.py')
            was_successful = data.get('was_successful', True)
            
            from .models import ExecutionHistory
            
            # Limit history to last 100 entries per user
            history_count = ExecutionHistory.objects.filter(user=request.user).count()
            if history_count >= 100:
                # Delete oldest entries
                oldest = ExecutionHistory.objects.filter(user=request.user).order_by('executed_at')[:history_count-99]
                ExecutionHistory.objects.filter(id__in=[h.id for h in oldest]).delete()
            
            history = ExecutionHistory.objects.create(
                user=request.user,
                code_snippet=code,
                output=output,
                error=error,
                execution_time=execution_time,
                filename=filename,
                was_successful=was_successful
            )
            
            return JsonResponse({
                'status': 'success',
                'history_id': history.id
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def get_execution_history(request):
    """Retrieve execution history for the user"""
    try:
        from .models import ExecutionHistory
        
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        history = ExecutionHistory.objects.filter(user=request.user)[offset:offset+limit]
        
        history_data = []
        for h in history:
            history_data.append({
                'id': h.id,
                'code_snippet': h.code_snippet[:200] + ('...' if len(h.code_snippet) > 200 else ''),
                'full_code': h.code_snippet,
                'output': h.output[:500] + ('...' if len(h.output) > 500 else ''),
                'error': h.error,
                'execution_time': h.execution_time,
                'filename': h.filename,
                'was_successful': h.was_successful,
                'executed_at': h.executed_at.isoformat()
            })
        
        return JsonResponse({
            'status': 'success',
            'history': history_data,
            'total': ExecutionHistory.objects.filter(user=request.user).count()
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def share_code(request):
    """Create a shareable link for code"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title', 'Untitled')
            code_content = data.get('code', '')
            description = data.get('description', '')
            is_public = data.get('is_public', True)
            expires_days = data.get('expires_days', None)
            
            from .models import SharedCode
            from datetime import timedelta
            
            expires_at = None
            if expires_days:
                expires_at = timezone.now() + timedelta(days=int(expires_days))
            
            shared_code = SharedCode.objects.create(
                user=request.user,
                title=title,
                code_content=code_content,
                description=description,
                is_public=is_public,
                expires_at=expires_at
            )
            
            share_url = f"{request.scheme}://{request.get_host()}/share/{shared_code.share_id}"
            
            return JsonResponse({
                'status': 'success',
                'share_id': str(shared_code.share_id),
                'share_url': share_url
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


def view_shared_code(request, share_id):
    """View a shared code snippet"""
    try:
        from .models import SharedCode
        
        shared_code = SharedCode.objects.get(share_id=share_id)
        
        # Check if expired
        if shared_code.expires_at and timezone.now() > shared_code.expires_at:
            return render(request, 'homepage/shared_code_expired.html')
        
        # Check if public or user is owner
        if not shared_code.is_public and (not request.user.is_authenticated or request.user != shared_code.user):
            return render(request, 'homepage/shared_code_private.html')
        
        # Increment view count
        shared_code.increment_view_count()
        
        return render(request, 'homepage/shared_code.html', {
            'shared_code': shared_code,
            'is_owner': request.user.is_authenticated and request.user == shared_code.user
        })
        
    except SharedCode.DoesNotExist:
        return render(request, 'homepage/shared_code_not_found.html', status=404)


@login_required
def fork_shared_code(request, share_id):
    """Fork a shared code to user's account"""
    try:
        from .models import SharedCode
        
        shared_code = SharedCode.objects.get(share_id=share_id)
        
        # Create a new file in user's account
        base_filename = f"forked_{shared_code.title.replace(' ', '_')}.py"
        filename = base_filename
        counter = 1
        
        while PythonCodeSession.objects.filter(user=request.user, filename=filename).exists():
            filename = f"forked_{shared_code.title.replace(' ', '_')}_{counter}.py"
            counter += 1
        
        PythonCodeSession.objects.create(
            user=request.user,
            filename=filename,
            code_content=shared_code.code_content
        )
        
        # Increment fork count
        shared_code.increment_fork_count()
        
        return JsonResponse({
            'status': 'success',
            'filename': filename,
            'message': f'Code forked as {filename}'
        })
        
    except SharedCode.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Shared code not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def update_plot_theme(request):
    """Update dark mode plots setting"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dark_mode_plots = data.get('dark_mode_plots', True)
            
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.dark_mode_plots = dark_mode_plots
            profile.save(update_fields=['dark_mode_plots'])
            
            return JsonResponse({
                'status': 'success',
                'dark_mode_plots': dark_mode_plots
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def get_user_settings(request):
    """Get user settings including plot theme preference"""
    try:
        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        return JsonResponse({
            'status': 'success',
            'settings': {
                'theme': profile.theme,
                'dark_mode_plots': profile.dark_mode_plots,
                'paidUser': profile.paidUser
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# Collaborative Session Views

@login_required
@rate_limit_per_user(max_requests=10, window=60)
def create_collaborative_session(request):
    """Create a new collaborative coding session"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title', 'Untitled Session')
            description = data.get('description', '')
            is_public = data.get('is_public', True)
            initial_code = data.get('code', '')
            imported_files = data.get('imported_files', {})  # {filename: content}
            expires_days = data.get('expires_days', 7)  # Default 7 days
            
            from .models import SharedCode
            from datetime import timedelta
            
            expires_at = timezone.now() + timedelta(days=int(expires_days))
            
            session = SharedCode.objects.create(
                user=request.user,
                title=title,
                code_content=initial_code,
                description=description,
                session_type='collaborative',
                is_public=is_public,
                is_active=True,
                expires_at=expires_at,
                imported_files=imported_files,
                session_state={'code': initial_code, 'terminal_output': []}
            )
            
            # Owner automatically has edit permission
            from .models import SessionMember
            SessionMember.objects.create(
                session=session,
                user=request.user,
                permission='edit'
            )
            
            session_url = f"/python/code/{session.share_id}/"
            
            return JsonResponse({
                'status': 'success',
                'session_id': str(session.share_id),
                'session_url': session_url,
                'expires_at': session.expires_at.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def join_collaborative_session(request, session_id):
    """Join a collaborative session"""
    try:
        from .models import SharedCode, SessionMember
        
        session = SharedCode.objects.get(share_id=session_id, session_type='collaborative')
        
        # Check if expired
        if session.is_expired():
            return render(request, 'homepage/session_expired.html')
        
        # Check for inactivity and deactivate if needed
        if session.deactivate_if_inactive():
            return render(request, 'homepage/session_expired.html', {
                'message': 'This session has been closed due to inactivity (1 hour with no users).'
            })
        
        # Check if session is inactive
        if not session.is_active:
            return render(request, 'homepage/session_expired.html')
        
        # Check if public or user is owner
        if not session.is_public and request.user != session.user:
            # Check if user is already a member
            if not SessionMember.objects.filter(session=session, user=request.user).exists():
                return render(request, 'homepage/session_private.html')
        
        # Get or create member
        member, created = SessionMember.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={'permission': 'view'}
        )
        
        # Get imported files for owner
        can_import_export = (request.user == session.user)
        
        # Get list of owner's .py files for import
        user_py_files = []
        if can_import_export:
            user_py_files = list(PythonCodeSession.objects.filter(
                user=request.user,
                filename__endswith='.py'
            ).values('filename', 'code_content'))
        
        # Get user theme preference
        user_theme = 'default'
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                user_theme = user_profile.theme
            except UserProfile.DoesNotExist:
                pass
        
        context = {
            'session': session,
            'is_owner': request.user == session.user,
            'can_edit': member.permission == 'edit' or request.user == session.user,
            'can_import_export': can_import_export,
            'user_py_files': user_py_files,
            'member_permission': member.permission,
            'user_theme': user_theme,
        }
        
        return render(request, 'homepage/collaborative_session.html', context)
        
    except SharedCode.DoesNotExist:
        return render(request, 'homepage/session_not_found.html', status=404)


@login_required
def get_session_members(request, session_id):
    """Get list of members in a session"""
    try:
        from .models import SharedCode, SessionMember
        
        session = SharedCode.objects.get(share_id=session_id)
        
        # Only owner or members can see member list
        if request.user != session.user and not SessionMember.objects.filter(session=session, user=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Not authorized'}, status=403)
        
        members = SessionMember.objects.filter(session=session).select_related('user')
        
        members_data = [{
            'user_id': m.user.id,
            'username': m.user.username,
            'permission': m.permission,
            'is_online': m.is_online,
            'is_owner': m.user == session.user,
            'joined_at': m.joined_at.isoformat(),
            'last_active': m.last_active.isoformat()
        } for m in members]
        
        return JsonResponse({
            'status': 'success',
            'members': members_data
        })
        
    except SharedCode.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)


@login_required
def update_member_permission(request, session_id):
    """Update a member's permission (owner only)"""
    if request.method == 'POST':
        try:
            from .models import SharedCode, SessionMember
            
            session = SharedCode.objects.get(share_id=session_id)
            
            # Only owner can update permissions
            if request.user != session.user:
                return JsonResponse({'status': 'error', 'message': 'Not authorized'}, status=403)
            
            data = json.loads(request.body)
            user_id = data.get('user_id')
            permission = data.get('permission', 'view')
            
            if permission not in ['view', 'edit']:
                return JsonResponse({'status': 'error', 'message': 'Invalid permission'}, status=400)
            
            member = SessionMember.objects.get(session=session, user_id=user_id)
            member.permission = permission
            member.save(update_fields=['permission'])
            
            # Notify via WebSocket
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'code_session_{session_id}',
                {
                    'type': 'permission_changed',
                    'user_id': user_id,
                    'permission': permission,
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Permission updated'
            })
            
        except SharedCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
        except SessionMember.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Member not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def remove_member(request, session_id):
    """Remove a member from session (owner only)"""
    if request.method == 'POST':
        try:
            from .models import SharedCode, SessionMember
            
            session = SharedCode.objects.get(share_id=session_id)
            
            # Only owner can remove members
            if request.user != session.user:
                return JsonResponse({'status': 'error', 'message': 'Not authorized'}, status=403)
            
            data = json.loads(request.body)
            user_id = data.get('user_id')
            
            # Can't remove owner
            if user_id == session.user.id:
                return JsonResponse({'status': 'error', 'message': 'Cannot remove owner'}, status=400)
            
            member = SessionMember.objects.get(session=session, user_id=user_id)
            member.delete()
            
            # Notify via WebSocket
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'code_session_{session_id}',
                {
                    'type': 'member_removed',
                    'user_id': user_id,
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Member removed'
            })
            
        except SharedCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
        except SessionMember.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Member not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def import_files_to_session(request, session_id):
    """Import .py files from owner's saved files to session (owner only)"""
    if request.method == 'POST':
        try:
            from .models import SharedCode
            
            session = SharedCode.objects.get(share_id=session_id)
            
            # Only owner can import files
            if request.user != session.user:
                return JsonResponse({'status': 'error', 'message': 'Not authorized'}, status=403)
            
            data = json.loads(request.body)
            filenames = data.get('filenames', [])
            
            imported_files = session.imported_files.copy()
            
            for filename in filenames:
                try:
                    py_session = PythonCodeSession.objects.get(
                        user=request.user,
                        filename=filename
                    )
                    imported_files[filename] = py_session.code_content
                except PythonCodeSession.DoesNotExist:
                    continue
            
            session.imported_files = imported_files
            session.save(update_fields=['imported_files'])
            
            return JsonResponse({
                'status': 'success',
                'imported_files': imported_files
            })
            
        except SharedCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def export_session_to_files(request, session_id):
    """Export session code to owner's saved .py files (owner only)"""
    if request.method == 'POST':
        try:
            from .models import SharedCode
            
            session = SharedCode.objects.get(share_id=session_id)
            
            # Only owner can export files
            if request.user != session.user:
                return JsonResponse({'status': 'error', 'message': 'Not authorized'}, status=403)
            
            data = json.loads(request.body)
            filename = data.get('filename', f"{session.title}.py")
            code_content = data.get('code', session.session_state.get('code', ''))
            
            # Ensure .py extension
            if not filename.endswith('.py'):
                filename += '.py'
            
            # Create or update the file
            py_session, created = PythonCodeSession.objects.update_or_create(
                user=request.user,
                filename=filename,
                defaults={'code_content': code_content}
            )
            
            return JsonResponse({
                'status': 'success',
                'filename': filename,
                'message': f'{"Created" if created else "Updated"} {filename}'
            })
            
        except SharedCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def end_session(request, session_id):
    """End a collaborative session (owner only)"""
    if request.method == 'POST':
        try:
            from .models import SharedCode
            
            session = SharedCode.objects.get(share_id=session_id)
            
            # Only owner can end session
            if request.user != session.user:
                return JsonResponse({'status': 'error', 'message': 'Not authorized'}, status=403)
            
            session.is_active = False
            session.save(update_fields=['is_active'])
            
            return JsonResponse({
                'status': 'success',
                'message': 'Session ended'
            })
            
        except SharedCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


# ==================== COMMUNITY FEATURES ====================

@login_required
def community(request):
    """Community page with friends and DMs"""
    from .models import Friendship, UserStatus
    
    user = request.user
    
    # Get or create user status
    user_status, created = UserStatus.objects.get_or_create(user=user)
    user_status.update_status(is_online=True)
    
    # Get friends
    friends = Friendship.get_friends(user)
    friends_data = []
    for friend in friends:
        friend_status, _ = UserStatus.objects.get_or_create(user=friend)
        friends_data.append({
            'id': friend.id,
            'username': friend.username,
            'is_online': friend_status.is_online,
            'last_seen': friend_status.last_seen.isoformat() if friend_status.last_seen else '',
            'status_message': friend_status.status_message,
        })
    
    # Get pending friend requests
    pending_requests = Friendship.objects.filter(
        to_user=user,
        status='pending'
    ).select_related('from_user')
    
    # Get sent requests
    sent_requests = Friendship.objects.filter(
        from_user=user,
        status='pending'
    ).select_related('to_user')
    
    # Get user theme
    user_theme = 'default'
    try:
        from .models import UserProfile
        user_profile = UserProfile.objects.get(user=user)
        user_theme = user_profile.theme
    except UserProfile.DoesNotExist:
        pass
    
    context = {
        'user': user,
        'friends_json': json.dumps(friends_data),
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
        'user_theme': user_theme,
    }
    
    return render(request, 'homepage/community.html', context)


@login_required
def send_friend_request(request):
    """Send a friend request to another user"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            
            if not username:
                return JsonResponse({'status': 'error', 'message': 'Username required'}, status=400)
            
            # Find target user
            try:
                target_user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            
            # Can't friend yourself
            if target_user == request.user:
                return JsonResponse({'status': 'error', 'message': 'Cannot add yourself as a friend'}, status=400)
            
            # Check if friendship already exists
            from .models import Friendship
            existing = Friendship.objects.filter(
                models.Q(from_user=request.user, to_user=target_user) |
                models.Q(from_user=target_user, to_user=request.user)
            ).first()
            
            if existing:
                if existing.status == 'accepted':
                    return JsonResponse({'status': 'error', 'message': 'Already friends'}, status=400)
                elif existing.status == 'pending':
                    return JsonResponse({'status': 'error', 'message': 'Friend request already sent'}, status=400)
                elif existing.status == 'blocked':
                    return JsonResponse({'status': 'error', 'message': 'Cannot send friend request'}, status=400)
            
            # Create friend request
            friendship = Friendship.objects.create(
                from_user=request.user,
                to_user=target_user,
                status='pending'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': f'Friend request sent to {username}'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def respond_friend_request(request):
    """Accept or reject a friend request"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')
            action = data.get('action')  # 'accept' or 'reject'
            
            from .models import Friendship
            friendship = Friendship.objects.get(
                id=request_id,
                to_user=request.user,
                status='pending'
            )
            
            if action == 'accept':
                friendship.status = 'accepted'
                friendship.save()
                message = f'You are now friends with {friendship.from_user.username}'
            elif action == 'reject':
                friendship.status = 'rejected'
                friendship.save()
                message = 'Friend request rejected'
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)
            
            return JsonResponse({
                'status': 'success',
                'message': message
            })
            
        except Friendship.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Request not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def remove_friend(request):
    """Remove a friend"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            friend_id = data.get('friend_id')
            
            friend_user = User.objects.get(id=friend_id)
            
            from .models import Friendship
            friendship = Friendship.objects.filter(
                models.Q(from_user=request.user, to_user=friend_user) |
                models.Q(from_user=friend_user, to_user=request.user),
                status='accepted'
            ).first()
            
            if friendship:
                friendship.delete()
                return JsonResponse({
                    'status': 'success',
                    'message': f'Removed {friend_user.username} from friends'
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Not friends'}, status=404)
            
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def get_friends_list(request):
    """Get list of friends with online status"""
    try:
        from .models import Friendship, UserStatus
        
        friends = Friendship.get_friends(request.user)
        friends_data = []
        
        for friend in friends:
            friend_status, _ = UserStatus.objects.get_or_create(user=friend)
            friends_data.append({
                'id': friend.id,
                'username': friend.username,
                'is_online': friend_status.is_online,
                'last_seen': friend_status.last_seen.isoformat(),
                'status_message': friend_status.status_message,
            })
        
        return JsonResponse({
            'status': 'success',
            'friends': friends_data
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def update_status_message(request):
    """Update user's status message"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status_message = data.get('status_message', '')[:100]  # Max 100 chars
            
            from .models import UserStatus
            user_status, created = UserStatus.objects.get_or_create(user=request.user)
            user_status.status_message = status_message
            user_status.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Status updated'
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def send_direct_message(request):
    """Send a direct message to a friend"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipient_id = data.get('recipient_id')
            message = data.get('message', '').strip()
            
            if not message:
                return JsonResponse({'status': 'error', 'message': 'Message cannot be empty'}, status=400)
            
            recipient = User.objects.get(id=recipient_id)
            
            # Check if they are friends
            from .models import Friendship, DirectMessage
            if not Friendship.are_friends(request.user, recipient):
                return JsonResponse({'status': 'error', 'message': 'You must be friends to send messages'}, status=403)
            
            # Create message
            dm = DirectMessage.objects.create(
                sender=request.user,
                recipient=recipient,
                message=message
            )
            
            return JsonResponse({
                'status': 'success',
                'message_id': dm.id,
                'created_at': dm.created_at.isoformat()
            })
            
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)


@login_required
def get_direct_messages(request, user_id):
    """Get direct messages between current user and another user"""
    try:
        other_user = User.objects.get(id=user_id)
        
        from .models import DirectMessage
        messages = DirectMessage.objects.filter(
            models.Q(sender=request.user, recipient=other_user) |
            models.Q(sender=other_user, recipient=request.user)
        ).order_by('created_at').select_related('sender', 'recipient')
        
        # Mark messages as read
        DirectMessage.objects.filter(
            sender=other_user,
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        messages_data = []
        for msg in messages:
            # Get sender's profile picture
            try:
                profile = UserProfile.objects.get(user=msg.sender)
                profile_pic = profile.profile_picture_url
            except UserProfile.DoesNotExist:
                profile_pic = None
            
            messages_data.append({
                'id': msg.id,
                'sender_id': msg.sender.id,
                'sender_username': msg.sender.username,
                'sender_profile_picture': profile_pic,
                'message': msg.message,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
                'is_mine': msg.sender == request.user
            })
        
        return JsonResponse({
            'status': 'success',
            'messages': messages_data
        })
        
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# Profile Views
@login_required
def get_user_profile(request, user_id):
    """Get user profile information"""
    try:
        user = User.objects.get(id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        # Check if they're friends
        from .models import Friendship
        is_friend = Friendship.objects.filter(
            models.Q(from_user=request.user, to_user=user, status='accepted') | 
            models.Q(from_user=user, to_user=request.user, status='accepted')
        ).exists()
        
        # Get stats
        from .models import SharedCode
        shared_codes_count = SharedCode.objects.filter(user=user).count()
        
        profile_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email if is_friend or user == request.user else None,
            'profile_picture_url': profile.get_profile_picture_url(),
            'bio': profile.bio,
            'location': profile.location,
            'github_username': profile.github_username,
            'twitter_username': profile.twitter_username,
            'website': profile.website,
            'theme': profile.theme,
            'is_paid_user': profile.paidUser,
            'joined_date': user.date_joined.strftime('%B %Y'),
            'is_friend': is_friend,
            'is_own_profile': user == request.user,
            'stats': {
                'shared_codes': shared_codes_count,
                'friends_count': Friendship.objects.filter(
                    models.Q(from_user=user, status='accepted') | models.Q(to_user=user, status='accepted')
                ).count()
            }
        }
        
        return JsonResponse({
            'status': 'success',
            'profile': profile_data
        })
        
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def update_profile(request):
    """Update user profile information"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        # Update fields
        if 'bio' in data:
            profile.bio = data['bio'][:500]  # Max 500 chars
        if 'location' in data:
            profile.location = data['location'][:100]
        if 'github_username' in data:
            profile.github_username = data['github_username'][:100]
        if 'twitter_username' in data:
            profile.twitter_username = data['twitter_username'][:100]
        if 'website' in data:
            profile.website = data['website'][:200]
        
        profile.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Profile updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def upload_profile_picture(request):
    """Upload or remove profile picture"""
    
    # Handle DELETE request to remove profile picture
    if request.method == 'DELETE':
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.profile_picture_url = None
            profile.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Profile picture removed'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # Handle POST request to upload profile picture
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST or DELETE required'}, status=400)
    
    try:
        import vercel_blob
        import os
        
        # Check for both 'file' and 'profile_picture' field names
        file = request.FILES.get('profile_picture') or request.FILES.get('file')
        
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)
        
        # Validate file
        if not file.content_type.startswith('image/'):
            return JsonResponse({'status': 'error', 'message': 'File must be an image'}, status=400)
        
        # Max 5MB
        if file.size > 5 * 1024 * 1024:
            return JsonResponse({'status': 'error', 'message': 'File too large (max 5MB)'}, status=400)
        
        # Get Vercel Blob token
        blob_token = os.getenv('BLOB_READ_WRITE_TOKEN')
        if not blob_token:
            return JsonResponse({'status': 'error', 'message': 'Blob storage not configured'}, status=500)
        
        # Upload to Vercel Blob using vercel_blob library
        filename = f"profile_{request.user.id}_{int(timezone.now().timestamp())}.{file.name.split('.')[-1]}"
        
        # Read file content
        file_content = file.read()
        
        # Upload using vercel_blob.put()
        response = vercel_blob.put(filename, file_content, {})
        
        # Get the URL from response
        if response and 'url' in response:
            image_url = response['url']
            
            # Save to user profile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.profile_picture_url = image_url
            profile.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Profile picture uploaded',
                'url': image_url
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Upload failed: {str(response)}'
            }, status=500)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Profile picture upload error: {error_details}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
