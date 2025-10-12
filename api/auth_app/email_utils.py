"""
Email utility functions for sending verification codes.
"""
from django.core.mail import send_mail
from django.conf import settings
import logging
import smtplib

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background-color: #ffffff;
            color: #000000;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
            border: 2px solid #000000;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #000000;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #000000;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
            margin: 0;
        }}
        .code-box {{
            background: #f5f5f5;
            border: 2px solid #000000;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
        }}
        .code {{
            font-size: 42px;
            font-weight: bold;
            letter-spacing: 10px;
            color: #000000;
            font-family: 'Courier New', monospace;
        }}
        .message {{
            line-height: 1.8;
            color: #000000;
            font-size: 16px;
        }}
        .message p {{
            margin: 15px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #cccccc;
            text-align: center;
            color: #666666;
            font-size: 12px;
        }}
        .warning {{
            color: #666666;
            margin-top: 20px;
            font-size: 14px;
            text-align: center;
        }}
        .label {{
            color: #666666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        .expiry {{
            color: #666666;
            margin-top: 10px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CLASS XII PYTHON ASSEMBLY</h1>
        </div>
        
        <div class="message">
            <p>Hello <strong>{username}</strong>,</p>
            <p>Thank you for signing up! Please verify your email address to complete your registration.</p>
        </div>
        
        <div class="code-box">
            <div class="label">YOUR VERIFICATION CODE</div>
            <div class="code">{code}</div>
            <div class="expiry">Valid for 10 minutes</div>
        </div>
        
        <div class="warning">
            <p>If you didn't request this code, please ignore this email.</p>
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
        # Debug email configuration
        logger.info(f"Email configuration - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}, TLS: {settings.EMAIL_USE_TLS}")
        logger.info(f"From email: {settings.EMAIL_HOST_USER}")
        logger.info(f"Password set: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
        logger.info(f"Password length: {len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 0}")
        
        # Test SMTP connection manually for better debugging
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        logger.info("Attempting manual SMTP connection...")
        
        # Use SSL connection if EMAIL_USE_SSL is True, otherwise use regular SMTP
        if getattr(settings, 'EMAIL_USE_SSL', False):
            logger.info("Using SSL connection...")
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
        else:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            
        server.set_debuglevel(1)  # Enable SMTP debugging
        
        if settings.EMAIL_USE_TLS and not getattr(settings, 'EMAIL_USE_SSL', False):
            logger.info("Starting TLS...")
            server.starttls()
            
        logger.info(f"Attempting login with user: {settings.EMAIL_HOST_USER}")
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        
        logger.info("SMTP login successful! Sending email via Django send_mail...")
        server.quit()
        
        # If manual connection works, try Django send_mail
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
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error: {str(e)}")
        logger.error("This usually means wrong username/password or app-specific password needed")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        logger.error(f"Email settings - Host: {settings.EMAIL_HOST}, User: {settings.EMAIL_HOST_USER}")
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background-color: #ffffff;
            color: #000000;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
            border: 2px solid #000000;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #000000;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #000000;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
            margin: 0;
        }}
        .code-box {{
            background: #f5f5f5;
            border: 2px solid #000000;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
        }}
        .code {{
            font-size: 42px;
            font-weight: bold;
            letter-spacing: 10px;
            color: #000000;
            font-family: 'Courier New', monospace;
        }}
        .message {{
            line-height: 1.8;
            color: #000000;
            font-size: 16px;
        }}
        .message p {{
            margin: 15px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #cccccc;
            text-align: center;
            color: #666666;
            font-size: 12px;
        }}
        .label {{
            color: #666666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        .expiry {{
            color: #666666;
            margin-top: 10px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NEW VERIFICATION CODE</h1>
        </div>
        
        <div class="message">
            <p>Hello <strong>{username}</strong>,</p>
            <p>You requested a new verification code. Here it is:</p>
        </div>
        
        <div class="code-box">
            <div class="label">YOUR NEW VERIFICATION CODE</div>
            <div class="code">{code}</div>
            <div class="expiry">Valid for 10 minutes</div>
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


def send_password_change_code(email, username, code):
    """
    Send password change verification code email to user.
    
    Args:
        email: Recipient email address
        username: Username of the user
        code: 6-digit verification code
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = 'Password Change Verification - CLASS XII PYTHON'
    
    message = f"""
Hello {username},

You have requested to change your password.

Your verification code is: {code}

This code will expire in 10 minutes.

If you did not request this change, please ignore this email and your password will remain unchanged.

Best regards,
CLASS XII PYTHON Team
"""
    
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background-color: #ffffff;
            color: #000000;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
            border: 2px solid #000000;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #000000;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #000000;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
            margin: 0;
        }}
        .code-box {{
            background: #f5f5f5;
            border: 2px solid #000000;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
        }}
        .code {{
            font-size: 42px;
            font-weight: bold;
            letter-spacing: 10px;
            color: #000000;
            font-family: 'Courier New', monospace;
        }}
        .message {{
            line-height: 1.8;
            color: #000000;
            font-size: 16px;
        }}
        .message p {{
            margin: 15px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #cccccc;
            text-align: center;
            color: #666666;
            font-size: 12px;
        }}
        .warning {{
            color: #666666;
            margin-top: 20px;
            font-size: 14px;
            text-align: center;
        }}
        .label {{
            color: #666666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        .expiry {{
            color: #666666;
            margin-top: 10px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>PASSWORD CHANGE REQUEST</h1>
        </div>
        
        <div class="message">
            <p>Hello <strong>{username}</strong>,</p>
            <p>You have requested to change your password. Please use the verification code below to confirm this change.</p>
        </div>
        
        <div class="code-box">
            <div class="label">VERIFICATION CODE</div>
            <div class="code">{code}</div>
            <div class="expiry">Valid for 10 minutes</div>
        </div>
        
        <div class="warning">
            <p>If you didn't request this password change, please ignore this email and your password will remain unchanged.</p>
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
        # Debug email configuration
        logger.info(f"Sending password change code to {email}")
        logger.info(f"Email configuration - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}")
        
        # Manual SMTP connection for debugging
        if settings.EMAIL_USE_SSL:
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
        else:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            if settings.EMAIL_USE_TLS:
                server.starttls()
            
        logger.info(f"Attempting login with user: {settings.EMAIL_HOST_USER}")
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        
        logger.info("SMTP login successful! Sending password change email...")
        server.quit()
        
        # If manual connection works, try Django send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password change code sent successfully to {email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to send password change code to {email}: {str(e)}")
        return False
