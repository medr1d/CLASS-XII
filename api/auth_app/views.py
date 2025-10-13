from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta
from homepage.models import UserProfile
from .models import LoginAttempt, EmailVerification, PasswordChangeRequest
from .email_utils import send_verification_email, send_verification_code_resend, send_password_change_code
from .rate_limiting import rate_limit, rate_limit_per_ip, rate_limit_per_user
import json
import re


def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@rate_limit_per_ip(max_requests=10, window=3600)  # 10 signups per hour per IP
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('auth_app:account')
    
    # Clean up old verifications periodically
    import random
    if random.randint(1, 100) == 1:
        EmailVerification.cleanup_old_verifications()
    
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
            # Use transaction to prevent race conditions
            with transaction.atomic():
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Username already exists.')
                    return render(request, 'auth_app/signup.html')
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email already registered.')
                    return render(request, 'auth_app/signup.html')
                
                # Delete any existing unverified verification for this email
                EmailVerification.objects.filter(email=email, verified=False).delete()
                
                # Create email verification record
                verification = EmailVerification.objects.create(
                    email=email,
                    username=username,
                    password=make_password(password)  # Store hashed password
                )
            
            # Send verification email (outside transaction to avoid locking)
            if send_verification_email(email, username, verification.verification_code):
                # Store email in session for verification page
                request.session['verification_email'] = email
                messages.success(request, f'Verification code sent to {email}. Please check your inbox.')
                return redirect('auth_app:verify_email')
            else:
                verification.delete()
                messages.error(request, 'Failed to send verification email. Please try again.')
                return render(request, 'auth_app/signup.html')
            
        except IntegrityError:
            messages.error(request, 'Email already registered.')
            return render(request, 'auth_app/signup.html')
        
        except Exception as e:
            messages.error(request, 'Registration failed. Please try again.')
            print(f"Signup error: {str(e)}")
            return render(request, 'auth_app/signup.html')
    
    return render(request, 'auth_app/signup.html')


@rate_limit_per_ip(max_requests=20, window=300)  # 20 login attempts per 5 minutes
def login_view(request):
    if request.user.is_authenticated:
        return redirect('auth_app:account')
    
    # Get client IP address
    ip_address = get_client_ip(request)
    
    # Clean up old login attempts periodically (1% chance each request)
    import random
    if random.randint(1, 100) == 1:
        LoginAttempt.cleanup_old_attempts()
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'auth_app/login.html')
        
        # Check if IP is blocked
        if LoginAttempt.is_blocked(ip_address):
            remaining_time = LoginAttempt.get_time_until_unblock(ip_address)
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            
            if minutes > 0:
                time_msg = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
            else:
                time_msg = f"{seconds} second{'s' if seconds != 1 else ''}"
            
            messages.error(
                request, 
                f'Too many failed login attempts. Please try again in {time_msg}.'
            )
            return render(request, 'auth_app/login.html', {
                'blocked': True,
                'remaining_time': remaining_time
            })
        
        try:
            user = User.objects.select_related().get(email=email)
            authenticated_user = authenticate(request, username=user.username, password=password)
            
            if authenticated_user:
                # Successful login - record it
                LoginAttempt.objects.create(
                    ip_address=ip_address,
                    attempted_email=email,
                    successful=True
                )
                
                # Check if 2FA is enabled
                from .models import TwoFactorAuth
                try:
                    twofa = TwoFactorAuth.objects.get(user=authenticated_user, is_enabled=True)
                    # Store user ID in session for 2FA verification
                    request.session['2fa_user_id'] = authenticated_user.id
                    return render(request, 'auth_app/verify_2fa.html', {'username': user.username})
                except TwoFactorAuth.DoesNotExist:
                    # No 2FA, proceed with normal login
                    login(request, authenticated_user)
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect('auth_app:account')
            else:
                # Failed login - record attempt
                LoginAttempt.objects.create(
                    ip_address=ip_address,
                    attempted_email=email,
                    successful=False
                )
                
                remaining = LoginAttempt.get_remaining_attempts(ip_address)
                if remaining > 0:
                    messages.error(
                        request, 
                        f'Invalid credentials. {remaining} attempt{"s" if remaining != 1 else ""} remaining.'
                    )
                else:
                    messages.error(
                        request, 
                        'Invalid credentials. Your account has been temporarily locked due to too many failed attempts.'
                    )
                return render(request, 'auth_app/login.html')
                
        except User.DoesNotExist:
            # Record failed attempt even for non-existent users
            LoginAttempt.objects.create(
                ip_address=ip_address,
                attempted_email=email,
                successful=False
            )
            
            remaining = LoginAttempt.get_remaining_attempts(ip_address)
            if remaining > 0:
                messages.error(
                    request, 
                    f'No account found with this email. {remaining} attempt{"s" if remaining != 1 else ""} remaining.'
                )
            else:
                messages.error(
                    request, 
                    'No account found with this email. Too many failed attempts - please try again later.'
                )
            return render(request, 'auth_app/login.html')
        
        except Exception as e:
            messages.error(request, 'Login failed. Please try again.')
            return render(request, 'auth_app/login.html')
    
    # GET request - show remaining attempts if any failed attempts exist
    remaining = LoginAttempt.get_remaining_attempts(ip_address)
    context = {}
    if remaining < 10:
        context['remaining_attempts'] = remaining
    
    return render(request, 'auth_app/login.html', context)


@login_required
def account_view(request):
    from .models import TwoFactorAuth
    from homepage.models import PythonCodeSession, UserProfile
    from django.utils import timezone
    from datetime import timedelta
    from django.core.cache import cache
    
    # Use cache for expensive calculations
    cache_key = f"account_data_{request.user.id}"
    account_data = cache.get(cache_key)
    
    if not account_data:
        # Get or create 2FA object for template context
        try:
            two_factor = TwoFactorAuth.objects.select_related('user').get(user=request.user)
        except TwoFactorAuth.DoesNotExist:
            two_factor = TwoFactorAuth(user=request.user, is_enabled=False)
        
        # Get user profile with optimized query
        try:
            user_profile = UserProfile.objects.select_related('user').get(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = UserProfile(user=request.user)
        
        # Calculate stats efficiently
        user_files_count = PythonCodeSession.objects.filter(user=request.user).count()
        days_since_joined = (timezone.now() - request.user.date_joined).days
        
        account_data = {
            'two_factor': two_factor,
            'user_profile': user_profile,
            'user_files_count': user_files_count,
            'days_since_joined': days_since_joined,
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, account_data, 300)
    
    return render(request, 'auth_app/account_pixel.html', {
        'user': request.user,
        'two_factor': account_data['two_factor'],
        'user_files_count': account_data['user_files_count'],
        'days_since_joined': account_data['days_since_joined'],
    })

@login_required
def update_theme(request):
    if request.method == 'POST':
        theme = request.POST.get('theme', 'default')
        from homepage.models import UserProfile
        from django.http import JsonResponse

        allowed = ['default', 'greydom', 'cloud', 'chaos', 'lebron']
        if theme not in allowed:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
                return JsonResponse({'success': False, 'error': 'Invalid theme'})
            messages.error(request, 'Invalid theme selected.')
            return redirect('auth_app:account')

        profile, _ = UserProfile.objects.select_related('user').get_or_create(user=request.user)
        if theme == 'lebron' and not profile.paidUser:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
                return JsonResponse({'success': False, 'error': 'LeBron theme is available only for premium users.'}, status=403)
            messages.error(request, 'LeBron theme requires a premium account.')
            return redirect('auth_app:account')

        profile.theme = theme
        profile.save(update_fields=['theme'])
        
        # Invalidate account cache when theme changes
        from django.core.cache import cache
        cache.delete(f"account_data_{request.user.id}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/x-www-form-urlencoded':
            return JsonResponse({'success': True, 'theme': theme})

        messages.success(request, f'Theme updated to {theme.title()}!')
    
    return redirect('auth_app:account')

def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'Goodbye {username}! You have been logged out successfully.')
    
    return redirect('auth_app:login')

@require_http_methods(["GET"])
@rate_limit(max_requests=30, window=60, key_prefix='check_email')  # 30 checks per minute
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
@rate_limit(max_requests=30, window=60, key_prefix='check_username')  # 30 checks per minute
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
    
    # Get filter parameters
    filter_type = request.GET.get('filter', 'all')  # all, paid, free, admin
    search_query = request.GET.get('search', '').strip()
    
    # Optimize query with select_related to avoid N+1 queries
    users_query = User.objects.all().select_related('profile').order_by('-date_joined')
    
    # Apply filters
    if filter_type == 'paid':
        users_query = users_query.filter(profile__paidUser=True)
    elif filter_type == 'free':
        users_query = users_query.filter(profile__paidUser=False)
    elif filter_type == 'admin':
        users_query = users_query.filter(is_superuser=True)
    
    # Apply search
    if search_query:
        users_query = users_query.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Get all users for statistics (before pagination)
    all_users = User.objects.all().select_related('profile')
    total_users = all_users.count()
    paid_count = all_users.filter(profile__paidUser=True).count()
    free_count = total_users - paid_count
    super_count = all_users.filter(is_superuser=True).count()
    
    # Recent activity - last 7 days
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(users_query, 20)  # 20 users per page
    
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    
    return render(request, 'auth_app/admin_panel.html', {
        'users': users,
        'total_users': total_users,
        'paid_users_count': paid_count,
        'free_users_count': free_count,
        'superusers_count': super_count,
        'new_users_week': new_users_week,
        'filter_type': filter_type,
        'search_query': search_query,
        'paginator': paginator,
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
        
        # Validate user_id is an integer
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return JsonResponse({
                'success': False,
                'error': 'user_id must be a valid integer'
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
            user = User.objects.select_related('profile').get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User with id {user_id} not found'
            }, status=404)
        
        # Get or create user profile
        profile, created = UserProfile.objects.select_related('user').get_or_create(user=user)
        
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


def verify_email_view(request):
    """Handle email verification with 6-digit code."""
    # Check if email is in session
    email = request.session.get('verification_email')
    if not email:
        messages.error(request, 'No verification in progress. Please sign up first.')
        return redirect('auth_app:signup')
    
    # Get verification record
    try:
        verification = EmailVerification.objects.get(email=email, verified=False)
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Verification expired or not found. Please sign up again.')
        # Clean up session
        if 'verification_email' in request.session:
            del request.session['verification_email']
        return redirect('auth_app:signup')
    
    # Check if expired
    if verification.is_expired():
        messages.error(request, 'Verification code expired. Please sign up again.')
        verification.delete()
        # Clean up session
        if 'verification_email' in request.session:
            del request.session['verification_email']
        return redirect('auth_app:signup')
    
    # Check if too many attempts
    if verification.attempts >= 5:
        messages.error(request, 'Too many failed attempts. Please sign up again.')
        verification.delete()
        # Clean up session
        if 'verification_email' in request.session:
            del request.session['verification_email']
        return redirect('auth_app:signup')
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        
        if not code:
            messages.error(request, 'Please enter the verification code.')
            return render(request, 'auth_app/verify_email.html', {'email': email})
        
        if len(code) != 6 or not code.isdigit():
            messages.error(request, 'Please enter a valid 6-digit code.')
            return render(request, 'auth_app/verify_email.html', {'email': email})
        
        # Verify code
        if verification.is_valid(code):
            try:
                # Create the user account
                user = User.objects.create_user(
                    username=verification.username,
                    email=verification.email,
                    password=verification.password  # Already hashed
                )
                user.password = verification.password  # Set the pre-hashed password
                user.save()
                
                # Mark verification as complete
                verification.mark_verified()
                
                # Clean up session
                if 'verification_email' in request.session:
                    del request.session['verification_email']
                
                # Auto-login the user
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.success(request, f'Email verified! Welcome to CLASS XII PYTHON, {user.username}!')
                return redirect('auth_app:account')
                
            except Exception as e:
                print(f"User creation error: {str(e)}")
                messages.error(request, 'Account creation failed. Please try again.')
                # Clean up on error
                if 'verification_email' in request.session:
                    del request.session['verification_email']
                return render(request, 'auth_app/verify_email.html', {'email': email})
        else:
            # Incorrect code
            verification.increment_attempts()
            remaining = 5 - verification.attempts
            
            if remaining > 0:
                messages.error(request, f'Incorrect code. {remaining} attempt{"s" if remaining != 1 else ""} remaining.')
            else:
                messages.error(request, 'Too many failed attempts. Please sign up again.')
                verification.delete()
                # Clean up session
                if 'verification_email' in request.session:
                    del request.session['verification_email']
                return redirect('auth_app:signup')
            
            return render(request, 'auth_app/verify_email.html', {'email': email})
    
    return render(request, 'auth_app/verify_email.html', {'email': email})


@require_http_methods(["POST"])
def resend_code_view(request):
    """Resend verification code to user's email."""
    email = request.session.get('verification_email')
    if not email:
        messages.error(request, 'No verification in progress.')
        return redirect('auth_app:signup')
    
    try:
        verification = EmailVerification.objects.get(email=email, verified=False)
        
        # Generate new code and extend expiration
        verification.verification_code = EmailVerification.generate_code()
        verification.expires_at = timezone.now() + timedelta(minutes=10)
        verification.attempts = 0  # Reset attempts
        verification.save()
        
        # Send new code
        if send_verification_code_resend(email, verification.username, verification.verification_code):
            messages.success(request, 'New verification code sent! Check your email.')
        else:
            messages.error(request, 'Failed to send email. Please try again.')
            
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Verification not found. Please sign up again.')
        # Clean up session
        if 'verification_email' in request.session:
            del request.session['verification_email']
        return redirect('auth_app:signup')
    
    return redirect('auth_app:verify_email')

@login_required
@require_http_methods(["POST"])
def request_password_change(request):
    """Verify current password and send verification code for password change."""
    try:
        data = json.loads(request.body)
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        if not all([current_password, new_password, confirm_password]):
            return JsonResponse({'success': False, 'error': 'All fields are required.'}, status=400)
        
        if not request.user.check_password(current_password):
            return JsonResponse({'success': False, 'error': 'Current password is incorrect.'}, status=400)
        
        if len(new_password) < 6:
            return JsonResponse({'success': False, 'error': 'New password must be at least 6 characters long.'}, status=400)
        
        if new_password != confirm_password:
            return JsonResponse({'success': False, 'error': 'New passwords do not match.'}, status=400)
        
        if check_password(new_password, request.user.password):
            return JsonResponse({'success': False, 'error': 'New password must be different from current password.'}, status=400)
        
        PasswordChangeRequest.objects.filter(user=request.user, verified=False).delete()
        
        change_request = PasswordChangeRequest.objects.create(user=request.user, new_password=make_password(new_password))
        
        if send_password_change_code(request.user.email, request.user.username, change_request.verification_code):
            return JsonResponse({'success': True, 'message': f'Verification code sent to {request.user.email}. Please check your inbox.', 'request_id': change_request.id})
        else:
            change_request.delete()
            return JsonResponse({'success': False, 'error': 'Failed to send verification email. Please try again.'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)
    except Exception as e:
        print(f"Password change request error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to process request. Please try again.'}, status=500)


@login_required
@require_http_methods(["POST"])
def verify_password_change(request):
    """Verify the code and update the user's password."""
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        
        if not code:
            return JsonResponse({'success': False, 'error': 'Verification code is required.'}, status=400)
        
        if len(code) != 6 or not code.isdigit():
            return JsonResponse({'success': False, 'error': 'Please enter a valid 6-digit code.'}, status=400)
        
        try:
            change_request = PasswordChangeRequest.objects.filter(user=request.user, verified=False).latest('created_at')
        except PasswordChangeRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No password change request found. Please start over.'}, status=404)
        
        # Debug logging
        print(f"[DEBUG] User entered code: '{code}' (type: {type(code)})")
        print(f"[DEBUG] Stored code: '{change_request.verification_code}' (type: {type(change_request.verification_code)})")
        print(f"[DEBUG] Codes match: {change_request.verification_code == code}")
        print(f"[DEBUG] Is expired: {change_request.is_expired()}")
        print(f"[DEBUG] Is verified: {change_request.verified}")
        print(f"[DEBUG] Attempts: {change_request.attempts}")
        
        if change_request.is_expired():
            change_request.delete()
            return JsonResponse({'success': False, 'error': 'Verification code expired. Please request a new one.'}, status=400)
        
        if change_request.attempts >= 5:
            change_request.delete()
            return JsonResponse({'success': False, 'error': 'Too many failed attempts. Please start over.'}, status=400)
        
        # Direct comparison instead of using is_valid method for debugging
        if (change_request.verification_code == code and 
            not change_request.is_expired() and 
            not change_request.verified and 
            change_request.attempts < 5):
            try:
                request.user.password = change_request.new_password
                request.user.save(update_fields=['password'])
                change_request.mark_verified()
                print(f"[SUCCESS] Password changed for user {request.user.username}")
                return JsonResponse({'success': True, 'message': 'Password changed successfully!'})
            except Exception as e:
                print(f"Password update error: {str(e)}")
                return JsonResponse({'success': False, 'error': 'Failed to update password. Please try again.'}, status=500)
        else:
            change_request.increment_attempts()
            remaining = 5 - change_request.attempts
            print(f"[ERROR] Code validation failed. Remaining attempts: {remaining}")
            if remaining > 0:
                return JsonResponse({'success': False, 'error': f'Incorrect code. {remaining} attempt{"s" if remaining != 1 else ""} remaining.'}, status=400)
            else:
                change_request.delete()
                return JsonResponse({'success': False, 'error': 'Too many failed attempts. Please start over.'}, status=400)
                
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)
    except Exception as e:
        print(f"Password verification error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to verify code. Please try again.'}, status=500)


@login_required
@require_http_methods(["POST"])
def resend_password_change_code(request):
    """Resend verification code for password change."""
    try:
        try:
            change_request = PasswordChangeRequest.objects.filter(user=request.user, verified=False).latest('created_at')
        except PasswordChangeRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No password change request found. Please start over.'}, status=404)
        
        change_request.verification_code = PasswordChangeRequest.generate_code()
        change_request.expires_at = timezone.now() + timedelta(minutes=10)
        change_request.attempts = 0
        change_request.save()
        
        if send_password_change_code(request.user.email, request.user.username, change_request.verification_code):
            return JsonResponse({'success': True, 'message': 'New verification code sent! Check your email.'})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to send email. Please try again.'}, status=500)
            
    except Exception as e:
        print(f"Resend password change code error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to resend code. Please try again.'}, status=500)


# Two-Factor Authentication Views
@login_required
@require_http_methods(["POST"])
def enable_2fa(request):
    """Enable two-factor authentication for the user."""
    try:
        from .models import TwoFactorAuth
        import io
        import base64
        import qrcode
        
        # Check if 2FA already enabled
        twofa, created = TwoFactorAuth.objects.get_or_create(user=request.user)
        
        if twofa.is_enabled and not created:
            return JsonResponse({'success': False, 'error': '2FA is already enabled.'}, status=400)
        
        # Generate new secret if not exists or regenerate for setup
        if not twofa.secret_key or not twofa.is_enabled:
            twofa.generate_secret()
        
        # Generate QR code
        provisioning_uri = twofa.get_provisioning_uri(request.user.username)
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        qr_code_html = f'<img src="data:image/png;base64,{img_str}" alt="QR Code" style="max-width: 100%;">'
        
        return JsonResponse({
            'success': True,
            'qr_code': qr_code_html,
            'secret': twofa.secret_key
        })
        
    except Exception as e:
        print(f"Enable 2FA error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to enable 2FA. Please try again.'}, status=500)


@login_required
@require_http_methods(["POST"])
def verify_2fa(request):
    """Verify TOTP code and complete 2FA setup."""
    try:
        from .models import TwoFactorAuth
        
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        
        if not code or len(code) != 6:
            return JsonResponse({'success': False, 'error': 'Please enter a 6-digit code.'}, status=400)
        
        try:
            twofa = TwoFactorAuth.objects.get(user=request.user)
        except TwoFactorAuth.DoesNotExist:
            return JsonResponse({'success': False, 'error': '2FA not initialized. Please start setup again.'}, status=404)
        
        if twofa.verify_totp(code):
            # Enable 2FA and generate backup codes
            twofa.is_enabled = True
            backup_codes = twofa.generate_backup_codes()
            twofa.save()
            
            return JsonResponse({
                'success': True,
                'message': '2FA enabled successfully!',
                'backup_codes': backup_codes
            })
        else:
            return JsonResponse({'success': False, 'error': 'Invalid code. Please try again.'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)
    except Exception as e:
        print(f"Verify 2FA error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to verify 2FA. Please try again.'}, status=500)


@login_required
@require_http_methods(["POST"])
def disable_2fa(request):
    """Disable two-factor authentication."""
    try:
        from .models import TwoFactorAuth
        
        try:
            twofa = TwoFactorAuth.objects.get(user=request.user)
            twofa.is_enabled = False
            twofa.save()
            
            return JsonResponse({'success': True, 'message': '2FA disabled successfully.'})
        except TwoFactorAuth.DoesNotExist:
            return JsonResponse({'success': False, 'error': '2FA is not enabled.'}, status=404)
            
    except Exception as e:
        print(f"Disable 2FA error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to disable 2FA. Please try again.'}, status=500)


@require_http_methods(["POST"])
def verify_2fa_login(request):
    """Verify 2FA code during login."""
    try:
        from .models import TwoFactorAuth
        
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        user_id = request.session.get('2fa_user_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'Session expired. Please login again.'}, status=400)
        
        if not code:
            return JsonResponse({'success': False, 'error': 'Please enter a code.'}, status=400)
        
        try:
            user = User.objects.get(id=int(user_id))
            twofa = TwoFactorAuth.objects.get(user=user, is_enabled=True)
        except (User.DoesNotExist, TwoFactorAuth.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid session. Please login again.'}, status=404)
        
        # Verify TOTP or backup code
        if twofa.verify_totp(code) or twofa.verify_backup_code(code):
            # Complete login
            login(request, user)
            del request.session['2fa_user_id']
            
            return JsonResponse({
                'success': True,
                'message': 'Login successful!',
                'redirect_url': '/python-environment/'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Invalid code. Please try again.'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data.'}, status=400)
    except Exception as e:
        print(f"Verify 2FA login error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to verify code. Please try again.'}, status=500)
