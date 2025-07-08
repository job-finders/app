# src/security/rate_limiting.py
import requests
from functools import wraps
from ipaddress import ip_address, ip_network
from flask import request, g, current_app, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# It's generally better to fetch this at startup or periodically
# rather than keeping a static list that can become outdated.
# For now, we'll keep the existing structure.
CLOUDFLARE_IPS = [
    ip_network("173.245.48.0/20"), ip_network("103.21.244.0/22"),
    ip_network("103.22.200.0/22"), ip_network("103.31.4.0/22"),
    ip_network("141.101.64.0/18"), ip_network("108.162.192.0/18"),
    ip_network("190.93.240.0/20"), ip_network("188.114.96.0/20"),
    ip_network("197.234.240.0/22"), ip_network("198.41.128.0/17"),
    ip_network("162.158.0.0/15"), ip_network("104.16.0.0/13"),
    ip_network("104.24.0.0/14"), ip_network("172.64.0.0/13"),
    ip_network("131.0.72.0/22"), ip_network("2400:cb00::/32"),
    ip_network("2606:4700::/32"), ip_network("2803:f800::/32"),
    ip_network("2405:b500::/32"), ip_network("2405:8100::/32"),
    ip_network("2a06:98c0::/29"), ip_network("2c0f:f248::/32"),
]

def update_cloudflare_ips():
    """Fetches the latest Cloudflare IP ranges."""
    try:
        v4 = requests.get('https://www.cloudflare.com/ips-v4', timeout=5).text.splitlines()
        v6 = requests.get('https://www.cloudflare.com/ips-v6', timeout=5).text.splitlines()
        # This will update the global list
        global CLOUDFLARE_IPS
        CLOUDFLARE_IPS = [ip_network(ip) for ip in v4 + v6]
        current_app.logger.info("Successfully updated Cloudflare IP ranges.")
    except requests.RequestException as e:
        current_app.logger.error(f"Could not update Cloudflare IPs: {e}")

def get_proxied_remote_address():
    """
    Get the real client IP address, trusting the CF-Connecting-IP header
    only if the request comes directly from a known Cloudflare IP.
    """
    remote_ip_str = get_remote_address()
    if not remote_ip_str:
        return "127.0.0.1" # Fallback if remote_addr is not available

    try:
        remote_ip = ip_address(remote_ip_str)
        # If the request is from Cloudflare, use the header they provide.
        if any(remote_ip in network for network in CLOUDFLARE_IPS):
            return request.headers.get('CF-Connecting-IP', remote_ip_str)
    except ValueError:
        # Handle cases where remote_addr might not be a valid IP string
        pass
    
    return remote_ip_str

def get_user_aware_key():
    """
    Determines the rate limit key.
    
    1. If a user is authenticated (g.user is set), the key is based on their user ID.
       This gives each user their own rate limit bucket.
    2. If the user is anonymous, it falls back to their real IP address.
    """
    # Assumes your auth decorator (e.g., @roles_required) sets g.user
    if hasattr(g, 'user') and g.user:
        # Use a stable identifier. A primary key like 'id' is best.
        user_identifier = g.user.uid or g.user.email
        if user_identifier:
            return f"user:{user_identifier}"
    
    # Fallback for anonymous users
    return get_proxied_remote_address()

# --- Limiter Initialization ---
# The key_func is now our new user-aware function.
limiter = Limiter(
    key_func=get_user_aware_key,
    default_limits=["100 per minute"],
    storage_uri="redis://localhost:6379",
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",  # or "moving-window" or "sliding-window-counter"

    # You must provide your app's storage_uri, e.g., "redis://localhost:6379"
    # storage_uri="memory://" # Example: for development only
)

def rate_limit(limit_string):
    """
    A custom decorator that wraps the limiter. This allows us to apply
    rate limits easily and consistently.
    """
    def decorator(f):
        @wraps(f)
        # Apply the limit from flask-limiter
        @limiter.limit(limit_string)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    return decorator

# --- IMPORTANT ---
# In your main application file (e.g., app.py or create_app factory):
#
# from flask import Flask
# from .security.rate_limiting import limiter, update_cloudflare_ips
#
# app = Flask(__name__)
#
# # Initialize the limiter with your app instance
# limiter.init_app(app)
#
# with app.app_context():
#    # Update IPs on startup
#    update_cloudflare_ips()
#
# Now you can use the @rate_limit decorator on your routes.
