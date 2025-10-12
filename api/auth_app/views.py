from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from homepage.models import UserProfile
import json
import re

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('auth_app:account')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not all([username, email, password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return render(request, 'auth_app/signup.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth_app/signup.html')
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'auth_app/signup.html')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messages.error(request, 'Username can only contain letters, numbers, and underscores.')
            return render(request, 'auth_app/signup.html')
        
        try:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return render(request, 'auth_app/signup.html')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered.')
                return render(request, 'auth_app/signup.html')
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('auth_app:login')
            
        except IntegrityError:
            messages.error(request, 'Email already registered.')
            return render(request, 'auth_app/signup.html')
        
        except Exception as e:
            messages.error(request, 'Registration failed. Please try again.')
            return render(request, 'auth_app/signup.html')
    
    return render(request, 'auth_app/signup.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('auth_app:account')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'auth_app/login.html')
        
        try:
            user = User.objects.get(email=email)
            authenticated_user = authenticate(request, username=user.username, password=password)
            
            if authenticated_user:
                login(request, authenticated_user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('auth_app:account')
            else:
                messages.error(request, 'Invalid credentials.')
                return render(request, 'auth_app/login.html')
                
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            return render(request, 'auth_app/login.html')
        
        except Exception as e:
            messages.error(request, 'Login failed. Please try again.')
            return render(request, 'auth_app/login.html')
    
    return render(request, 'auth_app/login.html')


@login_required
def account_view(request):
    return render(request, 'auth_app/account.html', {
        'user': request.user
    })

@login_required
def update_theme(request):
    if request.method == 'POST':
        theme = request.POST.get('theme', 'default')
        
        if theme in ['default', 'greydom']:
            # Get or create user profile
            from homepage.models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.theme = theme
            profile.save()
            
            messages.success(request, f'Theme updated to {theme.title()}!')
        else:
            messages.error(request, 'Invalid theme selected.')
    
    return redirect('auth_app:account')

def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'Goodbye {username}! You have been logged out successfully.')
    
    return redirect('auth_app:login')

@require_http_methods(["GET"])
def check_email_availability(request):
    email = request.GET.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'available': False, 'message': 'Email is required'})
    
    try:
        exists = User.objects.filter(email=email).exists()
        return JsonResponse({
            'available': not exists,
            'message': 'Email is available' if not exists else 'Email is already taken'
        })
    except Exception:
        return JsonResponse({'available': False, 'message': 'Error checking email availability'})

@require_http_methods(["GET"])
def check_username_availability(request):
    username = request.GET.get('username', '').strip()
    
    if not username:
        return JsonResponse({'available': False, 'message': 'Username is required'})
    
    try:
        exists = User.objects.filter(username=username).exists()
        return JsonResponse({
            'available': not exists,
            'message': 'Username is available' if not exists else 'Username is already taken'
        })
    except Exception:
        return JsonResponse({'available': False, 'message': 'Error checking username availability'})

def home_view(request):
    return render(request, 'auth_app/index.html')

@login_required
@ensure_csrf_cookie
def admin_panel_view(request):
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('auth_app:account')
    
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    
    paid_count = 0
    super_count = 0
    
    for user in users:
        if hasattr(user, 'profile') and user.profile.paidUser:
            paid_count += 1
        if user.is_superuser:
            super_count += 1
    
    return render(request, 'auth_app/admin_panel.html', {
        'users': users,
        'paid_users_count': paid_count,
        'free_users_count': len(users) - paid_count,
        'superusers_count': super_count,
    })

@login_required
@require_http_methods(["POST"])
def update_paid_status(request):
    print('update_paid_status called by:', request.user)
    if not request.user.is_superuser:
        print('User is not superuser')
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized. Admin access required.'
        }, status=403)
    try:
        data = json.loads(request.body)
        print('Received data:', data)
        user_id = data.get('user_id')
        paid_status = data.get('paid_status')
        if user_id is None or paid_status is None:
            print('Missing required parameters')
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters'
            }, status=400)
        user = User.objects.get(id=user_id)
        profile, created = UserProfile.objects.get_or_create(user=user)
        print(f'Updating user {user.username} paidUser from {profile.paidUser} to {paid_status}')
        profile.paidUser = paid_status
        profile.save()
        print('Update successful')
        return JsonResponse({
            'success': True,
            'message': f'User {user.username} paid status updated to {paid_status}'
        })
    except User.DoesNotExist:
        print('User not found')
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        print('Exception:', str(e))
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)