from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class AuthAppTestCase(TestCase):
    """
    Test cases for the authentication app using Django's built-in User model
    """
    
    def setUp(self):
        """Set up test client and clean database"""
        self.client = Client()
        
        # Clean up any existing test users
        User.objects.all().delete()
    
    def tearDown(self):
        """Clean up after tests"""
        User.objects.all().delete()
    
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