import secrets
import hmac
import hashlib
import time
from typing import Optional
from flask import session, current_app

class CSRFTokenGenerator:
    def __init__(self, secret_key: str, token_length: int = 32):
        self.secret_key = secret_key
        self.token_length = token_length
    
    def generate_csrf(self, user_id: Optional[str] = None) -> str:
        """Generate a CSRF token"""
        timestamp = str(int(time.time()))
        random_bytes = secrets.token_urlsafe(self.token_length)
        
        # Create payload
        payload = f"{user_id or 'anonymous'}:{timestamp}:{random_bytes}"
        
        # Create signature
        signature = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{payload}:{signature}"
        
        # Store in session for validation
        session['csrf_token'] = token
        session['csrf_timestamp'] = timestamp
        
        return token
    
    def validate_csrf(self, token: str, user_id: Optional[str] = None, 
                     max_age: int = 3600) -> bool:
        """Validate CSRF token"""
        if not token or ':' not in token:
            return False
        
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return False
            
            token_user_id, timestamp, random_part, signature = parts
            payload = f"{token_user_id}:{timestamp}:{random_part}"
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not secrets.compare_digest(signature, expected_signature):
                return False
            
            # Check user match
            expected_user = user_id or 'anonymous'
            if token_user_id != expected_user:
                return False
            
            # Check timestamp
            if int(time.time()) - int(timestamp) > max_age:
                return False
            
            # Check session token
            if session.get('csrf_token') != token:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False

# Initialize with your app
def get_csrf_generator():
    return CSRFTokenGenerator(current_app.config['SECRET_KEY'])

def generate_csrf(user_id: Optional[str] = None) -> str:
    """Wrapper function"""
    return get_csrf_generator().generate_csrf(user_id)

def validate_csrf(token: str, user_id: Optional[str] = None) -> bool:
    """Wrapper function"""
    return get_csrf_generator().validate_csrf(token, user_id)