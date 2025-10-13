"""
Rate limiting decorators for Django views.
"""
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
import hashlib


def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def rate_limit(max_requests=10, window=60, key_prefix='rate_limit'):
    """
    Rate limiting decorator for Django views.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        window: Time window in seconds
        key_prefix: Prefix for cache key
    
    Example:
        @rate_limit(max_requests=5, window=60)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get unique identifier (IP + user if authenticated)
            ip = get_client_ip(request)
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            
            # Create cache key
            cache_key = f"{key_prefix}:{view_func.__name__}:{ip}:{user_id}"
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Get current request count
            request_count = cache.get(cache_key_hash, 0)
            
            if request_count >= max_requests:
                # Rate limit exceeded
                return JsonResponse({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': window
                }, status=429)
            
            # Increment request count
            cache.set(cache_key_hash, request_count + 1, window)
            
            # Call the actual view
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def rate_limit_per_ip(max_requests=100, window=3600):
    """
    Simple rate limiting by IP address only.
    
    Args:
        max_requests: Maximum requests per IP
        window: Time window in seconds (default: 1 hour)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            ip = get_client_ip(request)
            cache_key = f"rate_limit_ip:{view_func.__name__}:{ip}"
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            request_count = cache.get(cache_key_hash, 0)
            
            if request_count >= max_requests:
                return JsonResponse({
                    'error': f'Too many requests from your IP. Limit: {max_requests} per {window//60} minutes.',
                    'retry_after': window
                }, status=429)
            
            cache.set(cache_key_hash, request_count + 1, window)
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def rate_limit_per_user(max_requests=50, window=3600):
    """
    Rate limiting per authenticated user.
    
    Args:
        max_requests: Maximum requests per user
        window: Time window in seconds (default: 1 hour)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            user_id = request.user.id
            cache_key = f"rate_limit_user:{view_func.__name__}:{user_id}"
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            request_count = cache.get(cache_key_hash, 0)
            
            if request_count >= max_requests:
                return JsonResponse({
                    'error': f'Rate limit exceeded. Limit: {max_requests} requests per {window//60} minutes.',
                    'retry_after': window
                }, status=429)
            
            cache.set(cache_key_hash, request_count + 1, window)
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator
