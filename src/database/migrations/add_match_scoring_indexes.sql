-- Database indexes for job match scoring performance optimization
-- Run this migration to improve query performance for match scoring

-- Index for job queries with status filtering
CREATE INDEX IF NOT EXISTS idx_jobs_status_created_at 
ON jobs (status, created_at DESC);

-- Index for job queries with featured flag and status
CREATE INDEX IF NOT EXISTS idx_jobs_featured_status_updated_at 
ON jobs (is_featured DESC, status, updated_at DESC);

-- Index for job location searches
CREATE INDEX IF NOT EXISTS idx_jobs_location_status 
ON jobs (location, status);

-- Index for job category searches
CREATE INDEX IF NOT EXISTS idx_jobs_category_status 
ON jobs (category_id, status);

-- Index for job title searches (if using full-text search)
CREATE INDEX IF NOT EXISTS idx_jobs_title_status 
ON jobs (title, status);

-- Composite index for job search with multiple filters
CREATE INDEX IF NOT EXISTS idx_jobs_search_composite 
ON jobs (status, category_id, location, is_featured DESC, created_at DESC);

-- Index for user profile queries
CREATE INDEX IF NOT EXISTS idx_jobseeker_profiles_user_id 
ON jobseeker_profiles (user_id);

-- Index for user skills (if stored in separate table)
-- CREATE INDEX IF NOT EXISTS idx_user_skills_user_id 
-- ON user_skills (user_id);

-- Index for job skills (if stored in separate table)
-- CREATE INDEX IF NOT EXISTS idx_job_skills_job_id 
-- ON job_skills (job_id);

-- Index for job applications (for checking if user already applied)
CREATE INDEX IF NOT EXISTS idx_job_applications_user_job 
ON job_applications (user_id, job_id);

-- Index for caching match scores (if stored in database)
-- CREATE INDEX IF NOT EXISTS idx_match_scores_user_job_timestamp 
-- ON match_scores (user_id, job_id, calculated_at DESC);

-- Analyze tables to update statistics for query optimizer
ANALYZE jobs;
ANALYZE jobseeker_profiles;
ANALYZE job_applications;