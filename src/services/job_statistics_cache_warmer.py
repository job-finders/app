"""
Job Statistics Cache Warmer

This service handles pre-computing and warming the cache for job statistics
to improve performance of the job detail pages.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from src.services.job_statistics_service import JobStatisticsService
from src.utils.route_helpers import get_controller


logger = logging.getLogger(__name__)


class JobStatisticsCacheWarmer:
    """Service for warming job statistics cache"""
    
    def __init__(self):
        self.statistics_service = JobStatisticsService()
        self.batch_size = 10  # Process jobs in batches to avoid overwhelming the system
        self.max_concurrent = 3  # Maximum concurrent cache warming operations
    
    async def warm_popular_jobs_cache(self, limit: int = 50) -> int:
        """
        Warm cache for the most popular/viewed jobs
        
        Args:
            limit: Number of popular jobs to warm cache for
            
        Returns:
            Number of jobs successfully cached
        """
        try:
            job_controller = get_controller('jobs_search')
            
            # Get popular jobs (this would need to be implemented in the controller)
            # For now, get recent active jobs as a proxy for popular jobs
            popular_jobs = await self._get_recent_active_jobs(limit)
            
            if not popular_jobs:
                logger.info("No popular jobs found to warm cache")
                return 0
            
            cached_count = 0
            
            # Process jobs in batches
            for i in range(0, len(popular_jobs), self.batch_size):
                batch = popular_jobs[i:i + self.batch_size]
                
                # Create semaphore to limit concurrent operations
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                # Process batch concurrently
                tasks = [
                    self._warm_job_cache(job_id, semaphore)
                    for job_id in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful cache warming operations
                for result in results:
                    if result is True:
                        cached_count += 1
                    elif isinstance(result, Exception):
                        logger.warning(f"Error warming cache: {result}")
                
                # Small delay between batches to avoid overwhelming the system
                if i + self.batch_size < len(popular_jobs):
                    await asyncio.sleep(0.5)
            
            logger.info(f"Successfully warmed cache for {cached_count}/{len(popular_jobs)} jobs")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error warming popular jobs cache: {e}")
            return 0
    
    async def warm_company_jobs_cache(self, company_id: str) -> int:
        """
        Warm cache for all active jobs from a specific company
        
        Args:
            company_id: The company ID to warm cache for
            
        Returns:
            Number of jobs successfully cached
        """
        try:
            job_controller = get_controller('jobs_search')
            
            # Get all active jobs for the company
            company_jobs = await self._get_company_active_jobs(company_id)
            
            if not company_jobs:
                logger.info(f"No active jobs found for company {company_id}")
                return 0
            
            cached_count = 0
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            # Process all jobs concurrently with semaphore limit
            tasks = [
                self._warm_job_cache(job_id, semaphore)
                for job_id in company_jobs
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful operations
            for result in results:
                if result is True:
                    cached_count += 1
                elif isinstance(result, Exception):
                    logger.warning(f"Error warming cache for company {company_id}: {result}")
            
            logger.info(f"Warmed cache for {cached_count}/{len(company_jobs)} jobs from company {company_id}")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error warming company jobs cache for {company_id}: {e}")
            return 0
    
    async def refresh_stale_cache(self, max_age_hours: int = 6) -> int:
        """
        Refresh cache for jobs with stale statistics
        
        Args:
            max_age_hours: Maximum age of cached statistics before refresh
            
        Returns:
            Number of caches successfully refreshed
        """
        try:
            # This would require tracking cache timestamps
            # For now, implement a simple approach
            stale_jobs = await self._get_jobs_with_stale_cache(max_age_hours)
            
            if not stale_jobs:
                logger.info("No stale caches found")
                return 0
            
            refreshed_count = 0
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            # Process stale jobs in batches
            for i in range(0, len(stale_jobs), self.batch_size):
                batch = stale_jobs[i:i + self.batch_size]
                
                tasks = [
                    self._refresh_job_cache(job_id, semaphore)
                    for job_id in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if result is True:
                        refreshed_count += 1
                    elif isinstance(result, Exception):
                        logger.warning(f"Error refreshing cache: {result}")
                
                # Small delay between batches
                if i + self.batch_size < len(stale_jobs):
                    await asyncio.sleep(0.5)
            
            logger.info(f"Refreshed {refreshed_count}/{len(stale_jobs)} stale caches")
            return refreshed_count
            
        except Exception as e:
            logger.error(f"Error refreshing stale caches: {e}")
            return 0
    
    async def _warm_job_cache(self, job_id: str, semaphore: asyncio.Semaphore) -> bool:
        """
        Warm cache for a single job
        
        Args:
            job_id: The job ID to warm cache for
            semaphore: Semaphore to limit concurrent operations
            
        Returns:
            True if successful, False otherwise
        """
        async with semaphore:
            try:
                # Get statistics (this will cache them)
                statistics = await self.statistics_service.get_job_statistics(job_id)
                return statistics is not None
                
            except Exception as e:
                logger.warning(f"Error warming cache for job {job_id}: {e}")
                return False
    
    async def _refresh_job_cache(self, job_id: str, semaphore: asyncio.Semaphore) -> bool:
        """
        Refresh cache for a single job by invalidating and recalculating
        
        Args:
            job_id: The job ID to refresh cache for
            semaphore: Semaphore to limit concurrent operations
            
        Returns:
            True if successful, False otherwise
        """
        async with semaphore:
            try:
                # Invalidate existing cache
                await self.statistics_service.invalidate_job_statistics_cache(job_id)
                
                # Recalculate statistics (this will cache them)
                statistics = await self.statistics_service.get_job_statistics(job_id)
                return statistics is not None
                
            except Exception as e:
                logger.warning(f"Error refreshing cache for job {job_id}: {e}")
                return False
    
    async def _get_recent_active_jobs(self, limit: int) -> List[str]:
        """
        Get recent active jobs as a proxy for popular jobs
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job IDs
        """
        try:
            job_controller = get_controller('jobs_search')
            
            # This would need to be implemented in the job controller
            # For now, return empty list as placeholder
            # In a real implementation, this would query for recent active jobs
            # ordered by view count, application count, or posting date
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent active jobs: {e}")
            return []
    
    async def _get_company_active_jobs(self, company_id: str) -> List[str]:
        """
        Get all active jobs for a company
        
        Args:
            company_id: The company ID
            
        Returns:
            List of job IDs
        """
        try:
            # This would need to be implemented to query active jobs by company
            # For now, return empty list as placeholder
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting company active jobs: {e}")
            return []
    
    async def _get_jobs_with_stale_cache(self, max_age_hours: int) -> List[str]:
        """
        Get jobs with stale cache that need refreshing
        
        Args:
            max_age_hours: Maximum age in hours before cache is considered stale
            
        Returns:
            List of job IDs with stale cache
        """
        try:
            # This would require tracking cache timestamps in Redis
            # For now, return empty list as placeholder
            # In a real implementation, this would query Redis for cache keys
            # and check their timestamps
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting jobs with stale cache: {e}")
            return []
    
    async def warm_cache_for_job_list(self, job_ids: List[str]) -> int:
        """
        Warm cache for a specific list of jobs
        
        Args:
            job_ids: List of job IDs to warm cache for
            
        Returns:
            Number of jobs successfully cached
        """
        if not job_ids:
            return 0
        
        try:
            cached_count = 0
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            # Process jobs in batches
            for i in range(0, len(job_ids), self.batch_size):
                batch = job_ids[i:i + self.batch_size]
                
                tasks = [
                    self._warm_job_cache(job_id, semaphore)
                    for job_id in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if result is True:
                        cached_count += 1
                    elif isinstance(result, Exception):
                        logger.warning(f"Error warming cache: {result}")
                
                # Small delay between batches
                if i + self.batch_size < len(job_ids):
                    await asyncio.sleep(0.5)
            
            logger.info(f"Warmed cache for {cached_count}/{len(job_ids)} specified jobs")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error warming cache for job list: {e}")
            return 0


# Convenience functions for common cache warming operations

async def warm_popular_jobs_cache(limit: int = 50) -> int:
    """Convenience function to warm cache for popular jobs"""
    warmer = JobStatisticsCacheWarmer()
    return await warmer.warm_popular_jobs_cache(limit)


async def warm_company_jobs_cache(company_id: str) -> int:
    """Convenience function to warm cache for company jobs"""
    warmer = JobStatisticsCacheWarmer()
    return await warmer.warm_company_jobs_cache(company_id)


async def refresh_stale_cache(max_age_hours: int = 6) -> int:
    """Convenience function to refresh stale caches"""
    warmer = JobStatisticsCacheWarmer()
    return await warmer.refresh_stale_cache(max_age_hours)