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
from .models import LoginAttempt
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
        # Get client IP address
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
        
        # Check if IP is blocked due to too many failed attempts
        if LoginAttempt.is_blocked(ip_address):
            messages.error(request, 'Too many failed login attempts. Please try again in 5 minutes.')
            return render(request, 'auth_app/login.html')
        
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
                # Record failed login attempt
                LoginAttempt.record_attempt(ip_address, email)
                messages.error(request, 'Invalid credentials.')
                return render(request, 'auth_app/login.html')
                
        except User.DoesNotExist:
            # Record failed login attempt
            LoginAttempt.record_attempt(ip_address, email)
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
    
    users = User.objects.all().select_related('profile').order_by('id')
    
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
    """Update the paid status of a user. Only accessible by superusers."""
    
    # Check if user is superuser
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized. Admin access required.'
        }, status=403)
    
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
        
        # Get and validate parameters
        user_id = data.get('user_id')
        paid_status = data.get('paid_status')
        
        if user_id is None:
            return JsonResponse({
                'success': False,
                'error': 'Missing user_id parameter'
            }, status=400)
        
        if paid_status is None:
            return JsonResponse({
                'success': False,
                'error': 'Missing paid_status parameter'
            }, status=400)
        
        # Validate paid_status is boolean
        if not isinstance(paid_status, bool):
            return JsonResponse({
                'success': False,
                'error': 'paid_status must be a boolean value'
            }, status=400)
        
        # Get user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User with id {user_id} not found'
            }, status=404)
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Log the change
        old_status = profile.paidUser
        print(f'[ADMIN ACTION] {request.user.username} updating user {user.username} (ID: {user_id})')
        print(f'[ADMIN ACTION] Changing paidUser from {old_status} to {paid_status}')
        
        # Update the status
        profile.paidUser = paid_status
        profile.save(update_fields=['paidUser'])
        
        # Verify the change was saved
        profile.refresh_from_db()
        if profile.paidUser != paid_status:
            print(f'[ERROR] Failed to save paid status for user {user.username}')
            return JsonResponse({
                'success': False,
                'error': 'Failed to save changes to database'
            }, status=500)
        
        print(f'[SUCCESS] User {user.username} paid status successfully updated to {paid_status}')
        
        return JsonResponse({
            'success': True,
            'message': f'User {user.username} paid status updated to {"PAID" if paid_status else "FREE"}',
            'user_id': user_id,
            'username': user.username,
            'paid_status': paid_status
        })
        
    except Exception as e:
        print(f'[ERROR] Exception in update_paid_status: {type(e).__name__}: {str(e)}')
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)