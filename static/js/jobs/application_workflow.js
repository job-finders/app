/**
 * Job Application Workflow JavaScript
 * 
 * Handles the job application workflow process including:
 * - Application initiation
 * - Cover letter generation
 * - Progress tracking
 * - Workflow navigation
 */

class ApplicationWorkflow {
    constructor() {
        this.baseUrl = '/api/applications/workflow';
        this.currentApplicationId = null;
        this.currentJobId = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadApplicationProgress();
    }
    
    bindEvents() {
        // Start Application button
        const startBtn = document.getElementById('start-application');
        if (startBtn) {
            startBtn.addEventListener('click', (e) => this.handleStartApplication(e));
        }
        
        // Continue Application button
        const continueBtn = document.getElementById('continue-application');
        if (continueBtn) {
            continueBtn.addEventListener('click', (e) => this.handleContinueApplication(e));
        }
        
        // Generate Cover Letter buttons
        const generateBtn = document.getElementById('generate-cover-letter-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', (e) => this.handleGenerateCoverLetter(e));
        }
        
        const standaloneBtn = document.getElementById('standalone-cover-letter-btn');
        if (standaloneBtn) {
            standaloneBtn.addEventListener('click', (e) => this.handleGenerateCoverLetter(e));
        }
        
        // View Progress button
        const progressBtn = document.getElementById('view-progress');
        if (progressBtn) {
            progressBtn.addEventListener('click', (e) => this.handleViewProgress(e));
        }
        
        // Analyze Match form (existing functionality)
        const analysisForm = document.getElementById('analysis-form');
        if (analysisForm) {
            analysisForm.addEventListener('submit', (e) => this.handleAnalyzeMatch(e));
        }
    }
    
    async handleStartApplication(event) {
        event.preventDefault();
        
        const button = event.target.closest('button');
        const jobId = button.dataset.jobId;
        
        if (!jobId) {
            this.showError('Job ID not found');
            return;
        }
        
        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch(`${this.baseUrl}/jobs/${jobId}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentApplicationId = result.application_id;
                this.currentJobId = jobId;
                
                // Handle next step based on workflow result
                if (result.next_step === 'cover_letter') {
                    this.showCoverLetterModal(jobId, result.application_id);
                } else if (result.next_step === 'questionnaires') {
                    this.redirectToQuestionnaires(result.application_id);
                } else if (result.next_step === 'review') {
                    this.redirectToReview(result.application_id);
                }
                
                this.showSuccess('Application process started successfully!');
            } else {
                this.showError(result.message || 'Failed to start application process');
            }
        } catch (error) {
            console.error('Error starting application:', error);
            this.showError('An error occurred while starting the application process');
        } finally {
            this.setButtonLoading(button, false);
        }
    }
    
    async handleContinueApplication(event) {
        event.preventDefault();
        
        const button = event.target.closest('button');
        const applicationId = button.dataset.applicationId;
        const nextStep = button.dataset.nextStep;
        
        if (!applicationId) {
            this.showError('Application ID not found');
            return;
        }
        
        this.currentApplicationId = applicationId;
        
        // Navigate to appropriate step
        switch (nextStep) {
            case 'cover_letter':
                this.showCoverLetterModal(this.currentJobId, applicationId);
                break;
            case 'questionnaires':
                this.redirectToQuestionnaires(applicationId);
                break;
            case 'review':
                this.redirectToReview(applicationId);
                break;
            case 'submit':
                this.handleFinalSubmission(applicationId);
                break;
            default:
                this.showError('Unknown next step: ' + nextStep);
        }
    }
    
    async handleGenerateCoverLetter(event) {
        event.preventDefault();
        
        const button = event.target.closest('button');
        const jobId = button.dataset.jobId;
        
        if (!jobId) {
            this.showError('Job ID not found');
            return;
        }
        
        // If no application exists, start one first
        if (!this.currentApplicationId) {
            await this.handleStartApplication(event);
            return;
        }
        
        this.showCoverLetterModal(jobId, this.currentApplicationId);
    }
    
    async handleViewProgress(event) {
        event.preventDefault();
        
        if (!this.currentApplicationId) {
            this.showError('No application in progress');
            return;
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/applications/${this.currentApplicationId}/progress`);
            const result = await response.json();
            
            if (result.success) {
                this.showProgressModal(result);
            } else {
                this.showError(result.message || 'Failed to load progress');
            }
        } catch (error) {
            console.error('Error loading progress:', error);
            this.showError('An error occurred while loading progress');
        }
    }
    
    async handleAnalyzeMatch(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const cvId = formData.get('cv_id');
        
        if (!cvId) {
            this.showError('Please select a CV first');
            return;
        }
        
        const button = form.querySelector('#analyze-btn');
        this.setButtonLoading(button, true);
        
        try {
            // Get job ID from page context
            const jobId = this.getJobIdFromPage();
            
            const response = await fetch(`/agents/employee/v1/jobs/${jobId}/match-analysis`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ cv_id: cvId })
            });
            
            const result = await response.json();
            
            if (response.ok && result) {
                this.displayMatchResults(result);
            } else {
                this.showError('Failed to analyze match');
            }
        } catch (error) {
            console.error('Error analyzing match:', error);
            this.showError('An error occurred during analysis');
        } finally {
            this.setButtonLoading(button, false);
        }
    }
    
    showCoverLetterModal(jobId, applicationId) {
        // Create and show cover letter modal
        const modal = this.createCoverLetterModal(jobId, applicationId);
        document.body.appendChild(modal);
        
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up modal when hidden
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }
    
    createCoverLetterModal(jobId, applicationId) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'coverLetterModal';
        modal.tabIndex = -1;
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-file-text me-2"></i>Generate Cover Letter
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="cover-letter-modal-form">
                            <div class="mb-3">
                                <label for="cv-select-modal" class="form-label">Select CV</label>
                                <select class="form-select" id="cv-select-modal" required>
                                    <option value="">-- Choose CV --</option>
                                    ${this.getCVOptions()}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="draft-text" class="form-label">Draft Cover Letter (Optional)</label>
                                <textarea class="form-control" id="draft-text" rows="4" 
                                         placeholder="Start writing your cover letter draft here..."></textarea>
                                <div class="form-text">
                                    You can write a draft or leave this blank to generate from scratch.
                                </div>
                            </div>
                            <div class="mb-3">
                                <label for="tone-select-modal" class="form-label">Tone</label>
                                <select class="form-select" id="tone-select-modal">
                                    <option value="professional" selected>Professional</option>
                                    <option value="enthusiastic">Enthusiastic</option>
                                    <option value="friendly">Friendly</option>
                                    <option value="formal">Formal</option>
                                    <option value="concise">Concise</option>
                                </select>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="generate-cover-letter-submit">
                            <i class="fas fa-magic me-2"></i>Generate Cover Letter
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Bind submit event
        const submitBtn = modal.querySelector('#generate-cover-letter-submit');
        submitBtn.addEventListener('click', () => {
            this.handleCoverLetterSubmit(jobId, applicationId, modal);
        });
        
        return modal;
    }
    
    async handleCoverLetterSubmit(jobId, applicationId, modal) {
        const form = modal.querySelector('#cover-letter-modal-form');
        const formData = new FormData(form);
        const cvId = modal.querySelector('#cv-select-modal').value;
        const draftText = modal.querySelector('#draft-text').value;
        const tone = modal.querySelector('#tone-select-modal').value;
        const submitBtn = modal.querySelector('#generate-cover-letter-submit');
        
        if (!cvId) {
            this.showError('Please select a CV');
            return;
        }
        
        this.setButtonLoading(submitBtn, true);
        
        try {
            // First, create cover letter session
            const sessionResponse = await fetch(`${this.baseUrl}/cover-letter/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    job_id: jobId,
                    cv_id: cvId,
                    draft_text: draftText,
                    selected_tone: tone
                })
            });
            
            const sessionResult = await sessionResponse.json();
            
            if (!sessionResult.success) {
                throw new Error(sessionResult.message || 'Failed to create cover letter session');
            }
            
            // Generate cover letter using existing endpoint
            const generateResponse = await fetch(`/agents/employee/v1/jobs/${jobId}/cover-letter`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    cv_id: cvId,
                    tone: tone
                })
            });
            
            const generateResult = await generateResponse.json();
            
            if (!generateResponse.ok || !generateResult) {
                throw new Error('Failed to generate cover letter');
            }
            
            // Link cover letter to application if we have an application ID
            if (applicationId) {
                await fetch(`${this.baseUrl}/applications/${applicationId}/cover-letter`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        session_id: sessionResult.session_id
                    })
                });
            }
            
            // Close modal and show success
            bootstrap.Modal.getInstance(modal).hide();
            this.showSuccess('Cover letter generated successfully!');
            
            // Refresh page to show updated state
            setTimeout(() => {
                window.location.reload();
            }, 1500);
            
        } catch (error) {
            console.error('Error generating cover letter:', error);
            this.showError(error.message || 'An error occurred while generating the cover letter');
        } finally {
            this.setButtonLoading(submitBtn, false);
        }
    }
    
    redirectToQuestionnaires(applicationId) {
        // Redirect to questionnaire page (to be implemented)
        window.location.href = `/applications/${applicationId}/questionnaires`;
    }
    
    redirectToReview(applicationId) {
        // Redirect to review page (to be implemented)
        window.location.href = `/applications/${applicationId}/review`;
    }
    
    async handleFinalSubmission(applicationId) {
        if (!confirm('Are you sure you want to submit your application? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/applications/${applicationId}/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Application submitted successfully!');
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                this.showError(result.message || 'Failed to submit application');
            }
        } catch (error) {
            console.error('Error submitting application:', error);
            this.showError('An error occurred while submitting the application');
        }
    }
    
    showProgressModal(progressData) {
        const modal = this.createProgressModal(progressData);
        document.body.appendChild(modal);
        
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }
    
    createProgressModal(progressData) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'progressModal';
        modal.tabIndex = -1;
        
        const stepsHtml = progressData.steps.map(step => `
            <div class="d-flex align-items-center mb-2">
                <div class="me-3">
                    ${step.completed ? 
                        '<i class="fas fa-check-circle text-success"></i>' : 
                        step.current ? 
                            '<i class="fas fa-circle text-primary"></i>' : 
                            '<i class="far fa-circle text-muted"></i>'
                    }
                </div>
                <div class="flex-grow-1">
                    <div class="fw-semibold ${step.current ? 'text-primary' : step.completed ? 'text-success' : 'text-muted'}">
                        ${step.display_name}
                    </div>
                </div>
            </div>
        `).join('');
        
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-tasks me-2"></i>Application Progress
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <div class="d-flex justify-content-between mb-2">
                                <span>Overall Progress</span>
                                <span class="fw-semibold">${progressData.completion_percentage}%</span>
                            </div>
                            <div class="progress">
                                <div class="progress-bar bg-primary" style="width: ${progressData.completion_percentage}%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <h6>Steps:</h6>
                            ${stepsHtml}
                        </div>
                        ${progressData.validation_score ? `
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                Application Quality Score: <strong>${progressData.validation_score}/100</strong>
                            </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    displayMatchResults(result) {
        const resultsDiv = document.getElementById('match-results');
        const summaryDiv = document.getElementById('match-summary');
        const scoreDiv = document.getElementById('match-score');
        
        if (resultsDiv && summaryDiv && scoreDiv) {
            summaryDiv.textContent = result.summary || 'Analysis complete';
            
            const score = result.overall_score || 0;
            const scoreClass = score >= 75 ? 'success' : score >= 50 ? 'warning' : 'danger';
            scoreDiv.innerHTML = `<span class="badge bg-${scoreClass}">${score}/100</span>`;
            
            resultsDiv.classList.remove('d-none');
        }
    }
    
    async loadApplicationProgress() {
        // Check if there's an application in progress for this job
        const jobId = this.getJobIdFromPage();
        if (!jobId) return;
        
        // This would typically be provided by the backend template
        // For now, we'll rely on the template data
    }
    
    getCVOptions() {
        // Get CV options from existing select element
        const existingSelect = document.getElementById('cv_select');
        if (existingSelect) {
            return existingSelect.innerHTML;
        }
        return '<option value="">No CVs available</option>';
    }
    
    getJobIdFromPage() {
        // Extract job ID from page context or URL
        const startBtn = document.getElementById('start-application');
        if (startBtn) {
            return startBtn.dataset.jobId;
        }
        
        // Fallback: extract from URL
        const pathParts = window.location.pathname.split('/');
        const jobIndex = pathParts.indexOf('jobs');
        if (jobIndex !== -1 && pathParts[jobIndex + 1]) {
            return pathParts[jobIndex + 1];
        }
        
        return null;
    }
    
    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.dataset.originalText = originalText;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
        } else {
            button.disabled = false;
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
                delete button.dataset.originalText;
            }
        }
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Add to toast container or create one
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        const bootstrapToast = new bootstrap.Toast(toast);
        bootstrapToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ApplicationWorkflow();
});
 
   /**
     * Progress Ring Component
     * Creates animated circular progress indicators
     */
    createProgressRing(percentage, size = 60) {
        const template = document.getElementById('progress-ring-template');
        if (!template) return null;
        
        const ring = template.content.cloneNode(true);
        const svg = ring.querySelector('svg');
        const fillCircle = ring.querySelector('.progress-ring-fill');
        const textElement = ring.querySelector('.progress-ring-text');
        
        // Set size
        svg.style.width = size + 'px';
        svg.style.height = size + 'px';
        
        // Calculate progress
        const radius = 25;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percentage / 100) * circumference;
        
        fillCircle.style.strokeDasharray = circumference;
        fillCircle.style.strokeDashoffset = offset;
        
        textElement.textContent = percentage + '%';
        
        return ring;
    }
    
    /**
     * Enhanced Progress Modal
     * Shows detailed progress with animations
     */
    showEnhancedProgressModal(progressData) {
        const modal = document.getElementById('workflowProgressModal');
        const contentDiv = document.getElementById('progress-modal-content');
        const continueBtn = document.getElementById('continue-from-modal');
        
        if (!modal || !contentDiv) {
            console.error('Progress modal elements not found');
            return;
        }
        
        // Build enhanced progress content
        const progressHtml = this.buildProgressModalContent(progressData);
        contentDiv.innerHTML = progressHtml;
        
        // Set up continue button
        if (continueBtn && progressData.next_step && progressData.current_step !== 'submitted') {
            continueBtn.style.display = 'block';
            continueBtn.onclick = () => {
                bootstrap.Modal.getInstance(modal).hide();
                this.handleContinueApplication({
                    target: {
                        closest: () => ({
                            dataset: {
                                applicationId: progressData.application_id,
                                nextStep: progressData.next_step
                            }
                        })
                    }
                });
            };
        } else {
            continueBtn.style.display = 'none';
        }
        
        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Animate progress elements
        setTimeout(() => {
            this.animateProgressElements(contentDiv);
        }, 300);
    }
    
    buildProgressModalContent(progressData) {
        const steps = progressData.steps || [];
        const currentStepIndex = steps.findIndex(step => step.current);
        
        let stepsHtml = steps.map((step, index) => {
            const isCompleted = step.completed;
            const isCurrent = step.current;
            const isPending = !isCompleted && !isCurrent;
            
            let iconClass = 'far fa-circle text-muted';
            let statusClass = 'text-muted';
            
            if (isCompleted) {
                iconClass = 'fas fa-check-circle text-success';
                statusClass = 'text-success fw-semibold';
            } else if (isCurrent) {
                iconClass = 'fas fa-circle text-primary';
                statusClass = 'text-primary fw-semibold';
            }
            
            return `
                <div class="progress-step-item slide-up" style="animation-delay: ${index * 0.1}s">
                    <div class="progress-step-icon">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="progress-step-content">
                        <div class="progress-step-title ${statusClass}">
                            ${step.display_name}
                        </div>
                        <div class="progress-step-description">
                            ${this.getStepDescription(step.step, isCompleted, isCurrent)}
                        </div>
                    </div>
                    ${isCurrent ? '<div class="badge bg-primary">Current</div>' : ''}
                    ${isCompleted ? '<div class="badge bg-success">Complete</div>' : ''}
                </div>
            `;
        }).join('');
        
        return `
            <div class="row">
                <div class="col-md-8">
                    <h6 class="mb-3">Progress Steps</h6>
                    <div class="progress-steps-container">
                        ${stepsHtml}
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="text-center mb-4">
                        <div class="progress-ring-container mb-3">
                            ${this.createProgressRingHTML(progressData.completion_percentage)}
                        </div>
                        <h6 class="mb-1">${progressData.completion_percentage}% Complete</h6>
                        <small class="text-muted">${progressData.current_step_display}</small>
                    </div>
                    
                    ${progressData.validation_score ? `
                        <div class="card border-0 bg-light">
                            <div class="card-body text-center py-3">
                                <h6 class="card-title mb-2">Quality Score</h6>
                                <div class="h4 mb-1 ${this.getScoreColorClass(progressData.validation_score)}">
                                    ${progressData.validation_score}/100
                                </div>
                                <small class="text-muted">${this.getScoreLabel(progressData.validation_score)}</small>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${progressData.workflow_duration_minutes ? `
                        <div class="mt-3 text-center">
                            <small class="text-muted">
                                <i class="fas fa-clock me-1"></i>
                                ${Math.round(progressData.workflow_duration_minutes)} min spent
                            </small>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    createProgressRingHTML(percentage) {
        const radius = 25;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percentage / 100) * circumference;
        
        return `
            <div class="progress-ring">
                <svg width="60" height="60">
                    <circle class="progress-ring-bg" cx="30" cy="30" r="25"></circle>
                    <circle class="progress-ring-fill" cx="30" cy="30" r="25" 
                            style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${offset};"></circle>
                </svg>
                <div class="progress-ring-text">${percentage}%</div>
            </div>
        `;
    }
    
    getStepDescription(step, isCompleted, isCurrent) {
        const descriptions = {
            'draft': isCompleted ? 'Application started successfully' : 
                    isCurrent ? 'Starting your application...' : 'Create your application',
            'cover_letter': isCompleted ? 'Cover letter generated and saved' : 
                           isCurrent ? 'Generate your personalized cover letter' : 'Create cover letter',
            'questionnaires': isCompleted ? 'All questions answered' : 
                             isCurrent ? 'Complete the required questionnaires' : 'Answer questions',
            'review': isCompleted ? 'Application reviewed and ready' : 
                     isCurrent ? 'Review your application before submitting' : 'Review application',
            'submitted': isCompleted ? 'Application submitted successfully' : 
                        isCurrent ? 'Submitting your application...' : 'Submit application'
        };
        
        return descriptions[step] || 'Application step';
    }
    
    getScoreColorClass(score) {
        if (score >= 90) return 'text-success';
        if (score >= 75) return 'text-primary';
        if (score >= 60) return 'text-warning';
        return 'text-secondary';
    }
    
    getScoreLabel(score) {
        if (score >= 90) return 'Excellent';
        if (score >= 75) return 'Good';
        if (score >= 60) return 'Fair';
        return 'Needs Improvement';
    }
    
    animateProgressElements(container) {
        const elements = container.querySelectorAll('.slide-up');
        elements.forEach((element, index) => {
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 100);
        });
        
        // Animate progress ring
        const progressRing = container.querySelector('.progress-ring-fill');
        if (progressRing) {
            progressRing.style.transition = 'stroke-dashoffset 1s ease-in-out';
        }
    }
    
    /**
     * Enhanced View Progress Handler
     * Uses the enhanced modal instead of basic one
     */
    async handleViewProgress(event) {
        event.preventDefault();
        
        if (!this.currentApplicationId) {
            // Try to get application ID from button data
            const button = event.target.closest('button');
            const appId = button?.dataset?.applicationId;
            if (appId) {
                this.currentApplicationId = appId;
            } else {
                this.showError('No application in progress');
                return;
            }
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/applications/${this.currentApplicationId}/progress`);
            const result = await response.json();
            
            if (result.success) {
                this.showEnhancedProgressModal(result);
            } else {
                this.showError(result.message || 'Failed to load progress');
            }
        } catch (error) {
            console.error('Error loading progress:', error);
            this.showError('An error occurred while loading progress');
        }
    }
    
    /**
     * Initialize Progress Indicators
     * Sets up progress indicators on page load
     */
    initializeProgressIndicators() {
        // Animate progress bars on page load
        const progressBars = document.querySelectorAll('.progress-bar');
        progressBars.forEach(bar => {
            const width = bar.style.width;
            bar.style.width = '0%';
            setTimeout(() => {
                bar.style.transition = 'width 1s ease-in-out';
                bar.style.width = width;
            }, 500);
        });
        
        // Initialize workflow steps animation
        const workflowSteps = document.querySelectorAll('.workflow-step');
        workflowSteps.forEach((step, index) => {
            step.style.opacity = '0';
            step.style.transform = 'translateY(20px)';
            setTimeout(() => {
                step.style.transition = 'all 0.5s ease';
                step.style.opacity = '1';
                step.style.transform = 'translateY(0)';
            }, index * 100 + 200);
        });
    }
}

// Override the init method to include progress indicators
ApplicationWorkflow.prototype.originalInit = ApplicationWorkflow.prototype.init;
ApplicationWorkflow.prototype.init = function() {
    this.originalInit();
    this.initializeProgressIndicators();
};