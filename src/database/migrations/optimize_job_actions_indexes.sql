-- Job Actions Database Optimization Script
-- This script creates optimized indexes for job actions tables
-- Run this after the main migration to ensure optimal query performance

-- ============================================================================
-- JOB LIKES TABLE OPTIMIZATIONS
-- ============================================================================

-- Primary composite index for user-job like lookups (most frequent query)
CREATE INDEX IF NOT EXISTS ix_job_likes_user_job_optimized
    ON job_likes(user_id, job_id, created_at DESC);

-- Index for job popularity analytics (like counts, trending jobs)
CREATE INDEX IF NOT EXISTS ix_job_likes_job_popularity
    ON job_likes(job_id, created_at DESC)
    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Index for user engagement analytics
CREATE INDEX IF NOT EXISTS ix_job_likes_user_activity
    ON job_likes(user_id, created_at DESC);

-- Index for recent likes (for activity feeds)
CREATE INDEX IF NOT EXISTS ix_job_likes_recent
    ON job_likes(created_at DESC)
    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY);

-- Covering index for like count queries (includes all needed columns)
CREATE INDEX IF NOT EXISTS ix_job_likes_covering
    ON job_likes(job_id, user_id, created_at, like_id);

-- ============================================================================
-- JOB SHARES TABLE OPTIMIZATIONS  
-- ============================================================================

-- Primary composite index for job-method analytics
CREATE INDEX IF NOT EXISTS ix_job_shares_job_method_optimized
    ON job_shares(job_id, share_method, shared_at DESC);

-- Index for share conversion tracking (referral analysis)
CREATE INDEX IF NOT EXISTS ix_job_shares_referral_tracking
    ON job_shares(referral_code, shared_at DESC)
    WHERE referral_code IS NOT NULL;

-- Index for user sharing behavior analytics
CREATE INDEX IF NOT EXISTS ix_job_shares_user_behavior
    ON job_shares(user_id, share_method, shared_at DESC)
    WHERE user_id IS NOT NULL;

-- Index for platform-specific analytics
CREATE INDEX IF NOT EXISTS ix_job_shares_platform_analytics
    ON job_shares(share_method, shared_at DESC, job_id);

-- Index for viral content identification (jobs with high share counts)
CREATE INDEX IF NOT EXISTS ix_job_shares_viral_content
    ON job_shares(job_id, shared_at DESC)
    WHERE shared_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);

-- Index for anonymous vs authenticated sharing analysis
CREATE INDEX IF NOT EXISTS ix_job_shares_auth_analysis
    ON job_shares(user_id IS NOT NULL, share_method, shared_at DESC);

-- Covering index for share statistics (includes all needed columns)
CREATE INDEX IF NOT EXISTS ix_job_shares_covering
    ON job_shares(job_id, share_method, shared_at, user_id, referral_code);

-- ============================================================================
-- CROSS-TABLE ANALYTICS OPTIMIZATIONS
-- ============================================================================

-- Optimize jobs table for action-related queries
CREATE INDEX IF NOT EXISTS ix_jobs_actions_analytics
    ON jobs(job_id, created_at DESC, status, is_featured)
    WHERE status = 'active';

-- Optimize jobseeker_profiles for action-related queries  
CREATE INDEX IF NOT EXISTS ix_jobseeker_actions_analytics
    ON jobseeker_profiles(user_uid, alerts_enabled, visibility)
    WHERE alerts_enabled = TRUE AND visibility = TRUE;

-- ============================================================================
-- PERFORMANCE MONITORING VIEWS
-- ============================================================================

-- Create view for job engagement metrics
CREATE OR REPLACE VIEW job_engagement_metrics AS
SELECT j.job_id,
       j.title,
       j.company_id,
       j.created_at                                                                as job_posted_at,
       COALESCE(like_stats.like_count, 0)                                          as like_count,
       COALESCE(share_stats.share_count, 0)                                        as share_count,
       COALESCE(like_stats.unique_likers, 0)                                       as unique_likers,
       COALESCE(share_stats.unique_sharers, 0)                                     as unique_sharers,
       COALESCE(share_stats.platform_diversity, 0)                                 as platform_diversity,
       (COALESCE(like_stats.like_count, 0) + COALESCE(share_stats.share_count, 0)) as total_engagement
FROM jobs j
         LEFT JOIN (SELECT job_id,
                           COUNT(*)                as like_count,
                           COUNT(DISTINCT user_id) as unique_likers
                    FROM job_likes
                    GROUP BY job_id) like_stats ON j.job_id = like_stats.job_id
         LEFT JOIN (SELECT job_id,
                           COUNT(*)                     as share_count,
                           COUNT(DISTINCT user_id)      as unique_sharers,
                           COUNT(DISTINCT share_method) as platform_diversity
                    FROM job_shares
                    GROUP BY job_id) share_stats ON j.job_id = share_stats.job_id;

-- Create view for user engagement analytics
CREATE OR REPLACE VIEW user_engagement_analytics AS
SELECT jsp.user_uid,
       jsp.first_name,
       jsp.last_name,
       COALESCE(like_stats.likes_given, 0)                                          as likes_given,
       COALESCE(share_stats.shares_made, 0)                                         as shares_made,
       COALESCE(like_stats.last_like_date, NULL)                                    as last_like_date,
       COALESCE(share_stats.last_share_date, NULL)                                  as last_share_date,
       COALESCE(share_stats.favorite_platform, NULL)                                as favorite_share_platform,
       (COALESCE(like_stats.likes_given, 0) + COALESCE(share_stats.shares_made, 0)) as total_actions
FROM jobseeker_profiles jsp
         LEFT JOIN (SELECT user_id,
                           COUNT(*)        as likes_given,
                           MAX(created_at) as last_like_date
                    FROM job_likes
                    GROUP BY user_id) like_stats ON jsp.user_uid = like_stats.user_id
         LEFT JOIN (SELECT user_id,
                           COUNT(*)       as shares_made,
                           MAX(shared_at) as last_share_date,
                           (SELECT share_method
                            FROM job_shares js2
                            WHERE js2.user_id = js1.user_id
                            GROUP BY share_method
                            ORDER BY COUNT(*) DESC
                            LIMIT 1)      as favorite_platform
                    FROM job_shares js1
                    WHERE user_id IS NOT NULL
                    GROUP BY user_id) share_stats ON jsp.user_uid = share_stats.user_id;

-- ============================================================================
-- MAINTENANCE AND CLEANUP
-- ============================================================================

-- Create procedure for cleaning up old analytics data
DELIMITER //
CREATE PROCEDURE CleanupOldJobActions(IN days_to_keep INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
        BEGIN
            ROLLBACK;
            RESIGNAL;
        END;

    START TRANSACTION;

    -- Archive old likes (older than specified days) to archive table if needed
    -- For now, we'll just delete very old data (older than 2 years by default)
    SET @cutoff_date = DATE_SUB(NOW(), INTERVAL IFNULL(days_to_keep, 730) DAY);

    -- Delete old job likes
    DELETE
    FROM job_likes
    WHERE created_at < @cutoff_date;

    -- Delete old job shares  
    DELETE
    FROM job_shares
    WHERE shared_at < @cutoff_date;
    COMMIT;

    SELECT CONCAT('Cleaned up job actions data older than ', days_to_keep, ' days') as result;
END //
DELIMITER ;

-- ============================================================================
-- PERFORMANCE ANALYSIS QUERIES
-- ============================================================================

-- Query to analyze index usage (run periodically to monitor performance)
-- SELECT 
--     TABLE_NAME,
--     INDEX_NAME,
--     CARDINALITY,
--     SUB_PART,
--     PACKED,
--     NULLABLE,
--     INDEX_TYPE
-- FROM information_schema.STATISTICS 
-- WHERE TABLE_SCHEMA = DATABASE() 
--   AND TABLE_NAME IN ('job_likes', 'job_shares')
-- ORDER BY TABLE_NAME, INDEX_NAME;

-- Query to find slow queries related to job actions
-- SELECT 
--     query_time,
--     lock_time,
--     rows_sent,
--     rows_examined,
--     sql_text
-- FROM mysql.slow_log 
-- WHERE sql_text LIKE '%job_likes%' 
--    OR sql_text LIKE '%job_shares%'
-- ORDER BY query_time DESC 
-- LIMIT 10;

-- ============================================================================
-- NOTES FOR DEVELOPERS
-- ============================================================================

/*
PERFORMANCE TIPS:

1. Use covering indexes when possible to avoid table lookups
2. Consider partitioning tables by date if data volume grows large
3. Monitor query performance regularly using EXPLAIN
4. Update table statistics regularly: ANALYZE TABLE job_likes, job_shares;
5. Consider read replicas for analytics queries if load is high

MAINTENANCE SCHEDULE:
- Run ANALYZE TABLE monthly
- Run CleanupOldJobActions() quarterly  
- Monitor index usage monthly
- Review slow query log weekly

INDEX USAGE PATTERNS:
- ix_job_likes_user_job_optimized: User checking if they liked a job
- ix_job_likes_job_popularity: Calculating like counts for job listings
- ix_job_shares_referral_tracking: Tracking conversion from shared links
- ix_job_shares_platform_analytics: Analyzing which platforms drive most shares

QUERY OPTIMIZATION:
- Always include job_id or user_id in WHERE clauses when possible
- Use LIMIT when fetching recent activities
- Consider using EXISTS instead of COUNT(*) for boolean checks
- Use appropriate date ranges to leverage partial indexes
*/