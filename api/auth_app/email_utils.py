"""
Email utility functions for sending verification codes.
"""
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_verification_email(email, username, code):
    """
    Send verification code email to user.
    
    Args:
        email: Recipient email address
        username: Username of the user
        code: 6-digit verification code
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = 'Verify Your Email - CLASS XII PYTHON'
    
    message = f"""
Hello {username},

Thank you for signing up for CLASS XII PYTHON ASSEMBLY!

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
CLASS XII PYTHON Team
"""
    
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background-color: #000;
            color: #0f0;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #0a0a0a;
            border: 2px solid #0f0;
            border-radius: 10px;
            padding: 40px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #0f0;
            font-size: 24px;
            letter-spacing: 3px;
            margin: 0;
        }}
        .code-box {{
            background: #000;
            border: 3px solid #0f0;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }}
        .code {{
            font-size: 42px;
            font-weight: bold;
            letter-spacing: 10px;
            color: #0f0;
            text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }}
        .message {{
            line-height: 1.8;
            color: #0f0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #0f0;
            text-align: center;
            color: #0a0;
            font-size: 12px;
        }}
        .warning {{
            color: #ff0;
            margin-top: 20px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>→ CLASS XII PYTHON ASSEMBLY ←</h1>
        </div>
        
        <div class="message">
            <p>Hello <strong>{username}</strong>,</p>
            <p>Thank you for signing up! Please verify your email address to complete your registration.</p>
        </div>
        
        <div class="code-box">
            <div style="color: #0a0; margin-bottom: 10px; font-size: 14px;">YOUR VERIFICATION CODE</div>
            <div class="code">{code}</div>
            <div style="color: #0a0; margin-top: 10px; font-size: 12px;">Valid for 10 minutes</div>
        </div>
        
        <div class="warning">
            ⚠️ If you didn't request this code, please ignore this email.
        </div>
        
        <div class="footer">
            <p>This is an automated message. Please do not reply.</p>
            <p>© 2025 CLASS XII PYTHON ASSEMBLY</p>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        return False


def send_verification_code_resend(email, username, code):
    """
    Send resent verification code email.
    
    Args:
        email: Recipient email address
        username: Username of the user
        code: 6-digit verification code
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = 'New Verification Code - CLASS XII PYTHON'
    
    message = f"""
Hello {username},

Here is your new verification code: {code}

This code will expire in 10 minutes.

Best regards,
CLASS XII PYTHON Team
"""
    
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background-color: #000;
            color: #0f0;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #0a0a0a;
            border: 2px solid #0f0;
            border-radius: 10px;
            padding: 40px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #0f0;
            font-size: 24px;
            letter-spacing: 3px;
            margin: 0;
        }}
        .code-box {{
            background: #000;
            border: 3px solid #0f0;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }}
        .code {{
            font-size: 42px;
            font-weight: bold;
            letter-spacing: 10px;
            color: #0f0;
            text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }}
        .message {{
            line-height: 1.8;
            color: #0f0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #0f0;
            text-align: center;
            color: #0a0;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>→ NEW VERIFICATION CODE ←</h1>
        </div>
        
        <div class="message">
            <p>Hello <strong>{username}</strong>,</p>
            <p>You requested a new verification code. Here it is:</p>
        </div>
        
        <div class="code-box">
            <div style="color: #0a0; margin-bottom: 10px; font-size: 14px;">YOUR NEW VERIFICATION CODE</div>
            <div class="code">{code}</div>
            <div style="color: #0a0; margin-top: 10px; font-size: 12px;">Valid for 10 minutes</div>
        </div>
        
        <div class="footer">
            <p>This is an automated message. Please do not reply.</p>
            <p>© 2025 CLASS XII PYTHON ASSEMBLY</p>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification code resent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to resend verification code to {email}: {str(e)}")
        return False
