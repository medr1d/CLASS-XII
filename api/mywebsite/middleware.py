"""
Custom middleware for performance optimizations
"""
from django.utils.cache import patch_cache_control
from django.http import HttpResponse
import gzip
import io


class StaticFileCacheMiddleware:
    """
    Add cache headers to static files and enable better caching
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add cache headers for static files
        if request.path.startswith('/static/'):
            # Cache static files for 1 year
            patch_cache_control(response, max_age=31536000, public=True)
            response['Vary'] = 'Accept-Encoding'
        
        # Add cache headers for favicon
        elif request.path.endswith(('favicon.ico', 'favicon.png')):
            patch_cache_control(response, max_age=86400, public=True)
        
        return response


class OptimizedResponseMiddleware:
    """
    Optimize responses with better compression and headers
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        if not response.get('X-Content-Type-Options'):
            response['X-Content-Type-Options'] = 'nosniff'
        if not response.get('X-Frame-Options'):
            response['X-Frame-Options'] = 'DENY'
        if not response.get('X-XSS-Protection'):
            response['X-XSS-Protection'] = '1; mode=block'
        
        # Add performance headers
        if request.path.startswith('/'):
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response


class HTMLMinifyMiddleware:
    """
    Minify HTML responses for better performance
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only minify HTML responses
        if (response.get('Content-Type', '').startswith('text/html') and 
            hasattr(response, 'content') and 
            response.status_code == 200):
            
            content = response.content.decode('utf-8')
            
            # Simple HTML minification
            import re
            
            # Remove comments (but keep IE conditional comments)
            content = re.sub(r'<!--(?!\[if|\[endif).*?-->', '', content, flags=re.DOTALL)
            
            # Remove extra whitespace between tags
            content = re.sub(r'>\s+<', '><', content)
            
            # Remove leading/trailing whitespace on lines
            content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
            
            response.content = content.encode('utf-8')
            response['Content-Length'] = str(len(response.content))
        
        return response