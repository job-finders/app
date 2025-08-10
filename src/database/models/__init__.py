
from enum import Enum
class Role(str, Enum):
    ADMIN = "admin"
    EMPLOYER = "employer"
    SEEKER = "seeker"
    SYSTEM_ADMIN = "system_admin"



    @classmethod
    def is_valid_role(cls, role_str: str) -> bool:
        try:
            # Try to get the enum value, will raise ValueError if invalid
            cls(role_str)
            return True
        except ValueError:
            return False


from .admin_models import (
    UserStatusFlagEnum, RiskRecommendation, RiskThreshold, FlaggedUser, AdminModel
)
from .agent_models import (
    CVOptimizationSuggestion, CoverLetterOutput, JobMatchInsights, JobPostInsights, CandidateBenchmarkReport
)
from .billing import (
    BillingPlan, CompanyBillingProfile, InvoiceStatusEnum, Invoice, PaymentMethod, BillingEvent
)

from .company_ats import (
    KeywordSourceType, KeywordSource, SuggestionImpact, AIEnhancementSuggestion, ATSOptimisationInput,
    ATSOptimisationOutput, ATSScoreBreakdown, KeywordTool, AIATSReport
)

# Jobs Must Be Above
from .company_models import (
    CompanyVerificationStatus, Company, CompanyUpdate, AllowableCompanyVerificationDocumentsEnum,
    AIBasedDocumentReviewResult,
    CompanyVerificationDocument, DirectorDetails, CompanyCIPC, InterestLevel, CompanyFollowing, CandidateStatus,
    SavedCandidates,
    CompanySettings
)

from .config import (Configuration)

from .employer_models import (
    Employer
)
from .feedback_analysis import (
    ArticleFeedbackEntry, FeedbackAnalysisSummary, BlogFeedbackInput, BlogFeedbackOutput, BlogTopic
)

from .jobs_model import (
    JobApprovalStatusEnum, JobApprovalRequest, JobVersionHistory, JobStatusEnum, JobCategory, Job, JobEditableFields,
    SavedJob, ATSReport, JobApplicationStatusEnum, JobApplication, StatusCounts, ApplicationMetrics, JobStatistics,
    ApplicationFunnelStats, JobApplicationDashboard, TalentPoolReport, BulkImportResult, JobLike, JobShare,
    JobActionsState, ShareMethodEnum, JobActionRequest, JobLikeRequest, JobSaveRequest, JobShareRequest,
    JobActionsResponse
)

from .jobseeker_profile import (
    JobSeekerProfile
)

from .notifications import (
    NotificationChannel, NotificationType, NotificationPayload, BaseNotification
)

from .resume import (
    Experience, Education, Certification, Language, Publication, Project, Award, CustomSection, SavedCV, JobSeekerCV
)

from .users import (
    Roles, RolesEnum, User
)

from .seo import (SEO)

BillingPlan.model_rebuild()
CompanyBillingProfile.model_rebuild()
Company.model_rebuild()
JobSeekerCV.model_rebuild()
JobSeekerProfile.model_rebuild()
