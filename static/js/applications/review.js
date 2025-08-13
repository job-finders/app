/**
 * Application Review JavaScript
 * 
 * Handles the application review page functionality including:
 * - Final submission process
 * - Edit actions for different sections
 * - Validation and confirmation
 * - Draft saving
 */

class ApplicationReview {
    constructor() {
        this.data = window.applicationData || {};
        this.isSubmitting = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateSubmissionButton();
    }
    
    bindEvents() {
        // Submission button
        const submitBtn = document.getElementById('submit-application');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.handleSubmissionClick());
        }
        
        // Save draft button
        const saveDraftBtn = document.getElementById('save-draft');
        if (saveDraftBtn) {
            saveDraftBtn.addEventListener('click', () => this.handleSaveDraft());
        }
        
        // Edit buttons
        const editCoverLetterBtn = document.getElementById('edit-cover-letter');
        if (editCoverLetterBtn) {
            editCoverLetterBtn.addEventListener('click', () => this.handleEditCoverLetter());
        }
        
        const addCoverLetterBtn = document.getElementById('add-cover-letter');
        if (addCoverLetterBtn) {
            addCoverLetterBtn.addEventListener('click', () => this.handleAddCoverLetter());
        }
        
        // Final submission modal
        const finalSubmitBtn = document.getElementById('final-submit');
        if (finalSubmitBtn) {
            finalSubmitBtn.addEventListener('click', () => this.handleFinalSubmission());
        }
        
        // Confirmation checkboxes
        const confirmCheckboxes = document.querySelectorAll('#confirm-accuracy, #confirm-terms');
        confirmCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateFinalSubmitButton());
        });
    }
    
    updateSubmissionButton() {
        const submitBtn = document.getElementById('submit-application');
        if (!submitBtn) return;
        
        // Enable/disable based on validation issues
        if (this.data.validation_issues > 0) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Fix Issues First';
        } else {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit Application';
        }
    }
    
    handleSubmissionClick() {
        if (this.data.validation_issues > 0) {
            this.showError('Please address all validation issues before submitting.');
            return;
        }
        
        // Show confirmation modal
        const modal = document.getElementById('submissionModal');
        if (modal) {
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        }
    }
    
    updateFinalSubmitButton() {
        const finalSubmitBtn = document.getElementById('final-submit');
        const accuracyCheck = document.getElementById('confirm-accuracy');
        const termsCheck = document.getElementById('confirm-terms');
        
        if (finalSubmitBtn && accuracyCheck && termsCheck) {
            const allChecked = accuracyCheck.checked && termsCheck.checked;
            finalSubmitBtn.disabled = !allChecked;
        }
    }
    
    async handleFinalSubmission() {
        if (this.isSubmitting) return;
        
        this.isSubmitting = true;
        const button = document.getElementById('final-submit');
        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch(`/api/applications/workflow/applications/${this.data.application_id}/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    confirmed: true,
                    submission_timestamp: new Date().toISOString()
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Hide modal and redirect to confirmation page
                const modal = bootstrap.Modal.getInstance(document.getElementById('submissionModal'));
                modal.hide();
                
                this.showSuccess('Application submitted successfully!');
                
                // Redirect to confirmation page after 2 seconds
                setTimeout(() => {
                    window.location.href = `/applications/${this.data.application_id}/confirmation`;
                }, 2000);
            } else {
                this.showError(result.message || 'Failed to submit application');
            }
        } catch (error) {
            console.error('Error submitting application:', error);
            this.showError('An error occurred while submitting your application');
        } finally {
            this.isSubmitting = false;
            this.setButtonLoading(button, false);
        }
    }
    
    async handleSaveDraft() {
        const button = document.getElementById('save-draft');
        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch(`/api/applications/workflow/applications/${this.data.application_id}/save-draft`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Draft saved successfully!');
            } else {
                this.showError(result.message || 'Failed to save draft');
            }
        } catch (error) {
            console.error('Error saving draft:', error);
            this.showError('An error occurred while saving the draft');
        } finally {
            this.setButtonLoading(button, false);
        }
    }
    
    handleEditCoverLetter() {
        // Redirect to cover letter editing
        window.location.href = `/applications/${this.data.application_id}/cover-letter/edit`;
    }
    
    handleAddCoverLetter() {
        // Redirect to cover letter creation or open modal
        const jobDetailUrl = `/jobs/${this.data.job_id}`;
        window.location.href = jobDetailUrl + '#cover-letter';
    }
    
    setButtonLoading(button, loading) {
        if (!button) return;
        
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
    new ApplicationReview();
});