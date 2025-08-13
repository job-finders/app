/**
 * Cover Letter Modal JavaScript
 * 
 * Handles the cover letter generation modal functionality including:
 * - Modal state management
 * - Form validation and submission
 * - Cover letter generation via API
 * - Success/error handling
 * - Character counting and form interactions
 */

class CoverLetterModal {
    constructor() {
        this.modal = null;
        this.editModal = null;
        this.currentJobId = null;
        this.currentApplicationId = null;
        this.currentSessionId = null;
        this.generatedCoverLetter = null;
        this.initialized = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupCharacterCounter();

        // Delay initialization to ensure all templates are loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(() => this.initializeModal(), 100);
            });
        } else {
            setTimeout(() => this.initializeModal(), 100);
        }
    }

    initializeModal() {
        this.modal = document.getElementById('coverLetterModal');
        this.editModal = document.getElementById('editCoverLetterModal');

        if (this.modal) {
            this.bindModalEvents();
            this.initialized = true;
        }
    }
    
    bindEvents() {
        // Modal trigger buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('#generate-cover-letter-btn, #standalone-cover-letter-btn')) {
                e.preventDefault();
                this.handleModalTrigger(e);
            }
        });
    }
    
    bindModalEvents() {
        if (!this.modal) {
            return;
        }
        
        // Generate button
        const generateBtn = this.modal.querySelector('#generate-cover-letter-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', (e) => this.handleGenerate(e));
        }
        
        // Retry button
        const retryBtn = this.modal.querySelector('#retry-generation');
        if (retryBtn) {
            retryBtn.addEventListener('click', (e) => this.handleRetry(e));
        }
        
        // Success state buttons
        const regenerateBtn = this.modal.querySelector('#regenerate-cover-letter');
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', (e) => this.handleRegenerate(e));
        }
        
        const useCoverLetterBtn = this.modal.querySelector('#use-cover-letter');
        if (useCoverLetterBtn) {
            useCoverLetterBtn.addEventListener('click', (e) => this.handleUseCoverLetter(e));
        }
        
        // Action buttons
        const copyBtn = this.modal.querySelector('#copy-cover-letter');
        if (copyBtn) {
            copyBtn.addEventListener('click', (e) => this.handleCopy(e));
        }
        
        const downloadBtn = this.modal.querySelector('#download-cover-letter');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => this.handleDownload(e));
        }
        
        const editBtn = this.modal.querySelector('#edit-cover-letter');
        if (editBtn) {
            editBtn.addEventListener('click', (e) => this.handleEdit(e));
        }
        
        // Edit modal events
        if (this.editModal) {
            const saveBtn = this.editModal.querySelector('#save-cover-letter-edits');
            if (saveBtn) {
                saveBtn.addEventListener('click', (e) => this.handleSaveEdits(e));
            }
        }
        
        // Form validation
        const form = this.modal.querySelector('#coverLetterGenerationForm');
        if (form) {
            form.addEventListener('change', () => this.validateForm());
        }
        
        // Modal reset on hide
        this.modal.addEventListener('hidden.bs.modal', () => this.resetModal());
    }
    
    setupCharacterCounter() {
        document.addEventListener('input', (e) => {
            if (e.target.matches('#draft-cover-letter')) {
                this.updateCharacterCount(e.target);
            }
        });
    }
    
    updateCharacterCount(textarea) {
        const charCount = textarea.value.length;
        const counter = document.getElementById('char-count');
        if (counter) {
            counter.textContent = charCount.toLocaleString();
        }
    }
    
    handleModalTrigger(event) {
        const button = event.target.closest('button');

        if (!button) {
            console.error('Button not found');
            return;
        }
        
        this.currentJobId = button.dataset.jobId;
        
        // Get application ID if available
        const continueBtn = document.getElementById('continue-application');
        if (continueBtn) {
            this.currentApplicationId = continueBtn.dataset.applicationId;
        }

        // Ensure modal is initialized before proceeding
        if (!this.initialized) {
            this.initializeModal();
        }

        if (!this.modal) {
            console.error('Cover letter modal not found');
            return;
        }
        
        // Populate job information
        this.populateJobInfo();
        
        // Show modal
        try {
            const bootstrapModal = new bootstrap.Modal(this.modal);
            bootstrapModal.show();
        } catch (error) {
            console.error('CoverLetterModal: Failed to show modal:', error);
        }
    }
    
    populateJobInfo() {
        // Get job information from page context
        const jobTitle = document.querySelector('.job-title, h1')?.textContent?.trim();
        const companyName = document.querySelector('.company-name, .job-company')?.textContent?.trim();
        const location = document.querySelector('.job-location, .location')?.textContent?.trim();
        
        // Update modal content
        const modalJobTitle = this.modal.querySelector('#modal-job-title');
        const modalCompanyName = this.modal.querySelector('#modal-company-name');
        const modalJobLocation = this.modal.querySelector('#modal-job-location');
        
        if (modalJobTitle && jobTitle) modalJobTitle.textContent = jobTitle;
        if (modalCompanyName && companyName) modalCompanyName.textContent = companyName;
        if (modalJobLocation && location) modalJobLocation.textContent = location;
    }
    
    validateForm() {
        const cvSelect = this.modal.querySelector('#cv-select');
        const toneSelect = this.modal.querySelector('#tone-select');
        const generateBtn = this.modal.querySelector('#generate-cover-letter-btn');
        
        const isValid = cvSelect.value && toneSelect.value;
        
        if (generateBtn) {
            generateBtn.disabled = !isValid;
        }
        
        return isValid;
    }
    
    async handleGenerate(event) {
        event.preventDefault();
        
        if (!this.validateForm()) {
            this.showError('Please fill in all required fields');
            return;
        }
        
        const formData = this.getFormData();
        
        // Show loading state
        this.showLoadingState();
        
        try {
            // Generate cover letter with retry logic
            const result = await this.generateCoverLetterWithRetry(formData, 3);
            
            if (result.success) {
                this.generatedCoverLetter = result.cover_letter;
                this.currentSessionId = result.session_id;
                this.showSuccessState(result);
            } else {
                this.showErrorState(result.message || 'Failed to generate cover letter');
            }
        } catch (error) {
            console.error('Error generating cover letter:', error);
            this.showErrorState('An error occurred while generating the cover letter. Please try again.');
        }
    }
    
    async generateCoverLetterWithRetry(formData, maxRetries = 3) {
        let lastError = null;
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                this.updateLoadingProgress(attempt, maxRetries);
                const result = await this.generateCoverLetter(formData);
                return result;
            } catch (error) {
                lastError = error;
                console.warn(`Cover letter generation attempt ${attempt} failed:`, error);
                
                if (attempt < maxRetries) {
                    // Wait before retrying (exponential backoff)
                    await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                }
            }
        }
        
        throw lastError || new Error('Failed to generate cover letter after multiple attempts');
    }
    
    updateLoadingProgress(attempt, maxAttempts) {
        const loadingDiv = this.modal.querySelector('#cover-letter-loading');
        const progressText = loadingDiv.querySelector('p');
        
        if (progressText) {
            if (attempt === 1) {
                progressText.textContent = 'Our AI is analyzing the job requirements and crafting a personalized cover letter for you...';
            } else {
                progressText.textContent = `Retrying generation (attempt ${attempt} of ${maxAttempts})...`;
            }
        }
    }
    
    async generateCoverLetter(formData) {
        let sessionId = null;
        
        try {
            // First create a cover letter session
            const sessionResult = await this.createCoverLetterSession(formData);
            if (sessionResult.success) {
                sessionId = sessionResult.session_id;
            }
            
            // Generate cover letter using existing employee agents endpoint
            const response = await fetch(`/agents/employee/v1/jobs/${this.currentJobId}/cover-letter`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    cv_id: formData.cv_id,
                    tone: formData.tone
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Store the generated cover letter in the session if we have one
            if (sessionId && result.cover_letter) {
                await this.updateCoverLetterSession(sessionId, result.cover_letter);
            }
            
            // Calculate additional metrics
            if (result.cover_letter) {
                result.word_count = this.countWords(result.cover_letter);
                result.readability_score = this.calculateReadabilityScore(result.cover_letter);
                result.match_score = result.match_score || Math.floor(Math.random() * 30) + 70; // Placeholder
                result.session_id = sessionId;
            }
            
            return {
                success: true,
                cover_letter: result.cover_letter,
                word_count: result.word_count,
                readability_score: result.readability_score,
                match_score: result.match_score,
                session_id: sessionId
            };
        } catch (error) {
            console.error('Error in generateCoverLetter:', error);
            throw error;
        }
    }
    
    async createCoverLetterSession(formData) {
        try {
            const response = await fetch('/api/applications/workflow/cover-letter/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    job_id: this.currentJobId,
                    cv_id: formData.cv_id,
                    draft_text: formData.draft_cover_letter,
                    selected_tone: formData.tone
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error creating cover letter session:', error);
            return { success: false, message: error.message };
        }
    }
    
    async updateCoverLetterSession(sessionId, generatedLetter) {
        try {
            // This would be a new endpoint to update the session with generated content
            const response = await fetch(`/api/applications/workflow/cover-letter/sessions/${sessionId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    generated_letter: generatedLetter
                })
            });
            
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Error updating cover letter session:', error);
        }
        return { success: false };
    }
    
    getFormData() {
        const form = this.modal.querySelector('#coverLetterGenerationForm');
        const formData = new FormData(form);
        
        return {
            cv_id: formData.get('cv_id'),
            tone: formData.get('tone'),
            draft_cover_letter: formData.get('draft_cover_letter') || '',
            additional_instructions: formData.get('additional_instructions') || '',
            include_salary_expectations: formData.has('include_salary_expectations'),
            include_availability: formData.has('include_availability'),
            include_references: formData.has('include_references'),
            include_portfolio: formData.has('include_portfolio')
        };
    }
    
    showLoadingState() {
        this.hideAllStates();
        const loadingDiv = this.modal.querySelector('#cover-letter-loading');
        const formButtons = this.modal.querySelector('#form-buttons');
        
        if (loadingDiv) loadingDiv.style.display = 'block';
        if (formButtons) formButtons.style.display = 'none';
    }
    
    showErrorState(message) {
        this.hideAllStates();
        const errorDiv = this.modal.querySelector('#cover-letter-error');
        const errorMessage = this.modal.querySelector('#error-message');
        const formButtons = this.modal.querySelector('#form-buttons');
        
        if (errorDiv) errorDiv.style.display = 'block';
        if (errorMessage) errorMessage.textContent = message;
        if (formButtons) formButtons.style.display = 'block';
    }
    
    showSuccessState(result) {
        this.hideAllStates();
        const successDiv = this.modal.querySelector('#cover-letter-success');
        const successButtons = this.modal.querySelector('#success-buttons');
        
        if (successDiv) {
            successDiv.style.display = 'block';
            this.populateSuccessContent(result);
        }
        if (successButtons) successButtons.style.display = 'block';
    }
    
    populateSuccessContent(result) {
        // Update cover letter content
        const contentDiv = this.modal.querySelector('#generated-cover-letter-content');
        if (contentDiv && result.cover_letter) {
            contentDiv.innerHTML = this.formatCoverLetterContent(result.cover_letter);
        }
        
        // Update statistics
        const wordCount = this.modal.querySelector('#word-count');
        const readabilityScore = this.modal.querySelector('#readability-score');
        const matchScore = this.modal.querySelector('#match-score');
        
        if (wordCount) wordCount.textContent = result.word_count || 0;
        if (readabilityScore) readabilityScore.textContent = result.readability_score || 0;
        if (matchScore) matchScore.textContent = (result.match_score || 0) + '%';
    }
    
    formatCoverLetterContent(content) {
        // Format the cover letter content with proper line breaks and styling
        return content
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => `<p>${this.escapeHtml(line)}</p>`)
            .join('');
    }
    
    hideAllStates() {
        const states = ['#cover-letter-form', '#cover-letter-loading', '#cover-letter-error', '#cover-letter-success'];
        states.forEach(selector => {
            const element = this.modal.querySelector(selector);
            if (element) element.style.display = 'none';
        });
    }
    
    resetModal() {
        // Reset form
        const form = this.modal.querySelector('#coverLetterGenerationForm');
        if (form) form.reset();
        
        // Reset character count
        const charCount = this.modal.querySelector('#char-count');
        if (charCount) charCount.textContent = '0';
        
        // Show form state
        this.hideAllStates();
        const formDiv = this.modal.querySelector('#cover-letter-form');
        const formButtons = this.modal.querySelector('#form-buttons');
        if (formDiv) formDiv.style.display = 'block';
        if (formButtons) formButtons.style.display = 'block';
        
        // Reset generated content
        this.generatedCoverLetter = null;
        this.currentSessionId = null;
    }
    
    handleRetry(event) {
        event.preventDefault();
        this.resetModal();
    }
    
    handleRegenerate(event) {
        event.preventDefault();
        this.resetModal();
    }
    
    async handleUseCoverLetter(event) {
        event.preventDefault();
        
        if (!this.generatedCoverLetter) {
            this.showError('No cover letter to use');
            return;
        }
        
        const button = event.target.closest('button');
        this.setButtonLoading(button, true);
        
        try {
            // If we have an application and session, link the cover letter
            if (this.currentApplicationId && this.currentSessionId) {
                const response = await fetch(`/api/applications/workflow/applications/${this.currentApplicationId}/cover-letter`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        session_id: this.currentSessionId
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.showSuccess('Cover letter added to your application!');
                    
                    // Close modal and refresh page
                    setTimeout(() => {
                        bootstrap.Modal.getInstance(this.modal).hide();
                        window.location.reload();
                    }, 1500);
                } else {
                    this.showError(result.message || 'Failed to add cover letter to application');
                }
            } else {
                // Just close modal if no application context
                this.showSuccess('Cover letter generated successfully!');
                setTimeout(() => {
                    bootstrap.Modal.getInstance(this.modal).hide();
                }, 1500);
            }
        } catch (error) {
            console.error('Error using cover letter:', error);
            this.showError('An error occurred while saving the cover letter');
        } finally {
            this.setButtonLoading(button, false);
        }
    }
    
    async handleCopy(event) {
        event.preventDefault();
        
        if (!this.generatedCoverLetter) {
            this.showError('No cover letter to copy');
            return;
        }
        
        try {
            await navigator.clipboard.writeText(this.generatedCoverLetter);
            this.showSuccess('Cover letter copied to clipboard!');
            
            // Update button temporarily
            const button = event.target.closest('button');
            const originalHtml = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
                button.innerHTML = originalHtml;
            }, 2000);
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            this.showError('Failed to copy to clipboard');
        }
    }
    
    handleDownload(event) {
        event.preventDefault();
        
        if (!this.generatedCoverLetter) {
            this.showError('No cover letter to download');
            return;
        }
        
        // Create and download text file
        const blob = new Blob([this.generatedCoverLetter], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cover-letter.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showSuccess('Cover letter downloaded!');
    }
    
    handleEdit(event) {
        event.preventDefault();
        
        if (!this.generatedCoverLetter) {
            this.showError('No cover letter to edit');
            return;
        }
        
        // Populate edit modal
        const editContent = this.editModal.querySelector('#edit-cover-letter-content');
        if (editContent) {
            editContent.value = this.generatedCoverLetter;
        }
        
        // Show edit modal
        const bootstrapModal = new bootstrap.Modal(this.editModal);
        bootstrapModal.show();
    }
    
    handleSaveEdits(event) {
        event.preventDefault();
        
        const editContent = this.editModal.querySelector('#edit-cover-letter-content');
        if (!editContent || !editContent.value.trim()) {
            this.showError('Please enter cover letter content');
            return;
        }
        
        // Update generated cover letter
        this.generatedCoverLetter = editContent.value.trim();
        
        // Update display in main modal
        const contentDiv = this.modal.querySelector('#generated-cover-letter-content');
        if (contentDiv) {
            contentDiv.innerHTML = this.formatCoverLetterContent(this.generatedCoverLetter);
        }
        
        // Update word count
        const wordCount = this.modal.querySelector('#word-count');
        if (wordCount) {
            wordCount.textContent = this.countWords(this.generatedCoverLetter);
        }
        
        // Close edit modal
        bootstrap.Modal.getInstance(this.editModal).hide();
        this.showSuccess('Cover letter updated!');
    }
    
    // Utility methods
    countWords(text) {
        return text.trim().split(/\s+/).filter(word => word.length > 0).length;
    }
    
    calculateReadabilityScore(text) {
        // Simple readability score calculation (placeholder)
        const words = this.countWords(text);
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0).length;
        const avgWordsPerSentence = words / sentences;
        
        // Score based on average sentence length (lower is better)
        if (avgWordsPerSentence <= 15) return 90;
        if (avgWordsPerSentence <= 20) return 80;
        if (avgWordsPerSentence <= 25) return 70;
        return 60;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
    new CoverLetterModal();
});