from google.auth.transport import requests
from google.oauth2 import id_token
from django.conf import settings
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

def verify_google_token(token):
    """
    Verify Google OAuth token and return user info
    
    Args:
        token (str): Google OAuth token from frontend
        
    Returns:
        dict: User information from Google or None if invalid
    """
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        # Token is valid, extract user information
        user_data = {
            'google_id': idinfo['sub'],
            'email': idinfo['email'],
            'first_name': idinfo.get('given_name', ''),
            'last_name': idinfo.get('family_name', ''),
            'full_name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'email_verified': idinfo.get('email_verified', False)
        }
        
        logger.info(f"Google OAuth successful for email: {user_data['email']}")
        return user_data
        
    except ValueError as e:
        # Invalid token
        logger.error(f"Google OAuth token verification failed: {str(e)}")
        return None
    except Exception as e:
        # Other errors
        logger.error(f"Google OAuth error: {str(e)}")
        return None

def generate_username_from_email(email):
    """
    Generate a unique username from email address
    
    Args:
        email (str): Email address
        
    Returns:
        str: Generated username
    """
    # Get base username from email (part before @)
    base_username = email.split('@')[0]
    
    # Remove any dots or special characters
    base_username = base_username.replace('.', '').replace('-', '').replace('_', '')[:30]
    
    # Check if username exists, if so, add numbers
    username = base_username
    counter = 1
    
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
        
        # Prevent infinite loop
        if counter > 999:
            username = f"{base_username}{counter}_{hash(email) % 1000}"
            break
    
    return username

def generate_secure_password():
    """
    Generate a secure random password for OAuth users
    
    Returns:
        str: Random secure password
    """
    import secrets
    import string
    
    # Generate a 16-character password with letters, digits, and symbols
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(16))
    
    return password