from django.http import HttpResponse
from django.core.management import call_command
from django.conf import settings
import io
import sys

def run_migrations(request):
    if not hasattr(settings, 'DATABASES'):
        return HttpResponse("❌ Database not configured", content_type="text/plain")
    
    try:
        output = io.StringIO()
        call_command('migrate', stdout=output, stderr=output)
        result = output.getvalue()
        
        response_text = f"""🎉 Django Migrations Completed Successfully!

📋 Migration Output:
{result}

✅ Database Tables Created:
- auth_user (for user accounts)
- auth_group (for permissions) 
- django_session (for login sessions)
- django_content_type (for Django admin)
- And other Django system tables

🚀 Your authentication system is now ready!

Try creating an account at:
- /auth/signup/
- /auth/login/
        """
        
        return HttpResponse(response_text, content_type="text/plain")
        
    except Exception as e:
        error_text = f"""❌ Migration Error:
{str(e)}

🔍 Debug Info:
- Database URL configured: {'Yes' if settings.DATABASES.get('default', {}).get('HOST') else 'No'}
- Environment: {'Production' if not settings.DEBUG else 'Development'}

💡 Make sure your Neon database environment variables are set in Vercel.
        """
        return HttpResponse(error_text, content_type="text/plain")