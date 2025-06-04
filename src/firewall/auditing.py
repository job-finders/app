def log_security_event(request, response):
    """Log security-relevant request/response data"""
    from flask import g
    logger = logging.getLogger('security')

    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': getattr(g, 'user_id', 'anonymous'),
        'ip': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'user_agent': request.headers.get('User-Agent'),
        'sensitive': bool('password' in request.data or 'token' in request.data)
    }

    if 400 <= response.status_code < 600:
        logger.warning(f"Security event: {event}")