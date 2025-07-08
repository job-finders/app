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
    r"waitfor\s+delay",
    r"or\s+1=1",  # or 1=1
    r"or\s+'1'='1'",  # or '1'='1'
    r"or\s+\"1\"=\"1\"",  # or "1"="1"
    r"and\s+1=1",  # and 1=1
    r"and\s+'1'='1'",  # and '1'='1'
    r"and\s+\"1\"=\"1\"",  # and "1"="1"
    r"select\s+.*\s+from",  # select ... from
    r"insert\s+into",  # insert into
    r"update\s+.*\s+set",  # update ... set
    r"delete\s+from",  # delete from
    r"drop\s+table",  # drop table
    r"drop\s+database",  # drop database
    r"information_schema",  # information_schema
    r"sleep\s*\(",  # sleep(
    r"benchmark\s*\(",  # benchmark(
    r"load_file\s*\(",  # load_file(
    r"outfile",  # outfile
    r"--",  # SQL comment
    r"#",  # SQL comment
    r"/\*",  # SQL comment start
    r"\*/",  # SQL comment end
    r"char\s*\(",  # char(
    r"cast\s*\(",  # cast(
    r"convert\s*\(",  # convert(
    r"having\s+",  # having clause
    r"order\s+by",  # order by
    r"group\s+by",  # group by
    r"xp_cmdshell",  # SQL Server command shell
    r"sp_executesql",  # SQL Server dynamic SQL
    r"0x[0-9a-fA-F]+",  # Hex encoded values
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
    uid = getattr(g.user, 'uid', 'anonymous') if hasattr(g, 'user') and g.user else 'anonymous'    
    ip = request.remote_addr

    security_logger.warning(
        f"{threat_type} attempt detected - "
        f"uid: {uid}, IP: {ip}, "
        f"Context: {context}, Payload: {payload[:100]}"
    )