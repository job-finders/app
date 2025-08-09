# Design Document

## Overview

The job match scoring feature will integrate AI-powered matching capabilities into the job listings interface. The system will calculate match scores using existing controller methods and present them through a modern, card-based UI with detailed modal dialogs for score breakdowns.

## Architecture

### Component Structure
```
Job Listings Page
├── Job Cards (with match scores)
├── Match Details Modal
├── Styling System (job-listings.css)
└── JavaScript Interactions
```

### Data Flow
```
User Profile + Job Data → Match Calculation → Score Display → Detail Modal
```

## Components and Interfaces

### 1. Job Match Score Calculation

**Two-Tier Approach:**

#### A. Quick Match Score (for Job Listings)
**Location:** New method `calculate_quick_match_score()` in `JobsSearchController`

**Interface:**
```python
async def calculate_quick_match_score(self, job: Job, user_profile: JobSeekerProfile) -> float:
    """
    Calculate lightweight match score for job listings
    Uses basic criteria without expensive AI operations
    Returns: float (0-100)
    """
```

**Quick Scoring Algorithm (Non-AI):**
- Location Match (40%): Exact city/province match or remote compatibility
- Job Title Keywords (30%): Simple keyword matching in job titles
- Experience Level (20%): Basic experience level comparison (entry/mid/senior)
- Industry Category (10%): Direct category matching

#### B. Detailed Match Analysis (for Modal Dialog)
**Location:** Use existing `calculate_job_match_score()` method

**Interface:** Already exists in `JobsSearchController`
```python
async def calculate_job_match_score(self, job_id: str, user_id: str) -> dict:
    """
    Comprehensive job match analysis with detailed breakdown
    Returns: {
        'score_breakdown': dict,  # Skills, experience, education, etc.
        'interpretation': str,
        'recommended_improvements': list
    }
    """
```

**Detailed Scoring (Existing Implementation):**
- Skills Match (30%): Set intersection of required/preferred skills
- Experience Level (20%): Experience level compatibility
- Education Match (15%): Qualification requirements matching
- Industry Interest (10%): Category alignment with user interests
- Job Title Interest (10%): Title matching with user preferences
- Location Compatibility (10%): Location and remote work preferences
- Remote Preference (5%): Remote work policy alignment

### 2. Enhanced Job Listing Template

**Template:** `template/jobs/job_listing.html`

**Structure:**
```html
<div class="job-listings-container">
    <div class="job-card" data-job-id="{{ job.job_id }}">
        <div class="job-card-header">
            <div class="company-info">
                <img src="{{ job.company.logo }}" class="company-logo">
                <div class="company-details">
                    <h3 class="job-title">{{ job.title }}</h3>
                    <p class="company-name">{{ job.company.name }}</p>
                </div>
            </div>
            <div class="match-score-badge" data-score="{{ match_data.total_score }}">
                <span class="score-percentage">{{ match_data.total_score }}%</span>
                <span class="score-label">Match</span>
            </div>
        </div>
        <div class="job-card-body">
            <div class="job-meta">
                <span class="location">{{ job.location }}</span>
                <span class="salary">{{ job.salary_range }}</span>
                <span class="job-type">{{ job.position_type }}</span>
            </div>
            <p class="job-description">{{ job.description | truncate(150) }}</p>
        </div>
        <div class="job-card-footer">
            <button class="btn-apply">Apply Now</button>
            <button class="btn-match-details" data-job-id="{{ job.job_id }}">
                <i class="fas fa-chart-line"></i> Match Details
            </button>
        </div>
    </div>
</div>
```

### 3. Match Details Modal

**Structure:**
```html
<div id="matchDetailsModal" class="modal-overlay">
    <div class="modal-content match-details-modal">
        <div class="modal-header">
            <h2>Job Match Analysis</h2>
            <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
            <div class="overall-score">
                <div class="score-circle">
                    <span class="score-number">85%</span>
                </div>
                <h3>Overall Match Score</h3>
            </div>
            
            <div class="match-breakdown">
                <div class="match-category">
                    <div class="category-header">
                        <h4>Skills Match</h4>
                        <span class="category-score">90%</span>
                    </div>
                    <div class="category-details">
                        <div class="matched-skills">
                            <h5>Matched Skills</h5>
                            <div class="skill-tags">
                                <!-- Dynamic skill tags -->
                            </div>
                        </div>
                        <div class="missing-skills">
                            <h5>Skills to Develop</h5>
                            <div class="skill-tags missing">
                                <!-- Dynamic missing skill tags -->
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Similar structure for Experience, Location, Salary -->
            </div>
        </div>
    </div>
</div>
```

## Data Models

### Match Score Data Structure
```python
@dataclass
class JobMatchScore:
    total_score: float
    skill_match: SkillMatchDetails
    experience_match: ExperienceMatchDetails
    location_match: LocationMatchDetails
    salary_match: SalaryMatchDetails

@dataclass
class SkillMatchDetails:
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    skill_gaps: List[str]
    relevance_explanation: str
```

## Error Handling

### Score Calculation Errors
- **No User Profile:** Display "Complete your profile for personalized match scores"
- **Incomplete Job Data:** Use available data and note limitations
- **Calculation Timeout:** Fall back to basic matching algorithm
- **API Failures:** Cache previous calculations and display with timestamp

### UI Error States
- **Modal Loading Errors:** Show error message with retry option
- **Network Failures:** Graceful degradation with cached data
- **Invalid Job Data:** Hide match score and show generic job card

## Testing Strategy

### Unit Tests
- Match score calculation accuracy
- Individual scoring component tests
- Error handling scenarios
- Data validation tests

### Integration Tests
- End-to-end job listing with scores
- Modal functionality across browsers
- Responsive design testing
- Performance testing with large job lists

### User Acceptance Tests
- Job seeker workflow testing
- Match score accuracy validation
- UI/UX usability testing
- Cross-device compatibility testing

## Performance Considerations

### Optimization Strategies
- **Two-Tier Architecture:** Use lightweight quick scoring for listings, detailed analysis only for modals
- **Batch Quick Scoring:** Calculate quick scores for all visible jobs in single request
- **Caching:** Cache quick scores for 30 minutes, detailed scores for 1 hour
- **Lazy Loading:** Load detailed match analysis only when modal is opened
- **Progressive Enhancement:** Show basic job cards first, then add quick scores, detailed analysis on demand

### Monitoring
- Track match score calculation time
- Monitor modal open/close rates
- Measure job application conversion rates
- Track user engagement with match details