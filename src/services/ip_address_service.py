from flask import request, has_request_context
import socket
import requests
from src.logger import init_logger

def get_ip_address() -> str:
    """
    Robustly obtain the client's IP address from various sources.
    Handles proxy headers, direct connections, and fallback scenarios.
    """

    # Method 1: Try Flask request context first
    logger = init_logger("IP-ADDRESS-SERVICE")
    logger.info("Inside get_ip_address")
    if has_request_context():
        try:
            # Check proxy headers in order of preference
            proxy_headers = [
                'HTTP_X_FORWARDED_FOR',
                'HTTP_X_REAL_IP',
                'HTTP_X_FORWARDED',
                'HTTP_X_CLUSTER_CLIENT_IP',
                'HTTP_CLIENT_IP',
                'HTTP_FORWARDED_FOR',
                'HTTP_FORWARDED'
            ]

            # Check each proxy header
            for header in proxy_headers:
                ip = request.environ.get(header)
                if ip:
                    # Handle comma-separated IPs (take first one)
                    ip = ip.split(',')[0].strip()
                    logger.info(f"Found IP : {ip}")
                    if _is_valid_ip(ip):
                        return ip

            # Try Flask's direct methods
            if hasattr(request, 'remote_addr') and request.remote_addr:
                if _is_valid_ip(request.remote_addr):
                    logger.info(f"Found IP in Remote Header : {request.remote_addr}")
                    return request.remote_addr

            # Try environ REMOTE_ADDR
            remote_addr = request.environ.get('REMOTE_ADDR')
            if remote_addr and _is_valid_ip(remote_addr):
                return remote_addr

        except Exception as e:
            logger.info(f"Got into an Error : {str(e)}")

            print(f"Flask context IP detection failed: {e}")

    # Method 2: Try to get local machine IP
    try:
        # Connect to external service to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            if _is_valid_ip(local_ip):
                return local_ip
    except Exception as e:
        print(f"Local IP detection failed: {e}")

    # Method 3: Try external IP services (as last resort)
    external_services = [
        'https://api.ipify.org?format=text',
        'https://ipinfo.io/ip',
        'https://icanhazip.com',
        'https://ident.me'
    ]

    for service in external_services:
        try:
            response = requests.get(service, timeout=3)
            if response.status_code == 200:
                ip = response.text.strip()
                if _is_valid_ip(ip):
                    return ip
        except Exception as e:
            print(f"External service {service} failed: {e}")
            continue

    # Method 4: Try system hostname resolution
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if _is_valid_ip(ip):
            return ip
    except Exception as e:
        print(f"Hostname resolution failed: {e}")

    # Final fallback
    return "127.0.0.1"


def _is_valid_ip(ip: str) -> bool:
    """Validate if string is a valid IP address and not a private/loopback."""
    import ipaddress

    try:
        ip_obj = ipaddress.ip_address(ip)

        # Exclude invalid ranges
        if ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
            return False

        # For private IPs, only accept if no other option
        if ip_obj.is_private and ip != "127.0.0.1":
            return True

        # Public IPs are preferred
        return not ip_obj.is_private

    except ValueError:
        return False


def get_comprehensive_ip_info() -> dict:
    """Get comprehensive IP information for debugging."""
    from flask import request, has_request_context

    info = {
        'detected_ip': get_ip_address(),
        'has_request_context': has_request_context(),
        'headers': {},
        'environ_vars': {}
    }

    if has_request_context():
        try:
            # Capture relevant headers
            relevant_headers = [
                'X-Forwarded-For', 'X-Real-IP', 'X-Forwarded',
                'X-Cluster-Client-IP', 'Client-IP', 'Forwarded-For', 'Forwarded'
            ]

            for header in relevant_headers:
                value = request.headers.get(header)
                if value:
                    info['headers'][header] = value

            # Capture environ variables
            relevant_environ = [
                'REMOTE_ADDR', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP',
                'HTTP_CLIENT_IP', 'HTTP_X_CLUSTER_CLIENT_IP'
            ]

            for var in relevant_environ:
                value = request.environ.get(var)
                if value:
                    info['environ_vars'][var] = value

            info['remote_addr'] = getattr(request, 'remote_addr', None)

        except Exception as e:
            info['error'] = str(e)

    return info