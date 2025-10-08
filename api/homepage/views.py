from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import PythonCodeSession, UserFiles
import io
import json
import sys
import traceback
import os
import subprocess
import pickle
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
                    
                    python_session, created = PythonCodeSession.objects.get_or_create(
                        user=user,
                        filename=filename,
                        defaults={'code_content': code_content}
                    )
                    if not created:
                        python_session.code_content = code_content
                        python_session.save()
                    
                    terminal_output = f"File '{filename}' saved to your account"
                    execution_success = True
            
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
print("This code runs in your browser!")
print(f"Welcome back, {user.username}!")

try:
    with open('text.txt', 'r') as f:
        data = f.read()
        print("text.txt content:", data[:50] + "..." if len(data) > 50 else data)
except FileNotFoundError:
    print("text.txt not found")

name = input("What is your name? ")
print(f"Hello, {{name}}!")

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
        for session in PythonCodeSession.objects.filter(user=user):
            python_files[session.filename] = session.code_content
        
        return JsonResponse({
            'text_content': text_file.content,
            'csv_content': csv_file.content,
            'binary_content': binary_file.content,
            'binary_hex': f"User file for {user.username}",
            'python_files': python_files,
            'saved_files': list(python_files.keys())
        })
        
    except UserFiles.DoesNotExist:
        return JsonResponse({
            'text_content': f"Welcome {user.username}! Your personal text file.",
            'csv_content': f"name,age,city,user\n{user.username},25,Home,active",
            'binary_content': f"Personal data for {user.username}",
            'python_files': {},
            'saved_files': []
        })









