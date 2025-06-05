# src/security/rate_limiting.py
from flask import request, current_app
from ipaddress import ip_address, ip_network
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Cloudflare's IP ranges (updated regularly)
CLOUDFLARE_IPS = [
    ip_network("173.245.48.0/20"),
    ip_network("103.21.244.0/22"),
    ip_network("103.22.200.0/22"),
    ip_network("103.31.4.0/22"),
    ip_network("141.101.64.0/18"),
    ip_network("108.162.192.0/18"),
    ip_network("190.93.240.0/20"),
    ip_network("188.114.96.0/20"),
    ip_network("197.234.240.0/22"),
    ip_network("198.41.128.0/17"),
    ip_network("162.158.0.0/15"),
    ip_network("104.16.0.0/13"),
    ip_network("104.24.0.0/14"),
    ip_network("172.64.0.0/13"),
    ip_network("131.0.72.0/22"),
    # IPv6 ranges
    ip_network("2400:cb00::/32"),
    ip_network("2606:4700::/32"),
    ip_network("2803:f800::/32"),
    ip_network("2405:b500::/32"),
    ip_network("2405:8100::/32"),
    ip_network("2a06:98c0::/29"),
    ip_network("2c0f:f248::/32"),
]

def update_cloudflare_ips():
    v4 = requests.get('https://www.cloudflare.com/ips-v4').text.splitlines()
    v6 = requests.get('https://www.cloudflare.com/ips-v6').text.splitlines()
    return [ip_network(ip) for ip in v4 + v6]

def _get_proxied_remote_address():
    # Cloudflare's recommended header :cite[6]:cite[8]
    return request.headers.get('CF-Connecting-IP', request.remote_addr)

def get_proxied_remote_address():
    """Get client IP with Cloudflare support and spoof protection"""
    client_ip = request.remote_addr

    # Only trust Cloudflare headers if request comes from Cloudflare IP
    if any(ip_address(client_ip) in network for network in CLOUDFLARE_IPS):
        return request.headers.get('CF-Connecting-IP', client_ip)

    return client_ip

limiter = Limiter(key_func=get_proxied_remote_address, default_limits=["100 per minute"])

def rate_limit(limit):
    """Decorator to apply a rate limit to a route."""
    return limiter.limit(limit)