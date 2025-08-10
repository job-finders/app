"""
Job Actions Cache Service

Specialized caching layer for job actions functionality including:
- Job actions state (likes, saves, shares)
- Company public profiles
- Job engagement statistics
- User activity data
"""

import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.cache.cache_redis import RedisCache
from src.database.constants import utc_time


class JobActionsCacheService:
    """Specialized cache service for job actions functionality"""

    def __init__(self, redis_cache: Optional[RedisCache] = None):
        self.cache = redis_cache or RedisCache(
            prefix="job_actions:",
            default_ttl=3600  # 1 hour default
        )

        # Cache TTL configurations (in seconds)
        self.ttl_config = {
            'job_actions_state': 1800,  # 30 minutes
            'company_profile': 3600,  # 1 hour
            'company_statistics': 7200,  # 2 hours
            'job_engagement': 900,  # 15 minutes
            'user_liked_jobs': 1800,  # 30 minutes
            'user_saved_jobs': 1800,  # 30 minutes
            'company_jobs': 1800,  # 30 minutes
            'job_categories': 7200,  # 2 hours
        }

    def _generate_key(self, key_type: str, *identifiers) -> str:
        """Generate a consistent cache key"""
        key_parts = [key_type] + [str(id) for id in identifiers]
        key_string = ":".join(key_parts)

        # Hash long keys to ensure Redis compatibility
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{key_type}:{key_hash}"

        return key_string

    def _get_ttl(self, key_type: str) -> int:
        """Get TTL for a specific key type"""
        return self.ttl_config.get(key_type, self.cache.default_ttl)

    # Job Actions State Caching
    def get_job_actions_state(self, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Get cached job actions state for a user and job"""
        key = self._generate_key('job_actions_state', user_id, job_id)
        return self.cache.get(key)

    def set_job_actions_state(self, user_id: str, job_id: str, state: Dict[str, Any]) -> None:
        """Cache job actions state for a user and job"""
        key = self._generate_key('job_actions_state', user_id, job_id)
        ttl = self._get_ttl('job_actions_state')

        # Add timestamp for cache validation
        state['cached_at'] = utc_time().isoformat()

        self.cache.set(key, state, ttl)

    def invalidate_job_actions_state(self, user_id: str, job_id: str) -> None:
        """Invalidate job actions state cache"""
        key = self._generate_key('job_actions_state', user_id, job_id)
        self.cache.delete(key)

    # Company Profile Caching
    def get_company_profile(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get cached company public profile"""
        key = self._generate_key('company_profile', company_id)
        return self.cache.get(key)

    def set_company_profile(self, company_id: str, profile_data: Dict[str, Any]) -> None:
        """Cache company public profile"""
        key = self._generate_key('company_profile', company_id)
        ttl = self._get_ttl('company_profile')

        profile_data['cached_at'] = utc_time().isoformat()
        self.cache.set(key, profile_data, ttl)

    def invalidate_company_profile(self, company_id: str) -> None:
        """Invalidate company profile cache"""
        key = self._generate_key('company_profile', company_id)
        self.cache.delete(key)

    # Company Statistics Caching
    def get_company_statistics(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get cached company statistics"""
        key = self._generate_key('company_statistics', company_id)
        return self.cache.get(key)

    def set_company_statistics(self, company_id: str, stats: Dict[str, Any]) -> None:
        """Cache company statistics"""
        key = self._generate_key('company_statistics', company_id)
        ttl = self._get_ttl('company_statistics')

        stats['cached_at'] = utc_time().isoformat()
        self.cache.set(key, stats, ttl)

    def invalidate_company_statistics(self, company_id: str) -> None:
        """Invalidate company statistics cache"""
        key = self._generate_key('company_statistics', company_id)
        self.cache.delete(key)

    # Job Engagement Caching
    def get_job_engagement_stats(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get cached job engagement statistics"""
        key = self._generate_key('job_engagement', job_id)
        return self.cache.get(key)

    def set_job_engagement_stats(self, job_id: str, stats: Dict[str, Any]) -> None:
        """Cache job engagement statistics"""
        key = self._generate_key('job_engagement', job_id)
        ttl = self._get_ttl('job_engagement')

        stats['cached_at'] = utc_time().isoformat()
        self.cache.set(key, stats, ttl)

    def invalidate_job_engagement_stats(self, job_id: str) -> None:
        """Invalidate job engagement statistics cache"""
        key = self._generate_key('job_engagement', job_id)
        self.cache.delete(key)

    # User Activity Caching
    def get_user_liked_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> Optional[Dict[str, Any]]:
        """Get cached user liked jobs"""
        key = self._generate_key('user_liked_jobs', user_id, limit, offset)
        return self.cache.get(key)

    def set_user_liked_jobs(self, user_id: str, jobs_data: Dict[str, Any], limit: int = 20, offset: int = 0) -> None:
        """Cache user liked jobs"""
        key = self._generate_key('user_liked_jobs', user_id, limit, offset)
        ttl = self._get_ttl('user_liked_jobs')

        jobs_data['cached_at'] = utc_time().isoformat()
        self.cache.set(key, jobs_data, ttl)

    def invalidate_user_liked_jobs(self, user_id: str) -> None:
        """Invalidate all cached liked jobs for a user"""
        # Use pattern matching to delete all user liked jobs cache entries
        pattern = self._generate_key('user_liked_jobs', user_id, '*')
        self._delete_pattern(pattern)

    # User Saved Jobs Caching
    def get_user_saved_jobs(self, user_id: str, limit: int = 20, offset: int = 0) -> Optional[Dict[str, Any]]:
        """Get cached user saved jobs"""
        key = self._generate_key('user_saved_jobs', user_id, limit, offset)
        return self.cache.get(key)

    def set_user_saved_jobs(self, user_id: str, jobs_data: Dict[str, Any], limit: int = 20, offset: int = 0) -> None:
        """Cache user saved jobs"""
        key = self._generate_key('user_saved_jobs', user_id, limit, offset)
        ttl = self._get_ttl('user_saved_jobs')

        jobs_data['cached_at'] = utc_time().isoformat()
        self.cache.set(key, jobs_data, ttl)

    def invalidate_user_saved_jobs(self, user_id: str) -> None:
        """Invalidate all cached saved jobs for a user"""
        pattern = self._generate_key('user_saved_jobs', user_id, '*')
        self._delete_pattern(pattern)

    # Company Jobs Caching
    def get_company_jobs(self, company_id: str, limit: int = 20, offset: int = 0,
                         query: str = "", category_id: str = "") -> Optional[Dict[str, Any]]:
        """Get cached company jobs"""
        cache_params = f"{limit}:{offset}:{query}:{category_id}"
        key = self._generate_key('company_jobs', company_id, cache_params)
        return self.cache.get(key)

    def set_company_jobs(self, company_id: str, jobs_data: Dict[str, Any],
                         limit: int = 20, offset: int = 0, query: str = "", category_id: str = "") -> None:
        """Cache company jobs"""
        cache_params = f"{limit}:{offset}:{query}:{category_id}"
        key = self._generate_key('company_jobs', company_id, cache_params)
        ttl = self._get_ttl('company_jobs')

        jobs_data['cached_at'] = utc_time().isoformat()
        self.cache.set(key, jobs_data, ttl)

    def invalidate_company_jobs(self, company_id: str) -> None:
        """Invalidate all cached jobs for a company"""
        pattern = self._generate_key('company_jobs', company_id, '*')
        self._delete_pattern(pattern)

    # Job Categories Caching
    def get_company_job_categories(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get cached company job categories"""
        key = self._generate_key('job_categories', company_id)
        return self.cache.get(key)

    def set_company_job_categories(self, company_id: str, categories: Dict[str, Any]) -> None:
        """Cache company job categories"""
        key = self._generate_key('job_categories', company_id)
        ttl = self._get_ttl('job_categories')

        categories['cached_at'] = utc_time().isoformat()
        self.cache.set(key, categories, ttl)

    def invalidate_company_job_categories(self, company_id: str) -> None:
        """Invalidate company job categories cache"""
        key = self._generate_key('job_categories', company_id)
        self.cache.delete(key)

    # Cache Warming
    def warm_job_cache(self, job_id: str) -> None:
        """Pre-warm cache for a job (engagement stats, etc.)"""
        # This would typically be called after job creation/update
        # Implementation would fetch and cache job-related data
        pass

    def warm_company_cache(self, company_id: str) -> None:
        """Pre-warm cache for a company (profile, stats, jobs)"""
        # This would typically be called after company updates
        # Implementation would fetch and cache company-related data
        pass

    def warm_user_cache(self, user_id: str) -> None:
        """Pre-warm cache for a user (liked jobs, saved jobs)"""
        # This would typically be called after user login
        # Implementation would fetch and cache user-related data
        pass

    # Cache Invalidation Helpers
    def invalidate_job_related_cache(self, job_id: str, company_id: str = None) -> None:
        """Invalidate all cache entries related to a job"""
        self.invalidate_job_engagement_stats(job_id)

        if company_id:
            self.invalidate_company_jobs(company_id)
            self.invalidate_company_statistics(company_id)
            self.invalidate_company_job_categories(company_id)

    def invalidate_user_action_cache(self, user_id: str, job_id: str) -> None:
        """Invalidate cache after user performs an action (like, save)"""
        self.invalidate_job_actions_state(user_id, job_id)
        self.invalidate_user_liked_jobs(user_id)
        self.invalidate_job_engagement_stats(job_id)

    def invalidate_company_related_cache(self, company_id: str) -> None:
        """Invalidate all cache entries related to a company"""
        self.invalidate_company_profile(company_id)
        self.invalidate_company_statistics(company_id)
        self.invalidate_company_jobs(company_id)
        self.invalidate_company_job_categories(company_id)

    # Utility Methods
    def _delete_pattern(self, pattern: str) -> None:
        """Delete cache entries matching a pattern"""
        try:
            # This is a simplified implementation
            # In production, you might want to use Redis SCAN for large datasets
            keys = self.cache.keys()
            matching_keys = [key for key in keys if pattern.replace('*', '') in key]
            for key in matching_keys:
                self.cache.delete(key.replace(self.cache.prefix, ''))
        except Exception as e:
            print(f"Error deleting pattern {pattern}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        try:
            info = self.cache.redis.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            return {'error': str(e)}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

    def clear_all_job_actions_cache(self) -> None:
        """Clear all job actions related cache (use with caution)"""
        try:
            self.cache.clear()
        except Exception as e:
            print(f"Error clearing job actions cache: {e}")

    def health_check(self) -> bool:
        """Check if cache service is healthy"""
        try:
            test_key = "health_check"
            test_value = "ok"
            self.cache.set(test_key, test_value, 10)
            result = self.cache.get(test_key)
            self.cache.delete(test_key)
            return result == test_value
        except Exception:
            return False


# Global cache service instance
job_actions_cache = JobActionsCacheService()


# Decorator for caching job actions methods
def cache_job_actions(cache_type: str, ttl: Optional[int] = None):
    """
    Decorator for caching job actions controller methods
    
    Usage:
        @cache_job_actions('job_engagement', ttl=900)
        async def get_job_engagement_stats(self, job_id: str):
            # method implementation
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract identifiers from arguments
            if cache_type == 'job_engagement' and len(args) >= 2:
                job_id = args[1]  # Assuming job_id is the second argument
                cached_result = job_actions_cache.get_job_engagement_stats(job_id)

                if cached_result:
                    return cached_result

                # Call original method
                result = await func(*args, **kwargs)

                # Cache the result
                if result and result.get('success'):
                    job_actions_cache.set_job_engagement_stats(job_id, result)

                return result

            # For other cache types, implement similar logic
            return await func(*args, **kwargs)

        return wrapper

    return decorator
