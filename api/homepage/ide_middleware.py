"""
Middleware for IDE access control
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
from homepage.models import UserProfile


class IDEAccessMiddleware:
    """
    Middleware to check if user has access to IDE features
    Only paid users can access the cloud IDE
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # IDE URLs that require paid access
        self.ide_paths = [
            '/ide/',
            '/api/ide/',
        ]
    
    def __call__(self, request):
        # Check if the request is for an IDE path
        is_ide_path = any(request.path.startswith(path) for path in self.ide_paths)
        
        if is_ide_path:
            # Must be authenticated
            if not request.user.is_authenticated:
                if request.path.startswith('/api/'):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Authentication required'
                    }, status=401)
                return redirect(f"{reverse('login')}?next={request.path}")
            
            # Check if user is paid
            try:
                profile = UserProfile.objects.get(user=request.user)
                if not profile.paidUser:
                    if request.path.startswith('/api/'):
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Premium subscription required to access cloud IDE'
                        }, status=403)
                    # Redirect to subscription page or show upgrade message
                    return redirect(reverse('home') + '?upgrade=true')
            except UserProfile.DoesNotExist:
                # Create profile and deny access
                UserProfile.objects.create(user=request.user, paidUser=False)
                if request.path.startswith('/api/'):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Premium subscription required'
                    }, status=403)
                return redirect(reverse('home') + '?upgrade=true')
        
        response = self.get_response(request)
        return response
