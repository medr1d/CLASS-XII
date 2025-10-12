from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import LoginAttempt
from django.utils import timezone


class AuthAppTestCase(TestCase):
    """
    Test cases for the authentication app using Django's built-in User model
    """
    
    def setUp(self):
        """Set up test client and clean database"""
        self.client = Client()
        
        # Clean up any existing test users
        User.objects.all().delete()
        # Clean up any existing login attempts
        LoginAttempt.objects.all().delete()
    
    def tearDown(self):
        """Clean up after tests"""
        User.objects.all().delete()
        LoginAttempt.objects.all().delete()
    
    def test_user_creation(self):
        """Test user creation with valid data"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepassword123'
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('securepassword123'))
    
    def test_user_authentication(self):
        """Test user authentication"""
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepassword123'
        )
        
        # Test authentication
        self.assertTrue(user.check_password('securepassword123'))
        
        # Test authentication with wrong password
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_signup_view(self):
        """Test signup view"""
        response = self.client.get(reverse('auth_app:signup'))
        self.assertEqual(response.status_code, 200)
        
        # Test POST request
        response = self.client.post(reverse('auth_app:signup'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123',
            'confirm_password': 'securepassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful signup
        
        # Check if user was created
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_login_view(self):
        """Test login view"""
        # Create a test user first
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepassword123'
        )
        
        response = self.client.get(reverse('auth_app:login'))
        self.assertEqual(response.status_code, 200)
        
        # Test login POST request
        response = self.client.post(reverse('auth_app:login'), {
            'email': 'test@example.com',
            'password': 'securepassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful login
    
    def test_account_view_requires_login(self):
        """Test that account view requires authentication"""
        response = self.client.get(reverse('auth_app:account'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_logout_view(self):
        """Test logout functionality"""
        # Create and login a user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepassword123'
        )
        self.client.login(username='testuser', password='securepassword123')
        
        # Test logout
        response = self.client.get(reverse('auth_app:logout'))
        self.assertEqual(response.status_code, 302)  # Redirect after logout
        
        # Test that user is logged out
        response = self.client.get(reverse('auth_app:account'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login
    
    def test_login_rate_limiting(self):
        """Test that login rate limiting blocks excessive failed attempts"""
        # Create a test user
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepassword123'
        )
        
        # Make 10 failed login attempts
        for i in range(10):
            response = self.client.post(reverse('auth_app:login'), {
                'email': 'test@example.com',
                'password': 'wrongpassword',
            }, REMOTE_ADDR='127.0.0.1')
        
        # The 11th attempt should be blocked
        response = self.client.post(reverse('auth_app:login'), {
            'email': 'test@example.com',
            'password': 'securepassword123',  # Even with correct password
        }, REMOTE_ADDR='127.0.0.1')
        
        # Should still show login page with error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many failed login attempts')
    
    def test_login_rate_limiting_with_nonexistent_email(self):
        """Test that rate limiting works for non-existent email addresses"""
        # Make 10 failed login attempts with non-existent email
        for i in range(10):
            response = self.client.post(reverse('auth_app:login'), {
                'email': 'nonexistent@example.com',
                'password': 'somepassword',
            }, REMOTE_ADDR='192.168.1.1')
        
        # The 11th attempt should be blocked
        response = self.client.post(reverse('auth_app:login'), {
            'email': 'nonexistent@example.com',
            'password': 'somepassword',
        }, REMOTE_ADDR='192.168.1.1')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many failed login attempts')
    
    def test_login_attempt_model(self):
        """Test LoginAttempt model methods"""
        # Test recording attempts
        ip = '10.0.0.1'
        LoginAttempt.record_attempt(ip, 'test@example.com')
        self.assertEqual(LoginAttempt.objects.filter(ip_address=ip).count(), 1)
        
        # Test is_blocked after insufficient attempts
        self.assertFalse(LoginAttempt.is_blocked(ip))
        
        # Add more attempts to trigger blocking
        for i in range(9):
            LoginAttempt.record_attempt(ip, 'test@example.com')
        
        # Should be blocked after 10 attempts
        self.assertTrue(LoginAttempt.is_blocked(ip))
        
        # Test that a different IP is not blocked
        self.assertFalse(LoginAttempt.is_blocked('10.0.0.2'))