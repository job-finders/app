from datetime import datetime, timezone
import logging


def log_security_event(request, response):
    """Log security-relevant request/response data"""
    from flask import g
    logger = logging.getLogger('security')

    # Get request data safely as string
    request_data = ''
    try:
        if request.content_type and 'application/json' in request.content_type:
            request_data = str(request.get_json() or {}).lower()
        else:
            # Convert bytes to string safely
            raw_data = request.get_data()
            if raw_data:
                request_data = raw_data.decode('utf-8', errors='ignore').lower()
    except Exception:
        request_data = ''

    event = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uid': getattr(g.user, 'uid', 'anonymous') if hasattr(g, 'user') and g.user else 'anonymous',
        'ip': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'user_agent': request.headers.get('User-Agent'),
        'sensitive': any(k in request_data for k in ('password', 'token')) if request_data else False
    }

    if 400 <= response.status_code < 600:
        logger.warning(f"Security event: {event}")
    else:
        logger.info(f"Security event: {event}")