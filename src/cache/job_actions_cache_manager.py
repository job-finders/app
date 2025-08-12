"""
Job Actions Cache Manager

Centralized cache management for job actions operations with intelligent
invalidation strategies, performance optimization, and comprehensive monitoring.

This module provides a unified caching layer for all job actions operations
including likes, saves, shares, and engagement statistics with proper
cache invalidation, performance monitoring, and optimization strategies.

Cache Features:
- Centralized cache management with consistent patterns
- Intelligent cache invalidation strategies
- Performance optimization with cache warming
- Session pooling integration
- Comprehensive cache monitoring and analytics
"""

import json
import hashlib
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import time

from src.cache.cache_redis import cache
from src.utils.job_actions_performance_logger import job_actions_performance_logger
from src.logger import init_logger


@dataclass
class CacheMetrics:
    """Cache performance metrics tracking"""
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    warming_operations: int = 0
    total_operations: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage"""
        if self.total_operations == 0:
            return 0.0
        return (self.hits / self.total_operations) * 100

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage"""
        return 100.0 - self.hit_rate


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    data: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        """Update access metadata"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class JobActionsCacheManager:
    """
    Centralized cache management for job actions operations.
    
    This class provides comprehensive caching capabilities with intelligent
    invalidation strategies, performance optimization, and monitoring for
    all job actions operations including likes, saves, shares, and statistics.
    
    Features:
        - Centralized cache key management with consistent naming
        - Intelligent cache invalidation with dependency tracking
        - Performance optimization with cache warming strategies
        - Session pooling integration for database operations
        - Comprehensive cache monitoring and analytics
        - Cache entry tagging for bulk invalidation
        - TTL management with automatic expiration
        - Cache warming for expensive operations
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize the cache manager.
        
        Args:
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self.logger = init_logger("JobActionsCacheManager")
        self.default_ttl = default_ttl

        # Cache metrics tracking
        self._metrics = CacheMetrics()
        self._metrics_lock = threading.RLock()

        # Cache dependency tracking for intelligent invalidation
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)

        # Cache warming configuration
        self._warming_strategies: Dict[str, Callable] = {}
        self._warming_schedule: Dict[str, datetime] = {}

        # Performance thresholds
        self.slow_cache_operation_threshold = 0.1  # seconds
        self.low_hit_rate_threshold = 70.0  # percentage

        self.logger.info("JobActionsCacheManager initialized")

    def get(self, key: str, default: Any = None, tags: Optional[Set[str]] = None) -> Any:
        """
        Get value from cache with performance tracking.
        
        Args:
            key: Cache key
            default: Default value if key not found
            tags: Tags to associate with cache access
            
        Returns:
            Cached value or default
        """
        start_time = time.time()

        try:
            # Track cache operation
            with self._metrics_lock:
                self._metrics.total_operations += 1

            # Get from Redis cache
            cached_data = cache.get(key)

            if cached_data is not None:
                # Cache hit
                with self._metrics_lock:
                    self._metrics.hits += 1

                # Record performance metrics
                duration = time.time() - start_time
                job_actions_performance_logger.record_cache_operation(
                    operation=f"get_{self._get_cache_category(key)}",
                    hit=True,
                    duration=duration
                )

                # Log slow cache operations
                if duration > self.slow_cache_operation_threshold:
                    self.logger.warning(f"Slow cache get operation: {key} took {duration:.3f}s")

                try:
                    return json.loads(cached_data)
                except (json.JSONDecodeError, TypeError):
                    return cached_data
            else:
                # Cache miss
                with self._metrics_lock:
                    self._metrics.misses += 1

                # Record performance metrics
                duration = time.time() - start_time
                job_actions_performance_logger.record_cache_operation(
                    operation=f"get_{self._get_cache_category(key)}",
                    hit=False,
                    duration=duration
                )

                self.logger.debug(f"Cache miss for key: {key}")
                return default

        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None) -> bool:
        """
        Set value in cache with dependency tracking.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            tags: Tags for dependency tracking and bulk invalidation
            
        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()

        try:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl

            # Serialize value for storage
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = value

            # Set in Redis cache
            success = cache.set(key, serialized_value, ttl=ttl)

            if success:
                # Track dependencies if tags provided
                if tags:
                    self._track_dependencies(key, tags)

                # Record performance metrics
                duration = time.time() - start_time
                job_actions_performance_logger.record_cache_operation(
                    operation=f"set_{self._get_cache_category(key)}",
                    hit=True,  # Set operations are always "hits"
                    duration=duration
                )

                # Log slow cache operations
                if duration > self.slow_cache_operation_threshold:
                    self.logger.warning(f"Slow cache set operation: {key} took {duration:.3f}s")

                self.logger.debug(f"Cache set successful for key: {key} (TTL: {ttl}s)")
                return True
            else:
                self.logger.warning(f"Cache set failed for key: {key}")
                return False

        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache with dependency cleanup.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from Redis cache
            success = cache.delete(key)

            if success:
                # Clean up dependencies
                self._cleanup_dependencies(key)

                # Track invalidation
                with self._metrics_lock:
                    self._metrics.invalidations += 1

                self.logger.debug(f"Cache delete successful for key: {key}")
                return True
            else:
                self.logger.debug(f"Cache delete failed or key not found: {key}")
                return False

        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def invalidate_by_tags(self, tags: Set[str]) -> int:
        """
        Invalidate all cache entries with specified tags.
        
        Args:
            tags: Set of tags to invalidate
            
        Returns:
            Number of entries invalidated
        """
        invalidated_count = 0

        try:
            # Find all keys with these tags
            keys_to_invalidate = set()

            for tag in tags:
                if tag in self._reverse_dependencies:
                    keys_to_invalidate.update(self._reverse_dependencies[tag])

            # Invalidate all found keys
            for key in keys_to_invalidate:
                if self.delete(key):
                    invalidated_count += 1

            self.logger.info(f"Invalidated {invalidated_count} cache entries for tags: {tags}")
            return invalidated_count

        except Exception as e:
            self.logger.error(f"Cache invalidation by tags error: {e}")
            return invalidated_count

    def warm_cache(self, warming_key: str, warming_function: Callable, *args, **kwargs) -> bool:
        """
        Warm cache with expensive operation results.
        
        Args:
            warming_key: Key to identify the warming operation
            warming_function: Function to execute for cache warming
            *args: Arguments for warming function
            **kwargs: Keyword arguments for warming function
            
        Returns:
            True if successful, False otherwise
        """
        try:
            start_time = time.time()

            # Execute warming function
            result = warming_function(*args, **kwargs)

            # Cache the result if it's not None
            if result is not None:
                cache_key = self._generate_cache_key("warmed", warming_key, *args, **kwargs)
                success = self.set(cache_key, result, tags={"warmed", warming_key})

                if success:
                    # Track warming operation
                    with self._metrics_lock:
                        self._metrics.warming_operations += 1

                    # Record performance metrics
                    duration = time.time() - start_time
                    job_actions_performance_logger.record_cache_operation(
                        operation=f"warm_{warming_key}",
                        hit=True,
                        duration=duration
                    )

                    self.logger.info(f"Cache warming successful for {warming_key} (took {duration:.3f}s)")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Cache warming error for {warming_key}: {e}")
            return False

    # Job Actions Specific Cache Methods

    def get_user_action_cache(self, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user action state for a specific job"""
        key = self._generate_cache_key("user_actions", user_id, job_id)
        return self.get(key, tags={"user_actions", f"user:{user_id}", f"job:{job_id}"})

    def set_user_action_cache(self, user_id: str, job_id: str, actions_data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache user action state for a specific job"""
        key = self._generate_cache_key("user_actions", user_id, job_id)
        return self.set(key, actions_data, ttl=ttl, tags={"user_actions", f"user:{user_id}", f"job:{job_id}"})

    def invalidate_user_action_cache(self, user_id: str, job_id: str) -> bool:
        """Invalidate user action cache for a specific job"""
        key = self._generate_cache_key("user_actions", user_id, job_id)
        return self.delete(key)

    def get_job_engagement_stats(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get cached job engagement statistics"""
        key = self._generate_cache_key("job_engagement", job_id)
        return self.get(key, tags={"job_engagement", f"job:{job_id}"})

    def set_job_engagement_stats(self, job_id: str, stats_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache job engagement statistics"""
        key = self._generate_cache_key("job_engagement", job_id)
        return self.set(key, stats_data, ttl=ttl, tags={"job_engagement", f"job:{job_id}"})

    def invalidate_job_engagement_stats(self, job_id: str) -> bool:
        """Invalidate job engagement statistics cache"""
        key = self._generate_cache_key("job_engagement", job_id)
        return self.delete(key)

    def get_user_liked_jobs(self, user_id: str, limit: int, offset: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached user liked jobs list"""
        key = self._generate_cache_key("user_liked_jobs", user_id, limit, offset)
        return self.get(key, tags={"user_liked_jobs", f"user:{user_id}"})

    def set_user_liked_jobs(self, user_id: str, limit: int, offset: int, jobs_data: List[Dict[str, Any]],
                            ttl: int = 1800) -> bool:
        """Cache user liked jobs list"""
        key = self._generate_cache_key("user_liked_jobs", user_id, limit, offset)
        return self.set(key, jobs_data, ttl=ttl, tags={"user_liked_jobs", f"user:{user_id}"})

    def invalidate_user_liked_jobs(self, user_id: str) -> int:
        """Invalidate all cached user liked jobs lists"""
        return self.invalidate_by_tags({f"user:{user_id}", "user_liked_jobs"})

    def get_user_saved_jobs(self, user_id: str, limit: int, offset: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached user saved jobs list"""
        key = self._generate_cache_key("user_saved_jobs", user_id, limit, offset)
        return self.get(key, tags={"user_saved_jobs", f"user:{user_id}"})

    def set_user_saved_jobs(self, user_id: str, limit: int, offset: int, jobs_data: List[Dict[str, Any]],
                            ttl: int = 1800) -> bool:
        """Cache user saved jobs list"""
        key = self._generate_cache_key("user_saved_jobs", user_id, limit, offset)
        return self.set(key, jobs_data, ttl=ttl, tags={"user_saved_jobs", f"user:{user_id}"})

    def invalidate_user_saved_jobs(self, user_id: str) -> int:
        """Invalidate all cached user saved jobs lists"""
        return self.invalidate_by_tags({f"user:{user_id}", "user_saved_jobs"})

    def invalidate_job_related_caches(self, job_id: str) -> int:
        """Invalidate all caches related to a specific job"""
        return self.invalidate_by_tags({f"job:{job_id}"})

    def invalidate_user_related_caches(self, user_id: str) -> int:
        """Invalidate all caches related to a specific user"""
        return self.invalidate_by_tags({f"user:{user_id}"})

    # Cache Analytics and Monitoring

    def get_cache_metrics(self) -> CacheMetrics:
        """Get current cache performance metrics"""
        with self._metrics_lock:
            return CacheMetrics(
                hits=self._metrics.hits,
                misses=self._metrics.misses,
                invalidations=self._metrics.invalidations,
                warming_operations=self._metrics.warming_operations,
                total_operations=self._metrics.total_operations
            )

    def reset_cache_metrics(self) -> None:
        """Reset cache performance metrics"""
        with self._metrics_lock:
            self._metrics = CacheMetrics()
        self.logger.info("Cache metrics reset")

    def generate_cache_report(self) -> Dict[str, Any]:
        """Generate comprehensive cache performance report"""
        metrics = self.get_cache_metrics()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": {
                "total_operations": metrics.total_operations,
                "cache_hits": metrics.hits,
                "cache_misses": metrics.misses,
                "hit_rate_percentage": metrics.hit_rate,
                "miss_rate_percentage": metrics.miss_rate,
                "invalidations": metrics.invalidations,
                "warming_operations": metrics.warming_operations
            },
            "health_indicators": {
                "hit_rate_healthy": metrics.hit_rate >= self.low_hit_rate_threshold,
                "dependency_tracking_active": len(self._dependencies) > 0,
                "warming_strategies_configured": len(self._warming_strategies) > 0
            },
            "recommendations": self._generate_cache_recommendations(metrics)
        }

    # Private Helper Methods

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key with prefix and arguments"""
        key_parts = [prefix]

        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))

        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")

        # Create hash for very long keys
        key_string = ":".join(key_parts)
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"

        return key_string

    def _get_cache_category(self, key: str) -> str:
        """Extract cache category from key for metrics"""
        parts = key.split(":")
        return parts[0] if parts else "unknown"

    def _track_dependencies(self, key: str, tags: Set[str]) -> None:
        """Track cache dependencies for intelligent invalidation"""
        try:
            # Track forward dependencies (key -> tags)
            self._dependencies[key] = tags.copy()

            # Track reverse dependencies (tag -> keys)
            for tag in tags:
                self._reverse_dependencies[tag].add(key)

        except Exception as e:
            self.logger.error(f"Error tracking dependencies for key {key}: {e}")

    def _cleanup_dependencies(self, key: str) -> None:
        """Clean up dependency tracking for deleted key"""
        try:
            # Get tags for this key
            if key in self._dependencies:
                tags = self._dependencies[key]

                # Remove from reverse dependencies
                for tag in tags:
                    if tag in self._reverse_dependencies:
                        self._reverse_dependencies[tag].discard(key)

                        # Clean up empty tag entries
                        if not self._reverse_dependencies[tag]:
                            del self._reverse_dependencies[tag]

                # Remove forward dependency
                del self._dependencies[key]

        except Exception as e:
            self.logger.error(f"Error cleaning up dependencies for key {key}: {e}")

    def _generate_cache_recommendations(self, metrics: CacheMetrics) -> List[str]:
        """Generate cache optimization recommendations based on metrics"""
        recommendations = []

        if metrics.hit_rate < self.low_hit_rate_threshold:
            recommendations.append(
                f"Cache hit rate is low ({metrics.hit_rate:.1f}%). Consider increasing TTL or implementing cache warming.")

        if metrics.total_operations > 0 and metrics.warming_operations / metrics.total_operations < 0.1:
            recommendations.append("Consider implementing more cache warming strategies for expensive operations.")

        if len(self._dependencies) == 0:
            recommendations.append(
                "No cache dependencies tracked. Consider implementing dependency tracking for better invalidation.")

        if not recommendations:
            recommendations.append("Cache performance is healthy. Continue monitoring.")

        return recommendations


# Global cache manager instance
job_actions_cache_manager = JobActionsCacheManager()
