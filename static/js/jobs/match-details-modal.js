/**
 * Job Match Details Modal Functionality
 * Handles modal interactions, AJAX requests, and data population
 */

class MatchDetailsModal {
    constructor() {
        this.modal = document.getElementById('matchDetailsModal');
        this.modalContent = this.modal?.querySelector('.match-details-modal');
        this.closeButton = this.modal?.querySelector('.modal-close');
        this.loadingSpinner = document.getElementById('modalLoadingSpinner');
        this.errorState = document.getElementById('modalErrorState');
        this.matchContent = document.getElementById('matchAnalysisContent');
        this.retryButton = document.getElementById('retryMatchAnalysis');
        
        this.currentJobId = null;
        this.currentJobSlug = null;
        this.isLoading = false;
        
        this.init();
    }

    init() {
        if (!this.modal) {
            console.warn('Match details modal not found in DOM');
            return;
        }

        this.bindEvents();
        this.setupNetworkStatusHandling();
    }

    setupNetworkStatusHandling() {
        const networkStatus = document.getElementById('networkStatus');
        
        window.addEventListener('online', () => {
            console.log('Network connection restored');

            if (networkStatus) {
                networkStatus.className = 'network-status online';
                networkStatus.querySelector('.status-text').textContent = 'Connection restored';
            }

            if (this.modal.classList.contains('active') && this.errorState.style.display === 'block') {
                const errorMessage = this.errorState.querySelector('.error-message');
                if (errorMessage && errorMessage.textContent.includes('offline')) {
                    this.showNetworkRestoredMessage();
                }
            }
        });

        window.addEventListener('offline', () => {
            console.log('Network connection lost');

            if (networkStatus) {
                networkStatus.className = 'network-status offline';
                networkStatus.querySelector('.status-text').textContent = 'You are offline';
            }

            if (this.isLoading) {
                this.showError('You appear to be offline. Please check your internet connection');
                this.hideLoading();
                this.isLoading = false;
            }
        });
    }

    showNetworkRestoredMessage() {
        const errorMessage = this.errorState.querySelector('.error-message');
        if (errorMessage) {
            errorMessage.textContent = 'Network connection restored. You can try again now.';
        }

        const retryButton = this.errorState.querySelector('#retryMatchAnalysis');
        if (retryButton) {
            retryButton.style.display = 'inline-block';
            retryButton.classList.add('btn-success');
            retryButton.innerHTML = '<i class="fas fa-wifi"></i> Connection Restored - Try Again';
        }
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-match-details')) {
                e.preventDefault();
                const button = e.target.closest('.btn-match-details');
                const jobId = button.dataset.jobId;
                const jobSlug = button.dataset.jobSlug;

                if (jobId) {
                    this.openModal(jobId, jobSlug);
                }
            }
        });

        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => this.closeModal());
        }

        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('active')) {
                this.closeModal();
            }
        });

        if (this.retryButton) {
            this.retryButton.addEventListener('click', () => {
                if (this.currentJobId) {
                    this.fetchMatchDetails(this.currentJobId, this.currentJobSlug);
                }
            });
        }
    }

    async openModal(jobId, jobSlug = null) {
        if (this.isLoading) return;

        this.currentJobId = jobId;
        this.currentJobSlug = jobSlug;

        // Show modal with proper visibility control
        this.modal.classList.add('active');
        this.modal.style.display = 'flex';
        document.body.classList.add('modal-open');

        console.log(`Opening match details modal for Job ID: ${jobId}, Slug: ${jobSlug}`);

        await this.fetchMatchDetails(jobId, jobSlug);
    }

    closeModal() {
        this.modal.classList.remove('active');
        document.body.classList.remove('modal-open');

        // Use timeout to allow transition to complete before hiding
        setTimeout(() => {
            if (!this.modal.classList.contains('active')) {
                this.modal.style.display = 'none';
            }
        }, 400);

        this.hideError();
        this.hideLoading();
        this.currentJobId = null;
        this.currentJobSlug = null;
    }

    async fetchMatchDetails(jobId, jobSlug = null) {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading();
        this.hideError();

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);

        try {
            const possibleEndpoints = [
                `/jobs/job-match-analysis/${jobId}`,
                `/api/jobs/job-match-analysis/${jobId}`,
                `job-match-analysis/${jobId}`
            ];

            let endpoint = possibleEndpoints[0];

            console.log('Current page URL:', window.location.href);
            console.log('Trying endpoint:', endpoint);

            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cache-Control': 'no-cache'
                },
                credentials: 'include',
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            console.log('Response status:', response.status);

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.error('Got HTML response instead of JSON - wrong endpoint or route issue');
                throw new Error('Server returned HTML instead of JSON. Check route configuration.');
            }

            const responseText = await response.text();
            console.log('Response body:', responseText);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${responseText}`);
            }

            const data = JSON.parse(responseText);

            if (data.success) {
                this.populateModalContent(data.match_analysis);
                this.hideLoading();
            } else {
                throw new Error(data.message || 'Failed to fetch match analysis');
            }

        } catch (error) {
            clearTimeout(timeoutId);
            console.error('Full error details:', error);

            let errorMessage = 'Failed to load match details. Please try again.';

            if (error.name === 'AbortError') {
                errorMessage = 'Request timed out. Please check your connection and try again.';
            } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                errorMessage = 'Network error. Please check your internet connection.';
            } else if (error.message.includes('HTML instead of JSON')) {
                errorMessage = 'Server configuration error. Please contact support.';
            }

            this.showError(errorMessage);
            this.hideLoading();
        } finally {
            this.isLoading = false;
        }
    }

    populateModalContent(matchData) {
        if (!this.matchContent) return;

        // Update overall score
        const scoreElement = this.matchContent.querySelector('#overallScoreNumber');
        if (scoreElement && matchData.total_score !== undefined) {
            scoreElement.textContent = `${Math.round(matchData.total_score)}%`;

            // Update SVG progress ring
            const progressRing = this.matchContent.querySelector('.progress-ring-progress');
            if (progressRing) {
                const circumference = 2 * Math.PI * 54; // radius = 54
                const strokeDashoffset = circumference - (matchData.total_score / 100) * circumference;
                progressRing.style.strokeDashoffset = strokeDashoffset;

                // Update color based on score
                const color = this.getScoreColor(matchData.total_score);
                progressRing.setAttribute('stroke', color);
            }
        }

        // Populate breakdown sections
        this.populateSkillsMatch(matchData.skills_match);
        this.populateExperienceMatch(matchData.experience_match);
        this.populateLocationMatch(matchData.location_match);
        this.populateSalaryMatch(matchData.salary_match);

        this.populateInterpretation(matchData.interpretation);
    }

    populateSkillsMatch(skillsData) {
        if (!skillsData) return;

        const skillsSection = this.matchContent.querySelector('[data-category="skills"]');
        if (!skillsSection) return;

        // Update category score
        const categoryPercentage = skillsSection.querySelector('.category-percentage');
        if (categoryPercentage) {
            categoryPercentage.textContent = `${Math.round(skillsData.score)}%`;
        }

        // Update progress bar
        const progressBar = skillsSection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${skillsData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(skillsData.score);
        }

        // Populate matched skills
        const matchedSkillsContainer = skillsSection.querySelector('.skill-tags.matched');
        if (matchedSkillsContainer && skillsData.matched_skills) {
            matchedSkillsContainer.innerHTML = skillsData.matched_skills
                .map(skill => `<span class="skill-tag">${skill}</span>`)
                .join('');
        }

        // Populate missing skills
        const missingSkillsContainer = skillsSection.querySelector('.skill-tags.missing');
        if (missingSkillsContainer && skillsData.missing_skills) {
            missingSkillsContainer.innerHTML = skillsData.missing_skills
                .map(skill => `<span class="skill-tag">${skill}</span>`)
                .join('');
        }

        // Add explanation
        const explanation = skillsSection.querySelector('.category-explanation p');
        if (explanation && skillsData.explanation) {
            explanation.textContent = skillsData.explanation;
        }
    }

    populateExperienceMatch(experienceData) {
        if (!experienceData) return;

        const experienceSection = this.matchContent.querySelector('[data-category="experience"]');
        if (!experienceSection) return;

        const categoryPercentage = experienceSection.querySelector('.category-percentage');
        if (categoryPercentage) {
            categoryPercentage.textContent = `${Math.round(experienceData.score)}%`;
        }

        const progressBar = experienceSection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${experienceData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(experienceData.score);
        }

        const experienceDetails = experienceSection.querySelector('.experience-details');
        if (experienceDetails && experienceData.details) {
            experienceDetails.innerHTML = `
                <div class="category-detail-section">
                    <div class="detail-label">Required Experience:</div>
                    <div class="detail-value">${experienceData.details.required_years || 'Not specified'} years</div>
                </div>
                <div class="category-detail-section">
                    <div class="detail-label">Your Experience:</div>
                    <div class="detail-value">${experienceData.details.user_years || 'Not specified'} years</div>
                </div>
                <div class="category-detail-section">
                    <div class="detail-label">Industry Match:</div>
                    <div class="detail-value">${experienceData.details.industry_match || 'Not specified'}</div>
                </div>
            `;
        }

        const explanation = experienceSection.querySelector('.category-explanation p');
        if (explanation && experienceData.explanation) {
            explanation.textContent = experienceData.explanation;
        }
    }

    populateLocationMatch(locationData) {
        if (!locationData) return;

        const locationSection = this.matchContent.querySelector('[data-category="location"]');
        if (!locationSection) return;

        const categoryPercentage = locationSection.querySelector('.category-percentage');
        if (categoryPercentage) {
            categoryPercentage.textContent = `${Math.round(locationData.score)}%`;
        }

        const progressBar = locationSection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${locationData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(locationData.score);
        }

        const locationDetails = locationSection.querySelector('.location-details');
        if (locationDetails && locationData.details) {
            locationDetails.innerHTML = `
                <div class="category-detail-section">
                    <div class="detail-label">Job Location:</div>
                    <div class="detail-value">${locationData.details.job_location || 'Not specified'}</div>
                </div>
                <div class="category-detail-section">
                    <div class="detail-label">Your Location:</div>
                    <div class="detail-value">${locationData.details.user_location || 'Not specified'}</div>
                </div>
                <div class="category-detail-section">
                    <div class="detail-label">Remote Work:</div>
                    <div class="detail-value">${locationData.details.remote_option || 'Not specified'}</div>
                </div>
            `;
        }

        const explanation = locationSection.querySelector('.category-explanation p');
        if (explanation && locationData.explanation) {
            explanation.textContent = locationData.explanation;
        }
    }

    populateSalaryMatch(salaryData) {
        if (!salaryData) return;

        const salarySection = this.matchContent.querySelector('[data-category="salary"]');
        if (!salarySection) return;

        const categoryPercentage = salarySection.querySelector('.category-percentage');
        if (categoryPercentage) {
            categoryPercentage.textContent = `${Math.round(salaryData.score)}%`;
        }

        const progressBar = salarySection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${salaryData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(salaryData.score);
        }

        const salaryDetails = salarySection.querySelector('.salary-details');
        if (salaryDetails && salaryData.details) {
            salaryDetails.innerHTML = `
                <div class="category-detail-section">
                    <div class="detail-label">Offered Range:</div>
                    <div class="detail-value">${salaryData.details.offered_range || 'Not specified'}</div>
                </div>
                <div class="category-detail-section">
                    <div class="detail-label">Your Expectation:</div>
                    <div class="detail-value">${salaryData.details.expected_range || 'Not specified'}</div>
                </div>
                <div class="category-detail-section">
                    <div class="detail-label">Match Level:</div>
                    <div class="detail-value">${salaryData.details.match_level || 'Not specified'}</div>
                </div>
            `;
        }

        const explanation = salarySection.querySelector('.category-explanation p');
        if (explanation && salaryData.explanation) {
            explanation.textContent = salaryData.explanation;
        }
    }

    populateInterpretation(interpretation) {
        const interpretationSection = this.matchContent.querySelector('.match-interpretation');
        if (interpretationSection && interpretation) {
            interpretationSection.innerHTML = `
                <div class="match-explanation">
                    <strong>Match Analysis:</strong> ${interpretation}
                </div>
            `;
        }
    }

    getScoreColor(score) {
        if (score >= 80) return '#10b981'; // success color
        if (score >= 60) return '#f59e0b'; // warning color
        return '#ef4444'; // danger color
    }

    getScoreClass(score) {
        if (score >= 80) return 'high-score';
        if (score >= 60) return 'medium-score';
        return 'low-score';
    }

    showLoading() {
        if (this.loadingSpinner) {
            this.loadingSpinner.style.display = 'flex';
        }
        if (this.matchContent) {
            this.matchContent.style.display = 'none';
        }
    }

    hideLoading() {
        if (this.loadingSpinner) {
            this.loadingSpinner.style.display = 'none';
        }
        if (this.matchContent) {
            this.matchContent.style.display = 'block';
        }
    }

    showError(message) {
        if (this.errorState) {
            this.errorState.style.display = 'block';
            const errorMessage = this.errorState.querySelector('.error-message');
            const errorTitle = this.errorState.querySelector('.error-title');
            const retryButton = this.errorState.querySelector('#retryMatchAnalysis');

            if (errorMessage) {
                errorMessage.textContent = message || 'Failed to load match details. Please try again.';
            }

            if (message && message.includes('complete your profile')) {
                if (errorTitle) {
                    errorTitle.textContent = 'Profile Incomplete';
                }
                if (retryButton) {
                    retryButton.style.display = 'none';
                }
                this.addProfileCompletionButton();
            } else if (message && message.includes('log in')) {
                if (errorTitle) {
                    errorTitle.textContent = 'Login Required';
                }
                if (retryButton) {
                    retryButton.style.display = 'none';
                }
                this.addLoginButton();
            } else {
                if (errorTitle) {
                    errorTitle.textContent = 'Unable to Load Match Details';
                }
                if (retryButton) {
                    retryButton.style.display = 'inline-block';
                }
            }
        }
        if (this.matchContent) {
            this.matchContent.style.display = 'none';
        }
    }

    addProfileCompletionButton() {
        const errorState = this.errorState;
        if (!errorState) return;
        
        let profileButton = errorState.querySelector('.btn-complete-profile-modal');
        if (!profileButton) {
            profileButton = document.createElement('a');
            profileButton.className = 'btn btn-primary btn-complete-profile-modal';
            profileButton.href = '/jobseekers/profile';
            profileButton.innerHTML = '<i class="fas fa-user-edit"></i> Complete Your Profile';
            
            const retryButton = errorState.querySelector('#retryMatchAnalysis');
            if (retryButton) {
                retryButton.parentNode.insertBefore(profileButton, retryButton);
            } else {
                errorState.appendChild(profileButton);
            }
        }
    }

    addLoginButton() {
        const errorState = this.errorState;
        if (!errorState) return;
        
        let loginButton = errorState.querySelector('.btn-login-modal');
        if (!loginButton) {
            loginButton = document.createElement('a');
            loginButton.className = 'btn btn-primary btn-login-modal';
            loginButton.href = '/auth/login';
            loginButton.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login to Continue';
            
            const retryButton = errorState.querySelector('#retryMatchAnalysis');
            if (retryButton) {
                retryButton.parentNode.insertBefore(loginButton, retryButton);
            } else {
                errorState.appendChild(loginButton);
            }
        }
    }
    hideError() {
        if (this.errorState) {
            this.errorState.style.display = 'none';
        }
    }
}

// Initialize modal when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.matchDetailsModal = new MatchDetailsModal();
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MatchDetailsModal;
}