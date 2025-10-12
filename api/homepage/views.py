
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
            
            # Create additional example files for data science
            matplotlib_example = '''import matplotlib.pyplot as plt
import numpy as np

print("Creating advanced matplotlib visualizations...")

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

x = np.linspace(0, 10, 100)
ax1.plot(x, np.sin(x), 'b-', label='sin(x)')
ax1.plot(x, np.cos(x), 'r--', label='cos(x)')
ax1.set_title('Trigonometric Functions')
ax1.legend()
ax1.grid(True, alpha=0.3)

n = 50
x = np.random.randn(n)
y = np.random.randn(n)
colors = np.random.rand(n)
ax2.scatter(x, y, c=colors, alpha=0.6)
ax2.set_title('Random Scatter Plot')

data = np.random.normal(100, 15, 1000)
ax3.hist(data, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
ax3.set_title('Normal Distribution')
ax3.set_xlabel('Value')
ax3.set_ylabel('Frequency')

categories = ['Python', 'Java', 'JavaScript', 'C++', 'Go']
values = [85, 70, 75, 60, 55]
ax4.bar(categories, values, color=['#3776ab', '#ed8b00', '#f7df1e', '#00599c', '#00add8'])
ax4.set_title('Programming Languages Popularity')
ax4.set_ylabel('Popularity Score')

plt.tight_layout()
plt.show()

print("Advanced plots created successfully!")
'''

            pandas_example = '''import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("Pandas Data Analysis Demo...")

np.random.seed(42)

sales_data = {
    'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'Product_A': [100, 120, 140, 110, 160, 180],
    'Product_B': [80, 90, 100, 95, 110, 120],
    'Product_C': [60, 70, 80, 85, 90, 95]
}
df_sales = pd.DataFrame(sales_data)

print("Sales Data:")
print(df_sales)
print("\\nData Info:")
print(df_sales.describe())

df_sales.set_index('Month').plot(kind='bar', figsize=(10, 6))
plt.title('Monthly Sales by Product')
plt.ylabel('Sales Amount')
plt.xticks(rotation=45)
plt.legend(title='Products')
plt.tight_layout()
plt.show()

students_data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank'],
    'Math': np.random.randint(70, 100, 6),
    'Science': np.random.randint(65, 95, 6),
    'English': np.random.randint(75, 100, 6),
    'History': np.random.randint(60, 90, 6)
}
df_students = pd.DataFrame(students_data)

print("\\nStudent Grades:")
print(df_students)

df_students['Average'] = df_students[['Math', 'Science', 'English', 'History']].mean(axis=1)
print("\\nWith Averages:")
print(df_students)

plt.figure(figsize=(12, 8))

plt.subplot(2, 2, 1)
df_students[['Math', 'Science', 'English', 'History']].plot(kind='box')
plt.title('Grade Distribution by Subject')

plt.subplot(2, 2, 2)
df_students['Average'].hist(bins=10, alpha=0.7, color='lightgreen')
plt.title('Average Grade Distribution')
plt.xlabel('Average Grade')
plt.ylabel('Number of Students')

plt.subplot(2, 2, 3)
subject_means = df_students[['Math', 'Science', 'English', 'History']].mean()
subject_means.plot(kind='pie', autopct='%1.1f%%')
plt.title('Subject Performance Distribution')

plt.subplot(2, 2, 4)
df_students.set_index('Name')[['Math', 'Science', 'English', 'History']].plot(kind='bar')
plt.title('Individual Student Performance')
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()

print("Pandas analysis complete!")
'''

            numpy_example = '''import numpy as np
import matplotlib.pyplot as plt

print("NumPy Scientific Computing Demo...")

print("\\nArray Operations:")
arr1 = np.array([1, 2, 3, 4, 5])
arr2 = np.array([5, 4, 3, 2, 1])

print(f"Array 1: {arr1}")
print(f"Array 2: {arr2}")
print(f"Addition: {arr1 + arr2}")
print(f"Multiplication: {arr1 * arr2}")
print(f"Dot product: {np.dot(arr1, arr2)}")

print("\\nMatrix Operations:")
matrix_a = np.random.randint(1, 10, (3, 3))
matrix_b = np.random.randint(1, 10, (3, 3))

print("Matrix A:")
print(matrix_a)
print("\\nMatrix B:")
print(matrix_b)
print("\\nMatrix Multiplication:")
print(np.matmul(matrix_a, matrix_b))

print("\\nStatistical Operations:")
data = np.random.normal(100, 15, 1000)
print(f"Mean: {np.mean(data):.2f}")
print(f"Standard Deviation: {np.std(data):.2f}")
print(f"Min: {np.min(data):.2f}")
print(f"Max: {np.max(data):.2f}")

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

x = np.linspace(0, 4*np.pi, 1000)
y1 = np.sin(x)
y2 = np.cos(x)
ax1.plot(x, y1, 'b-', label='sin(x)', linewidth=2)
ax1.plot(x, y2, 'r-', label='cos(x)', linewidth=2)
ax1.set_title('Trigonometric Functions')
ax1.legend()
ax1.grid(True, alpha=0.3)

x_3d = np.linspace(-5, 5, 50)
y_3d = np.linspace(-5, 5, 50)
X, Y = np.meshgrid(x_3d, y_3d)
Z = np.sin(np.sqrt(X**2 + Y**2))
contour = ax2.contour(X, Y, Z, levels=20)
ax2.set_title('Contour Plot of sin(√(x²+y²))')

ax3.hist(data, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
ax3.set_title('Normal Distribution (μ=100, σ=15)')
ax3.set_xlabel('Value')
ax3.set_ylabel('Frequency')

t = np.linspace(0, 1, 500)
signal = np.sin(2*np.pi*5*t) + 0.5*np.sin(2*np.pi*10*t) + 0.3*np.random.randn(500)
fft = np.fft.fft(signal)
freqs = np.fft.fftfreq(len(t), t[1]-t[0])
ax4.plot(freqs[:len(freqs)//2], np.abs(fft[:len(fft)//2]))
ax4.set_title('FFT of Mixed Signal')
ax4.set_xlabel('Frequency (Hz)')
ax4.set_ylabel('Magnitude')

plt.tight_layout()
plt.show()

print("NumPy demonstrations complete!")
'''

            # Create the example files
            try:
                PythonCodeSession.objects.get_or_create(
                    user=user,
                    filename='matplotlib_examples.py',
                    defaults={'code_content': matplotlib_example}
                )
                PythonCodeSession.objects.get_or_create(
                    user=user,
                    filename='pandas_analysis.py',
                    defaults={'code_content': pandas_example}
                )
                PythonCodeSession.objects.get_or_create(
                    user=user,
                    filename='numpy_computing.py',
                    defaults={'code_content': numpy_example}
                )
            except:
                pass
        
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

@login_required
@csrf_exempt
def save_user_data(request):
    if request.method == 'POST':
        try:
            user_data = json.loads(request.body)
            user = request.user
            
            # Save current code
            if user_data.get('currentCode'):
                session, created = PythonCodeSession.objects.get_or_create(
                    user=user,
                    filename='main.py',
                    defaults={'code_content': user_data['currentCode']}
                )
                if not created:
                    session.code_content = user_data['currentCode']
                    session.save()
            
            # Save scripts
            if user_data.get('scripts'):
                for key, content in user_data['scripts'].items():
                    if key.startswith('python_script_'):
                        filename = key.replace('python_script_', '')
                        session, created = PythonCodeSession.objects.get_or_create(
                            user=user,
                            filename=filename,
                            defaults={'code_content': content}
                        )
                        if not created:
                            session.code_content = content
                            session.save()
                    elif key.startswith('data_file_'):
                        filename = key.replace('data_file_', '')
                        file_obj, created = UserFiles.objects.get_or_create(
                            user=user,
                            filename=filename,
                            defaults={'content': content, 'is_system_file': False}
                        )
                        if not created:
                            file_obj.content = content
                            file_obj.save()
            
            # Save notebook data to user profile or create a new model for it
            if user_data.get('notebooks'):
                # For now, save as a special PythonCodeSession
                session, created = PythonCodeSession.objects.get_or_create(
                    user=user,
                    filename='_notebook_data.json',
                    defaults={'code_content': json.dumps(user_data['notebooks'])}
                )
                if not created:
                    session.code_content = json.dumps(user_data['notebooks'])
                    session.save()
            
            return JsonResponse({'status': 'success', 'message': 'Data saved successfully'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

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