"""
Job Actions Security Module

Specialized security measures for job actions functionality including:
- Rate limiting for different action types
- Input validation and sanitization
- CSRF protection
- Audit logging
- Abuse detection and prevention
"""

import time
import json
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, List
from flask import request, g, current_app, jsonify, session
from ipaddress import ip_address

from src.firewall.rate_limiting import limiter, get_user_aware_key
from src.firewall.auditing import log_security_event
from src.cache.job_actions_cache import job_actions_cache


class JobActionsSecurityManager:
    """Security manager for job actions functionality"""

    def __init__(self):
        # Rate limiting configurations for different actions
        self.rate_limits = {
            'like': {
                'limit': '10 per minute',
                'burst_limit': '50 per hour',
                'description': 'Job like/unlike actions'
            },
            'save': {
                'limit': '20 per minute',
                'burst_limit': '100 per hour',
                'description': 'Job save/unsave actions'
            },
            'share': {
                'limit': '5 per minute',
                'burst_limit': '25 per hour',
                'description': 'Job sharing actions'
            },
            'view_state': {
                'limit': '60 per minute',
                'burst_limit': '300 per hour',
                'description': 'Job actions state retrieval'
            },
            'company_profile': {
                'limit': '30 per minute',
                'burst_limit': '150 per hour',
                'description': 'Company profile access'
            }
        }

        # Suspicious activity thresholds
        self.abuse_thresholds = {
            'rapid_likes': 20,  # Likes in 1 minute
            'rapid_saves': 30,  # Saves in 1 minute
            'rapid_shares': 10,  # Shares in 1 minute
            'daily_actions': 1000,  # Total actions per day
        }

    def get_client_identifier(self) -> str:
        """Get a unique identifier for the client"""
        if hasattr(g, 'user') and g.user:
            return f"user:{g.user.uid}"

        # Fallback to IP address for anonymous users
        return f"ip:{request.remote_addr}"

    def validate_job_id(self, job_id: str) -> bool:
        """Validate job ID format and existence"""
        if not job_id or not isinstance(job_id, str):
            return False

        # Basic UUID format validation
        if len(job_id) != 36 or job_id.count('-') != 4:
            return False

        # Additional validation could include database check
        return True

    def validate_user_id(self, user_id: str) -> bool:
        """Validate user ID format"""
        if not user_id or not isinstance(user_id, str):
            return False

        # Basic UUID format validation
        if len(user_id) != 36 or user_id.count('-') != 4:
            return False

        return True

    def validate_share_method(self, method: str) -> bool:
        """Validate share method"""
        valid_methods = ['email', 'linkedin', 'twitter', 'facebook', 'whatsapp', 'copy_link']
        return method in valid_methods

    def check_csrf_token(self) -> bool:
        """Check CSRF token for state-changing operations"""
        if request.method in ['POST', 'PUT', 'DELETE']:
            # Check for CSRF token in headers or form data
            csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            session_token = session.get('csrf_token')

            if not csrf_token or not session_token:
                return False

            return csrf_token == session_token

        return True  # GET requests don't need CSRF protection

    def detect_suspicious_activity(self, user_id: str, action_type: str) -> Dict[str, Any]:
        """Detect suspicious activity patterns"""
        client_id = self.get_client_identifier()
        current_time = int(time.time())

        # Check recent activity from cache
        activity_key = f"activity:{client_id}:{action_type}"
        recent_activity = job_actions_cache.cache.get(activity_key) or []

        # Clean old entries (older than 1 hour)
        recent_activity = [
            timestamp for timestamp in recent_activity
            if current_time - timestamp < 3600
        ]

        # Add current action
        recent_activity.append(current_time)

        # Store updated activity
        job_actions_cache.cache.set(activity_key, recent_activity, 3600)

        # Analyze patterns
        suspicious_indicators = []

        # Check for rapid actions in last minute
        last_minute = [t for t in recent_activity if current_time - t < 60]
        threshold_key = f'rapid_{action_type}s'

        if len(last_minute) > self.abuse_thresholds.get(threshold_key, 100):
            suspicious_indicators.append(f"Rapid {action_type} actions: {len(last_minute)} in 1 minute")

        # Check daily total
        daily_actions = len([t for t in recent_activity if current_time - t < 86400])
        if daily_actions > self.abuse_thresholds['daily_actions']:
            suspicious_indicators.append(f"High daily activity: {daily_actions} actions")

        return {
            'is_suspicious': len(suspicious_indicators) > 0,
            'indicators': suspicious_indicators,
            'recent_count': len(recent_activity),
            'last_minute_count': len(last_minute)
        }

    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log security-related events"""
        try:
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'client_id': self.get_client_identifier(),
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'endpoint': request.endpoint,
                'method': request.method,
                'details': details
            }

            # Use existing audit logging if available
            if hasattr(current_app, 'security_logger'):
                current_app.security_logger.info(json.dumps(log_data))
            else:
                current_app.logger.warning(f"Security Event: {json.dumps(log_data)}")

        except Exception as e:
            current_app.logger.error(f"Failed to log security event: {e}")

    def create_rate_limit_response(self, action_type: str) -> tuple:
        """Create a standardized rate limit response"""
        return jsonify({
            'success': False,
            'message': f'Rate limit exceeded for {action_type} actions',
            'code': 429,
            'retry_after': 60
        }), 429


# Global security manager instance
job_actions_security = JobActionsSecurityManager()


def validate_job_action_request(action_type: str, require_auth: bool = True):
    """
    Decorator for validating job action requests
    
    Args:
        action_type: Type of action (like, save, share, etc.)
        require_auth: Whether authentication is required
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check authentication if required
            if require_auth and not (hasattr(g, 'user') and g.user):
                job_actions_security.log_security_event('unauthorized_access', {
                    'action_type': action_type,
                    'endpoint': request.endpoint
                })
                return jsonify({
                    'success': False,
                    'message': 'Authentication required',
                    'code': 401
                }), 401

            # Validate request data
            if request.method in ['POST', 'PUT']:
                if not request.is_json and not request.form:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid request format',
                        'code': 400
                    }), 400

            # Check CSRF token for state-changing operations
            if not job_actions_security.check_csrf_token():
                job_actions_security.log_security_event('csrf_violation', {
                    'action_type': action_type,
                    'endpoint': request.endpoint
                })
                return jsonify({
                    'success': False,
                    'message': 'CSRF token validation failed',
                    'code': 403
                }), 403

            # Detect suspicious activity
            if hasattr(g, 'user') and g.user:
                suspicion_check = job_actions_security.detect_suspicious_activity(
                    g.user.uid, action_type
                )

                if suspicion_check['is_suspicious']:
                    job_actions_security.log_security_event('suspicious_activity', {
                        'action_type': action_type,
                        'indicators': suspicion_check['indicators'],
                        'user_id': g.user.uid
                    })

                    # For now, just log - could implement blocking in the future
                    current_app.logger.warning(
                        f"Suspicious activity detected for user {g.user.uid}: "
                        f"{suspicion_check['indicators']}"
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_job_action(action_type: str):
    """
    Decorator for applying rate limits to job actions
    
    Args:
        action_type: Type of action to rate limit
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get rate limit configuration
            limit_config = job_actions_security.rate_limits.get(action_type, {})
            limit_string = limit_config.get('limit', '10 per minute')

            # Apply rate limiting
            try:
                # Use the existing limiter with custom limit
                @limiter.limit(limit_string)
                def rate_limited_func():
                    return func(*args, **kwargs)

                return rate_limited_func()

            except Exception as e:
                # Rate limit exceeded
                job_actions_security.log_security_event('rate_limit_exceeded', {
                    'action_type': action_type,
                    'limit': limit_string,
                    'client_id': job_actions_security.get_client_identifier()
                })

                return job_actions_security.create_rate_limit_response(action_type)

        return wrapper

    return decorator


def secure_job_action(action_type: str, require_auth: bool = True):
    """
    Combined decorator for comprehensive job action security
    
    Args:
        action_type: Type of action
        require_auth: Whether authentication is required
    """

    def decorator(func):
        @wraps(func)
        @rate_limit_job_action(action_type)
        @validate_job_action_request(action_type, require_auth)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_job_id_param(func):
    """Decorator to validate job_id parameter"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        job_id = kwargs.get('job_id') or (args[1] if len(args) > 1 else None)

        if not job_actions_security.validate_job_id(job_id):
            job_actions_security.log_security_event('invalid_job_id', {
                'job_id': job_id,
                'endpoint': request.endpoint
            })
            return jsonify({
                'success': False,
                'message': 'Invalid job ID format',
                'code': 400
            }), 400

        return func(*args, **kwargs)

    return wrapper


def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize input data to prevent injection attacks"""
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Basic HTML/script tag removal
            value = value.replace('<script>', '').replace('</script>', '')
            value = value.replace('<', '&lt;').replace('>', '&gt;')
            # Limit string length
            value = value[:1000] if len(value) > 1000 else value
        elif isinstance(value, dict):
            value = sanitize_input(value)
        elif isinstance(value, list):
            value = [sanitize_input(item) if isinstance(item, dict) else item for item in value[:100]]

        sanitized[key] = value

    return sanitized


def check_ip_reputation(ip_address: str) -> Dict[str, Any]:
    """Check IP address reputation (placeholder for future implementation)"""
    # This could integrate with threat intelligence services
    # For now, just return a basic check

    try:
        ip_obj = ip_address(ip_address)

        # Check for private/local IPs
        if ip_obj.is_private or ip_obj.is_loopback:
            return {'is_suspicious': False, 'reason': 'private_ip'}

        # Placeholder for external reputation checks
        return {'is_suspicious': False, 'reason': 'clean'}

    except ValueError:
        return {'is_suspicious': True, 'reason': 'invalid_ip'}


def generate_csrf_token() -> str:
    """Generate a CSRF token for the session"""
    import secrets
    token = secrets.token_urlsafe(32)
    session['csrf_token'] = token
    return token


def get_csrf_token() -> Optional[str]:
    """Get the current CSRF token from session"""
    return session.get('csrf_token')
