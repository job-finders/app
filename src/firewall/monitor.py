# src/security/monitoring.py
import re
from flask import request, g
from src.logger import init_logger

security_logger = init_logger("security_monitor")

XSS_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"javascript:",
    r"onerror\s*=",
    r"alert\("
]

SQLI_PATTERNS = [
    r";\s*--",
    r";\s*#",
    r"union\s+select",
    r"exec\s*\(",
    r"waitfor\s+delay"
]


def detect_attacks():
    """Middleware to detect common attack patterns"""
    # Check URL parameters
    for key, value in request.args.items():
        scan_for_threats(f"URL param {key}", value)

    # Check POST data
    if request.is_json:
        for key, value in request.json.items():
            if isinstance(value, str):
                scan_for_threats(f"JSON field {key}", value)

    # Check headers
    scan_for_threats("User-Agent", request.headers.get('User-Agent', ''))


def scan_for_threats(context: str, input_str: str):
    """Scan input for known attack patterns"""
    if not isinstance(input_str, str):
        return

    input_lower = input_str.lower()

    # XSS detection
    for pattern in XSS_PATTERNS:
        if re.search(pattern, input_lower):
            log_threat("XSS", context, input_str)

    # SQLi detection
    for pattern in SQLI_PATTERNS:
        if re.search(pattern, input_lower):
            log_threat("SQLi", context, input_str)

    # Path traversal
    if '../' in input_str or '..\\' in input_str:
        log_threat("Path Traversal", context, input_str)


def log_threat(threat_type: str, context: str, payload: str):
    """Log security threats"""
    user_id = getattr(g, 'user_id', 'anonymous')
    ip = request.remote_addr

    security_logger.warning(
        f"{threat_type} attempt detected - "
        f"User: {user_id}, IP: {ip}, "
        f"Context: {context}, Payload: {payload[:100]}"
    )