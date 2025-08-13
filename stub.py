# Fix 1: SQL Query - Use filter() instead of filter_by() for complex conditions
@error_handler
async def get_applied_jobs_for_user(self, user_id: str, page: int = 1, page_size: int = 20) -> tuple[
    list[JobApplication], int]:
    """Get job applications with full job details for a user with pagination"""
    try:
        if not (isinstance(user_id, str) and user_id.strip()):
            self.logger.error("Invalid User ID")
            return [], 0

        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(page_size, int) or page_size < 1:
            page_size = 20

        with self.get_session() as session:
            # Fix: Use filter() instead of filter_by() for proper parameter binding
            total_count = (
                session.query(JobApplicationORM)
                .filter(JobApplicationORM.user_id == user_id)
                .join(JobApplicationORM.job)
                .count()
            )

            offset = (page - 1) * page_size
            job_applications_orm_list = (
                session.query(JobApplicationORM)
                .filter(JobApplicationORM.user_id == user_id)
                .options(joinedload(JobApplicationORM.job))
                .join(JobApplicationORM.job)
                .order_by(JobApplicationORM.applied_date.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            applications = [
                JobApplication(**app.to_dict(include_relationships=True))
                for app in job_applications_orm_list
            ] if job_applications_orm_list else []

            return applications, total_count
            
    except Exception as e:
        self.logger.error(f"Error getting applied jobs for user {user_id}: {str(e)}")
        return [], 0


# Fix 2: User Profile - Add null check before accessing attributes
async def dashboard(user: User):
    """Dashboard route with dynamic statistics from database"""
    try:
        # Validate user object
        if not user or not hasattr(user, 'uid'):
            self.logger.error("Invalid user object")
            return redirect(url_for('auth.login'))
        
        # Get controllers
        resume_controller = get_controller('resume')
        jobs_search_controller = get_controller('jobs_search')
        
        # Get user CVs
        user_cvs = await resume_controller.list_cvs_for_user(user_uid=user.uid)
        
        # Get dashboard statistics with error handling
        try:
            dashboard_stats = await jobs_search_controller.get_user_dashboard_statistics(user.uid)
        except Exception as e:
            self.logger.error(f"Error fetching dashboard stats: {str(e)}")
            dashboard_stats = {}
        
        # Get saved jobs with error handling
        try:
            saved_jobs = await jobs_search_controller.get_saved_jobs_for_user(user.uid)
            recent_saved_jobs = saved_jobs[:5] if saved_jobs else []
        except Exception as e:
            self.logger.error(f"Error fetching saved jobs: {str(e)}")
            recent_saved_jobs = []
        
        # Safe access to user attributes
        seeker_stats = {
            'count': len(user_cvs) if user_cvs else 0,
            'cv_uploaded': dashboard_stats.get('cv_uploaded', False),
            'cv_count': dashboard_stats.get('cv_count', 0),
            'applications_count': dashboard_stats.get('applications_count', 0),
            'saved_jobs_count': dashboard_stats.get('saved_jobs_count', 0),
            'recent_applications_count': dashboard_stats.get('recent_applications_count', 0),
            'saved_jobs': recent_saved_jobs
        }
        
        context = dict(current_user=user, seeker_stats=seeker_stats)
        return render_template("jobseekers/dashboard.html", **context)
        
    except Exception as e:
        self.logger.error(f"Dashboard error: {str(e)}")
        return redirect(url_for('auth.login'))


# Fix 3: User profile fetching method - add null checks
async def get_user_profile(self, user_id: str):
    """Get user profile with null checking"""
    try:
        with self.get_session() as session:
            user = session.query(UserORM).filter(UserORM.uid == user_id).first()
            
            if not user:
                self.logger.warning(f"No user found with ID: {user_id}")
                return None
                
            # Safe attribute access
            profile_data = {
                'uid': user.uid,
                'first_name': getattr(user, 'first_name', ''),
                'last_name': getattr(user, 'last_name', ''),
                'email': getattr(user, 'email', ''),
                # Add other fields as needed
            }
            
            return profile_data
            
    except Exception as e:
        self.logger.error(f"Error fetching user profile {user_id}: {str(e)}")
        return None