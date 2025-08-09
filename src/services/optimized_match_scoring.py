"""
Optimized Match Scoring Service

This module provides optimized batch processing and caching for job match scoring
to improve performance and reduce database load.
"""

import asyncio
import time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

from src.cache.cache_redis import cache
from src.monitoring.match_scoring_metrics import track_performance, analytics
from src.database.models import Job, JobSeekerProfile


@dataclass
class BatchScoringRequest:
    """Request for batch match scoring"""
    user_id: str
    jobs: List[Job]
    user_profile: JobSeekerProfile
    cache_ttl: int = 1800  # 30 minutes default


@dataclass
class MatchScoreResult:
    """Result of match scoring operation"""
    job_id: str
    score: Optional[float]
    cached: bool
    error: Optional[str] = None


class OptimizedMatchScoringService:
    """Optimized service for batch match scoring with caching and performance optimizations"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Performance settings
        self.batch_size = 50  # Process jobs in batches
        self.cache_prefix = "match_score"
        self.profile_cache_prefix = "user_profile"
        
        # Circuit breaker settings
        self.failure_threshold = 5
        self.failure_count = 0
        self.circuit_open = False
        self.last_failure_time = 0
        self.circuit_timeout = 300  # 5 minutes
    
    def _generate_cache_key(self, user_id: str, job_id: str, profile_hash: str) -> str:
        """Generate cache key for match score"""
        return f"{self.cache_prefix}:{user_id}:{job_id}:{profile_hash}"
    
    def _generate_profile_hash(self, profile: JobSeekerProfile) -> str:
        """Generate hash of user profile for cache invalidation"""
        profile_data = {
            'location': getattr(profile, 'location', ''),
            'skills': getattr(profile, 'skills', []),
            'experience_level': getattr(profile, 'experience_level', ''),
            'preferred_categories': getattr(profile, 'preferred_categories', []),
            'updated_at': getattr(profile, 'updated_at', '').isoformat() if hasattr(profile, 'updated_at') else ''
        }
        
        profile_json = json.dumps(profile_data, sort_keys=True)
        return hashlib.md5(profile_json.encode()).hexdigest()[:16]
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.circuit_open:
            return False
        
        # Check if timeout has passed
        if time.time() - self.last_failure_time > self.circuit_timeout:
            self.circuit_open = False
            self.failure_count = 0
            return False
        
        return True
    
    def _record_failure(self):
        """Record a failure for circuit breaker"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
    
    def _record_success(self):
        """Record a success for circuit breaker"""
        self.failure_count = 0
        self.circuit_open = False
    
    @track_performance("batch_match_scoring")
    async def calculate_batch_scores(self, request: BatchScoringRequest) -> List[MatchScoreResult]:
        """Calculate match scores for a batch of jobs with optimizations"""
        
        # Check circuit breaker
        if self._is_circuit_open():
            return [
                MatchScoreResult(job.job_id, None, False, "Service temporarily unavailable")
                for job in request.jobs
            ]
        
        try:
            profile_hash = self._generate_profile_hash(request.user_profile)
            
            # Step 1: Check cache for existing scores
            cached_results, uncached_jobs = await self._get_cached_scores(
                request.user_id, request.jobs, profile_hash
            )
            
            # Step 2: Calculate scores for uncached jobs
            if uncached_jobs:
                calculated_results = await self._calculate_uncached_scores(
                    request.user_id, uncached_jobs, request.user_profile, profile_hash, request.cache_ttl
                )
            else:
                calculated_results = []
            
            # Step 3: Combine results
            all_results = cached_results + calculated_results
            
            # Step 4: Sort results to match original job order
            job_id_to_result = {result.job_id: result for result in all_results}
            ordered_results = [
                job_id_to_result.get(job.job_id, MatchScoreResult(job.job_id, None, False, "Not processed"))
                for job in request.jobs
            ]
            
            self._record_success()
            return ordered_results
            
        except Exception as e:
            self._record_failure()
            # Return error results for all jobs
            return [
                MatchScoreResult(job.job_id, None, False, str(e))
                for job in request.jobs
            ]
    
    async def _get_cached_scores(self, user_id: str, jobs: List[Job], profile_hash: str) -> Tuple[List[MatchScoreResult], List[Job]]:
        """Get cached scores and return uncached jobs"""
        cached_results = []
        uncached_jobs = []
        
        # Batch cache lookup
        cache_keys = [self._generate_cache_key(user_id, job.job_id, profile_hash) for job in jobs]
        cached_scores = cache.get_many(cache_keys)
        
        for job, cache_key in zip(jobs, cache_keys):
            cached_score = cached_scores.get(cache_key)
            
            if cached_score is not None:
                cached_results.append(MatchScoreResult(job.job_id, cached_score, True))
            else:
                uncached_jobs.append(job)
        
        return cached_results, uncached_jobs
    
    async def _calculate_uncached_scores(self, user_id: str, jobs: List[Job], 
                                       profile: JobSeekerProfile, profile_hash: str, 
                                       cache_ttl: int) -> List[MatchScoreResult]:
        """Calculate scores for uncached jobs with parallel processing"""
        
        # Process jobs in smaller batches to avoid overwhelming the system
        results = []
        
        for i in range(0, len(jobs), self.batch_size):
            batch = jobs[i:i + self.batch_size]
            batch_results = await self._process_job_batch(
                user_id, batch, profile, profile_hash, cache_ttl
            )
            results.extend(batch_results)
        
        return results
    
    async def _process_job_batch(self, user_id: str, jobs: List[Job], 
                               profile: JobSeekerProfile, profile_hash: str, 
                               cache_ttl: int) -> List[MatchScoreResult]:
        """Process a single batch of jobs"""
        
        # Create tasks for parallel processing
        tasks = []
        for job in jobs:
            task = self._calculate_single_score(user_id, job, profile, profile_hash, cache_ttl)
            tasks.append(task)
        
        # Execute tasks concurrently with limited concurrency
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        limited_tasks = [limited_task(task) for task in tasks]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for job, result in zip(jobs, results):
            if isinstance(result, Exception):
                processed_results.append(
                    MatchScoreResult(job.job_id, None, False, str(result))
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    @track_performance("single_match_scoring")
    async def _calculate_single_score(self, user_id: str, job: Job, 
                                    profile: JobSeekerProfile, profile_hash: str, 
                                    cache_ttl: int) -> MatchScoreResult:
        """Calculate match score for a single job"""
        
        try:
            # Import here to avoid circular imports
            from src.controllers.jobs import JobsSearchController
            from src.utils.route_helpers import get_controller
            
            controller: JobsSearchController = get_controller('jobs_search')
            
            # Calculate the score
            score = await controller.calculate_quick_match_score(job, profile)
            
            # Cache the result
            cache_key = self._generate_cache_key(user_id, job.job_id, profile_hash)
            cache.set(cache_key, score, ttl=cache_ttl)
            
            return MatchScoreResult(job.job_id, score, False)
            
        except Exception as e:
            return MatchScoreResult(job.job_id, None, False, str(e))
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cached scores for a user (when profile changes)"""
        try:
            # This would require a way to find all cache keys for a user
            # Implementation depends on your cache strategy
            
            # Option 1: Use cache key pattern matching (if supported)
            pattern = f"{self.cache_prefix}:{user_id}:*"
            cache.delete_pattern(pattern)
            
            # Option 2: Track user cache keys separately
            # user_keys = cache.get(f"user_cache_keys:{user_id}")
            # if user_keys:
            #     cache.delete_many(user_keys)
            #     cache.delete(f"user_cache_keys:{user_id}")
            
        except Exception as e:
            # Log error but don't fail
            print(f"Error invalidating cache for user {user_id}: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the service"""
        return {
            'max_workers': self.max_workers,
            'batch_size': self.batch_size,
            'circuit_breaker': {
                'is_open': self.circuit_open,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold
            },
            'cache_stats': self._get_cache_stats()
        }
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            # This would depend on your cache implementation
            # Redis example:
            info = cache.redis_client.info() if hasattr(cache, 'redis_client') else {}
            
            return {
                'connected': True,
                'memory_usage': info.get('used_memory_human', 'unknown'),
                'hit_rate': info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)
            }
        except Exception:
            return {'connected': False, 'error': 'Unable to get cache stats'}


class MatchScoringOptimizer:
    """Optimizer for match scoring performance"""
    
    def __init__(self):
        self.service = OptimizedMatchScoringService()
    
    async def optimize_job_listing_scores(self, user_id: str, jobs: List[Job], 
                                        user_profile: JobSeekerProfile) -> List[Job]:
        """Optimize match score calculation for job listings"""
        
        if not user_id or not user_profile or not jobs:
            # Set all scores to None if no user or profile
            for job in jobs:
                job.match_score = None
            return jobs
        
        # Create batch request
        request = BatchScoringRequest(
            user_id=user_id,
            jobs=jobs,
            user_profile=user_profile,
            cache_ttl=1800  # 30 minutes
        )
        
        # Calculate scores
        results = await self.service.calculate_batch_scores(request)
        
        # Apply scores to jobs
        result_map = {result.job_id: result for result in results}
        
        for job in jobs:
            result = result_map.get(job.job_id)
            if result and result.score is not None:
                job.match_score = result.score
                job._match_score_cached = result.cached
            else:
                job.match_score = None
                job._match_score_cached = False
        
        # Track analytics
        scores_displayed = sum(1 for job in jobs if job.match_score is not None)
        analytics.track_match_score_display(
            user_id=user_id,
            job_count=len(jobs),
            scores_displayed=scores_displayed,
            page_type='listing'
        )
        
        return jobs
    
    async def preload_popular_job_scores(self, popular_job_ids: List[str]):
        """Preload match scores for popular jobs to improve cache hit rate"""
        # This could be run as a background task to warm the cache
        # Implementation would depend on your job popularity tracking
        pass
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get recommendations for improving match scoring performance"""
        recommendations = []
        
        stats = self.service.get_performance_stats()
        
        # Check cache hit rate
        cache_hit_rate = stats.get('cache_stats', {}).get('hit_rate', 0)
        if cache_hit_rate < 0.7:
            recommendations.append("Consider increasing cache TTL or implementing cache warming")
        
        # Check circuit breaker status
        if stats['circuit_breaker']['is_open']:
            recommendations.append("Circuit breaker is open - investigate underlying issues")
        
        # Check batch size optimization
        if stats['batch_size'] > 100:
            recommendations.append("Consider reducing batch size for better responsiveness")
        
        return recommendations


# Global optimizer instance
optimizer = MatchScoringOptimizer()

# Export for use in routes
__all__ = [
    'OptimizedMatchScoringService',
    'MatchScoringOptimizer',
    'BatchScoringRequest',
    'MatchScoreResult',
    'optimizer'
]