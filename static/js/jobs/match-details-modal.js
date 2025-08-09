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
        
        // Handle online/offline events
        window.addEventListener('online', () => {
            console.log('Network connection restored');
            
            // Show network restored indicator
            if (networkStatus) {
                networkStatus.className = 'network-status online';
                networkStatus.querySelector('.status-text').textContent = 'Connection restored';
            }
            
            if (this.modal.classList.contains('active') && this.errorState.style.display === 'block') {
                // If modal is open and showing error, offer to retry
                const errorMessage = this.errorState.querySelector('.error-message');
                if (errorMessage && errorMessage.textContent.includes('offline')) {
                    this.showNetworkRestoredMessage();
                }
            }
        });

        window.addEventListener('offline', () => {
            console.log('Network connection lost');
            
            // Show offline indicator
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
        // Bind match details button clicks
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

        // Close modal events
        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => this.closeModal());
        }

        // Close on overlay click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });

        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('active')) {
                this.closeModal();
            }
        });

        // Retry button
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
        
        // Show modal
        this.modal.classList.add('active');
        document.body.classList.add('modal-open');
        
        // Fetch and display match details
        await this.fetchMatchDetails(jobId, jobSlug);
    }

    closeModal() {
        this.modal.classList.remove('active');
        document.body.classList.remove('modal-open');
        
        // Reset states
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

        // Set timeout for the request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

        try {
            // Construct API endpoint
            const endpoint = jobSlug 
                ? `/api/jobs/${jobSlug}/match-analysis`
                : `/api/jobs/${jobId}/match-analysis`;

            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                let errorMessage = 'Failed to load match details';
                
                if (response.status === 401) {
                    errorMessage = 'Please log in to view match details';
                } else if (response.status === 404) {
                    errorMessage = 'Job not found or no longer available';
                } else if (response.status === 400) {
                    errorMessage = 'Please complete your profile to view match analysis';
                } else if (response.status >= 500) {
                    errorMessage = 'Server error. Please try again later';
                } else if (response.status === 429) {
                    errorMessage = 'Too many requests. Please wait a moment and try again';
                }
                
                throw new Error(errorMessage);
            }

            const data = await response.json();
            
            if (data.success) {
                this.populateModalContent(data.match_analysis);
                this.hideLoading();
            } else {
                throw new Error(data.message || 'Failed to fetch match analysis');
            }

        } catch (error) {
            clearTimeout(timeoutId);
            console.error('Error fetching match details:', error);
            
            let userFriendlyMessage = error.message;
            
            if (error.name === 'AbortError') {
                userFriendlyMessage = 'Request timed out. Please check your connection and try again';
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                userFriendlyMessage = 'Network error. Please check your internet connection';
            } else if (!navigator.onLine) {
                userFriendlyMessage = 'You appear to be offline. Please check your internet connection';
            }
            
            this.showError(userFriendlyMessage);
            this.hideLoading();
        } finally {
            this.isLoading = false;
        }
    }

    populateModalContent(matchData) {
        if (!this.matchContent) return;

        // Update overall score
        const scoreElement = this.matchContent.querySelector('.score-number');
        if (scoreElement && matchData.total_score !== undefined) {
            scoreElement.textContent = `${Math.round(matchData.total_score)}%`;
            
            // Update score circle color based on score
            const scoreCircle = scoreElement.closest('.score-circle');
            if (scoreCircle) {
                scoreCircle.className = 'score-circle ' + this.getScoreClass(matchData.total_score);
            }
        }

        // Update job title and company
        const jobTitle = this.matchContent.querySelector('.job-title');
        const companyName = this.matchContent.querySelector('.company-name');
        
        if (jobTitle && matchData.job_title) {
            jobTitle.textContent = matchData.job_title;
        }
        if (companyName && matchData.company_name) {
            companyName.textContent = matchData.company_name;
        }

        // Populate match breakdown sections
        this.populateSkillsMatch(matchData.skills_match);
        this.populateExperienceMatch(matchData.experience_match);
        this.populateLocationMatch(matchData.location_match);
        this.populateSalaryMatch(matchData.salary_match);

        // Show interpretation if available
        this.populateInterpretation(matchData.interpretation);
    }

    populateSkillsMatch(skillsData) {
        if (!skillsData) return;

        const skillsSection = this.matchContent.querySelector('[data-category="skills"]');
        if (!skillsSection) return;

        // Update category score
        const categoryScore = skillsSection.querySelector('.category-score');
        if (categoryScore) {
            categoryScore.textContent = `${Math.round(skillsData.score)}%`;
        }

        // Update progress bar
        const progressBar = skillsSection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${skillsData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(skillsData.score);
        }

        // Populate matched skills
        const matchedSkillsContainer = skillsSection.querySelector('.matched-skills .skill-tags');
        if (matchedSkillsContainer && skillsData.matched_skills) {
            matchedSkillsContainer.innerHTML = skillsData.matched_skills
                .map(skill => `<span class="skill-tag matched">${skill}</span>`)
                .join('');
        }

        // Populate missing skills
        const missingSkillsContainer = skillsSection.querySelector('.missing-skills .skill-tags');
        if (missingSkillsContainer && skillsData.missing_skills) {
            missingSkillsContainer.innerHTML = skillsData.missing_skills
                .map(skill => `<span class="skill-tag missing">${skill}</span>`)
                .join('');
        }

        // Add explanation if available
        const explanation = skillsSection.querySelector('.category-explanation');
        if (explanation && skillsData.explanation) {
            explanation.textContent = skillsData.explanation;
        }
    }

    populateExperienceMatch(experienceData) {
        if (!experienceData) return;

        const experienceSection = this.matchContent.querySelector('[data-category="experience"]');
        if (!experienceSection) return;

        // Update category score
        const categoryScore = experienceSection.querySelector('.category-score');
        if (categoryScore) {
            categoryScore.textContent = `${Math.round(experienceData.score)}%`;
        }

        // Update progress bar
        const progressBar = experienceSection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${experienceData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(experienceData.score);
        }

        // Update experience details
        const experienceDetails = experienceSection.querySelector('.experience-details');
        if (experienceDetails && experienceData.details) {
            experienceDetails.innerHTML = `
                <div class="experience-item">
                    <span class="label">Required Experience:</span>
                    <span class="value">${experienceData.details.required_years || 'Not specified'} years</span>
                </div>
                <div class="experience-item">
                    <span class="label">Your Experience:</span>
                    <span class="value">${experienceData.details.user_years || 'Not specified'} years</span>
                </div>
                <div class="experience-item">
                    <span class="label">Industry Match:</span>
                    <span class="value">${experienceData.details.industry_match || 'Not specified'}</span>
                </div>
            `;
        }

        // Add explanation if available
        const explanation = experienceSection.querySelector('.category-explanation');
        if (explanation && experienceData.explanation) {
            explanation.textContent = experienceData.explanation;
        }
    }

    populateLocationMatch(locationData) {
        if (!locationData) return;

        const locationSection = this.matchContent.querySelector('[data-category="location"]');
        if (!locationSection) return;

        // Update category score
        const categoryScore = locationSection.querySelector('.category-score');
        if (categoryScore) {
            categoryScore.textContent = `${Math.round(locationData.score)}%`;
        }

        // Update progress bar
        const progressBar = locationSection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${locationData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(locationData.score);
        }

        // Update location details
        const locationDetails = locationSection.querySelector('.location-details');
        if (locationDetails && locationData.details) {
            locationDetails.innerHTML = `
                <div class="location-item">
                    <span class="label">Job Location:</span>
                    <span class="value">${locationData.details.job_location || 'Not specified'}</span>
                </div>
                <div class="location-item">
                    <span class="label">Your Location:</span>
                    <span class="value">${locationData.details.user_location || 'Not specified'}</span>
                </div>
                <div class="location-item">
                    <span class="label">Remote Work:</span>
                    <span class="value">${locationData.details.remote_option || 'Not specified'}</span>
                </div>
            `;
        }

        // Add explanation if available
        const explanation = locationSection.querySelector('.category-explanation');
        if (explanation && locationData.explanation) {
            explanation.textContent = locationData.explanation;
        }
    }

    populateSalaryMatch(salaryData) {
        if (!salaryData) return;

        const salarySection = this.matchContent.querySelector('[data-category="salary"]');
        if (!salarySection) return;

        // Update category score
        const categoryScore = salarySection.querySelector('.category-score');
        if (categoryScore) {
            categoryScore.textContent = `${Math.round(salaryData.score)}%`;
        }

        // Update progress bar
        const progressBar = salarySection.querySelector('.progress-fill');
        if (progressBar) {
            progressBar.style.width = `${salaryData.score}%`;
            progressBar.className = 'progress-fill ' + this.getScoreClass(salaryData.score);
        }

        // Update salary details
        const salaryDetails = salarySection.querySelector('.salary-details');
        if (salaryDetails && salaryData.details) {
            salaryDetails.innerHTML = `
                <div class="salary-item">
                    <span class="label">Offered Range:</span>
                    <span class="value">${salaryData.details.offered_range || 'Not specified'}</span>
                </div>
                <div class="salary-item">
                    <span class="label">Your Expectation:</span>
                    <span class="value">${salaryData.details.expected_range || 'Not specified'}</span>
                </div>
                <div class="salary-item">
                    <span class="label">Match Level:</span>
                    <span class="value">${salaryData.details.match_level || 'Not specified'}</span>
                </div>
            `;
        }

        // Add explanation if available
        const explanation = salarySection.querySelector('.category-explanation');
        if (explanation && salaryData.explanation) {
            explanation.textContent = salaryData.explanation;
        }
    }

    populateInterpretation(interpretation) {
        const interpretationSection = this.matchContent.querySelector('.match-interpretation');
        if (interpretationSection && interpretation) {
            interpretationSection.innerHTML = `
                <h4>Match Analysis</h4>
                <p>${interpretation}</p>
            `;
        }
    }

    getScoreClass(score) {
        if (score >= 80) return 'score-high';
        if (score >= 60) return 'score-medium';
        return 'score-low';
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
            
            // Customize error state based on message type
            if (message && message.includes('complete your profile')) {
                if (errorTitle) {
                    errorTitle.textContent = 'Profile Incomplete';
                }
                if (retryButton) {
                    retryButton.style.display = 'none';
                }
                // Add profile completion button
                this.addProfileCompletionButton();
            } else if (message && message.includes('log in')) {
                if (errorTitle) {
                    errorTitle.textContent = 'Login Required';
                }
                if (retryButton) {
                    retryButton.style.display = 'none';
                }
                // Add login button
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