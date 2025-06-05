# src/firewall/improved_rate_limiting.py
import asyncio
import aiohttp
import redis
import time
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Tuple, Dict
from flask import request, g, current_app, jsonify, make_response
from ipaddress import ip_address, ip_network
import logging

logger = logging.getLogger(__name__)


class CloudflareIPManager:
    """Async manager for Cloudflare IP ranges with fallback"""

    def __init__(self):
        self.last_update = None
        self.update_interval = timedelta(hours=6)
        # Fallback IP ranges
        self.ips = [
            ip_network("173.245.48.0/20"), ip_network("103.21.244.0/22"),
            ip_network("103.22.200.0/22"), ip_network("141.101.64.0/18"),
            ip_network("108.162.192.0/18"), ip_network("104.16.0.0/13"),
            ip_network("172.64.0.0/13"), ip_network("2400:cb00::/32"),
            ip_network("2606:4700::/32")
        ]

    async def update_ips_async(self):
        """Async update with comprehensive error handling"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                tasks = [
                    session.get('https://www.cloudflare.com/ips-v4'),
                    session.get('https://www.cloudflare.com/ips-v6')
                ]

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                ip_lists = []
                for resp in responses:
                    if isinstance(resp, Exception):
                        logger.warning(f"Failed to fetch Cloudflare IPs: {resp}")
                        continue
                    text = await resp.text()
                    ip_lists.extend(text.strip().splitlines())

                if ip_lists:
                    self.ips = [ip_network(ip.strip()) for ip in ip_lists if ip.strip()]
                    self.last_update = datetime.utcnow()
                    logger.info(f"Updated {len(self.ips)} Cloudflare IP ranges")

        except Exception as e:
            logger.error(f"Critical error updating Cloudflare IPs: {e}")

    def should_update(self) -> bool:
        return (not self.last_update or
                datetime.utcnow() - self.last_update > self.update_interval)

    def is_cloudflare_ip(self, ip_str: str) -> bool:
        """Check if IP belongs to Cloudflare"""
        try:
            ip = ip_address(ip_str)
            return any(ip in network for network in self.ips)
        except ValueError:
            return False


class RedisRateLimiter:
    """Redis-based sliding window rate limiter"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.circuit_breaker = CircuitBreaker()

    def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        """Sliding window rate limiting with circuit breaker"""
        try:
            return self.circuit_breaker.call(self._check_limit, key, limit, window)
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return False  # Fail open for availability

    def _check_limit(self, key: str, limit: int, window: int) -> bool:
        """Internal rate limit check"""
        current_time = time.time()

        with self.redis.pipeline() as pipe:
            pipe.multi()

            # Remove expired entries
            pipe.zremrangebyscore(key, 0, current_time - window)

            # Count current requests
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration
            pipe.expire(key, window + 1)

            results = pipe.execute()
            current_count = results[1]

            return current_count >= limit

    def get_remaining_limit(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests in current window"""
        try:
            current_time = time.time()
            self.redis.zremrangebyscore(key, 0, current_time - window)
            current_count = self.redis.zcard(key)
            return max(0, limit - current_count)
        except Exception:
            return limit


class CircuitBreaker:
    """Circuit breaker for Redis operations"""

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'

    def call(self, func, *args, **kwargs):
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'

    def reset(self):
        self.failure_count = 0
        self.state = 'closed'


class SmartRateLimiter:
    """Context-aware rate limiter with user differentiation"""

    def __init__(self, redis_client: redis.Redis, config: Dict):
        self.redis_limiter = RedisRateLimiter(redis_client)
        self.cloudflare_manager = CloudflareIPManager()
        self.config = config
        self.monitor = RateLimitMonitor(redis_client)

    def get_client_ip(self) -> str:
        """Get real client IP with Cloudflare support"""
        client_ip = request.remote_addr

        # Only trust CF headers from Cloudflare IPs
        if self.cloudflare_manager.is_cloudflare_ip(client_ip):
            return request.headers.get('CF-Connecting-IP', client_ip)

        return client_ip

    def get_rate_limit_key(self) -> Tuple[str, Tuple[int, int]]:
        """Generate smart rate limit key and limits"""
        ip = self.get_client_ip()
        user_id = getattr(g, 'user_id', None)
        endpoint = request.endpoint or 'unknown'

        # Use user ID if available, fall back to IP
        if user_id:
            base_key = f"user:{user_id}:{endpoint}"
            user_type = self.get_user_type(user_id)
        else:
            base_key = f"ip:{ip}:{endpoint}"
            user_type = 'anonymous'

        # Get limits for this endpoint and user type
        limits = self.get_limits_for_endpoint(endpoint, user_type)

        return base_key, limits

    def get_user_type(self, user_id: str) -> str:
        """Determine user type (cached)"""
        # This should be cached and fetched from your user service
        # Simplified example:
        cache_key = f"user_type:{user_id}"
        cached_type = self.redis_limiter.redis.get(cache_key)

        if cached_type:
            return cached_type.decode('utf-8')

        # Fetch from database (implement your logic)
        user_type = 'user'  # Default fallback

        # Cache for 5 minutes
        self.redis_limiter.redis.setex(cache_key, 300, user_type)
        return user_type

    def get_limits_for_endpoint(self, endpoint: str, user_type: str) -> Tuple[int, int]:
        """Get rate limits for specific endpoint and user type"""
        endpoint_limits = self.config.get(endpoint, self.config.get('default', {}))

        if isinstance(endpoint_limits, dict):
            return endpoint_limits.get(user_type, (30, 60))  # Default: 30 per minute

        return endpoint_limits  # Backward compatibility

    def is_rate_limited(self) -> Tuple[bool, Dict]:
        """Check if current request is rate limited"""
        key, (limit, window) = self.get_rate_limit_key()

        is_limited = self.redis_limiter.is_rate_limited(key, limit, window)
        remaining = self.redis_limiter.get_remaining_limit(key, limit, window)

        info = {
            'limit': limit,
            'remaining': remaining,
            'reset_time': int(time.time() + window),
            'retry_after': window if is_limited else 0
        }

        if is_limited:
            self.monitor.log_rate_limit_hit(key, request.endpoint, self.get_client_ip())

        return is_limited, info


class RateLimitMonitor:
    """Monitoring and alerting for rate limiting"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def log_rate_limit_hit(self, key: str, endpoint: str, ip: str):
        """Log rate limit violations"""
        event = {
            'timestamp': time.time(),
            'key': key,
            'endpoint': endpoint,
            'ip': ip,
            'user_agent': request.headers.get('User-Agent', '')[:100]
        }

        # Store recent events
        self.redis.lpush('rate_limit_events', json.dumps(event))
        self.redis.ltrim('rate_limit_events', 0, 1000)

        # Check for abuse patterns
        self._check_abuse_patterns(ip, endpoint)

    def _check_abuse_patterns(self, ip: str, endpoint: str):
        """Detect and respond to abuse patterns"""
        # Count violations from this IP in last hour
        recent_key = f"violations:{ip}"
        violations = self.redis.incr(recent_key)
        self.redis.expire(recent_key, 3600)  # 1 hour

        if violations > 50:  # Threshold
            logger.warning(f"High rate limit violations from IP {ip}: {violations}")
            # Could trigger additional security measures here


def smart_rate_limit(custom_limit: Optional[Tuple[int, int]] = None):
    """Enhanced rate limiting decorator"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = current_app.extensions.get('smart_limiter')

            if not limiter:
                logger.warning("Smart limiter not initialized")
                return f(*args, **kwargs)

            # Update Cloudflare IPs if needed (async in background)
            if limiter.cloudflare_manager.should_update():
                asyncio.create_task(limiter.cloudflare_manager.update_ips_async())

            is_limited, info = limiter.is_rate_limited()

            if custom_limit:
                # Override with custom limits
                key, _ = limiter.get_rate_limit_key()
                limit, window = custom_limit
                is_limited = limiter.redis_limiter.is_rate_limited(key, limit, window)
                info.update({'limit': limit, 'retry_after': window if is_limited else 0})

            if is_limited:
                response = make_response(
                    jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f"Too many requests. Try again in {info['retry_after']} seconds."
                    }), 429
                )

                # Add rate limit headers
                response.headers.update({
                    'X-RateLimit-Limit': str(info['limit']),
                    'X-RateLimit-Remaining': str(info['remaining']),
                    'X-RateLimit-Reset': str(info['reset_time']),
                    'Retry-After': str(info['retry_after'])
                })

                return response

            # Add rate limit info to successful responses
            response = make_response(f(*args, **kwargs))
            response.headers.update({
                'X-RateLimit-Limit': str(info['limit']),
                'X-RateLimit-Remaining': str(info['remaining']),
                'X-RateLimit-Reset': str(info['reset_time'])
            })

            return response

        return decorated_function

    return decorator


def init_smart_rate_limiter(app):
    """Initialize smart rate limiter"""
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = redis.Redis.from_url(redis_url, decode_responses=False)

    # Default rate limit configuration
    rate_limits = app.config.get('RATE_LIMITS', {
        'auth.login': {'anonymous': (5, 300), 'user': (10, 300), 'premium': (20, 300)},
        'auth.subscribe': {'anonymous': (3, 300), 'user': (5, 300), 'premium': (10, 300)},
        'auth.password_reset': {'anonymous': (2, 300), 'user': (3, 300), 'premium': (5, 300)},
        'default': {'anonymous': (30, 60), 'user': (100, 60), 'premium': (500, 60)}
    })

    limiter = SmartRateLimiter(redis_client, rate_limits)
    app.extensions['smart_limiter'] = limiter

    return limiter