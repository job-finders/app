/**
 * Application Confirmation JavaScript
 * 
 * Handles the confirmation page functionality including:
 * - Reference number copying
 * - Social sharing
 * - Reminder setting
 * - Analytics tracking
 */

class ApplicationConfirmation {
    constructor() {
        this.data = window.confirmationData || {};
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.trackSubmissionEvent();
    }
    
    bindEvents() {
        // Copy reference number
        const copyBtn = document.getElementById('copy-reference');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyReferenceNumber());
        }
        
        // Social sharing buttons
        const linkedinBtn = document.getElementById('share-linkedin');
        const twitterBtn = document.getElementById('share-twitter');
        const whatsappBtn = document.getElementById('share-whatsapp');
        
        if (linkedinBtn) {
            linkedinBtn.addEventListener('click', () => this.shareOnLinkedIn());
        }
        
        if (twitterBtn) {
            twitterBtn.addEventListener('click', () => this.shareOnTwitter());
        }
        
        if (whatsappBtn) {
            whatsappBtn.addEventListener('click', () => this.shareOnWhatsApp());
        }
        
        // Reminder modal
        const setReminderBtn = document.getElementById('set-reminder');
        if (setReminderBtn) {
            setReminderBtn.addEventListener('click', () => this.setReminder());
        }
    }
    
    async copyReferenceNumber() {
        const referenceNumber = this.data.reference_number;
        const copyBtn = document.getElementById('copy-reference');
        
        if (!referenceNumber) {
            this.showError('Reference number not found');
            return;
        }
        
        try {
            await navigator.clipboard.writeText(referenceNumber);
            
            // Update button appearance
            copyBtn.classList.add('copied');
            copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            
            this.showSuccess('Reference number copied to clipboard!');
            
            // Reset button after 3 seconds
            setTimeout(() => {
                copyBtn.classList.remove('copied');
                copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            }, 3000);
            
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            
            // Fallback: select text for manual copying
            this.selectReferenceText();
            this.showError('Please copy the reference number manually');
        }
    }
    
    selectReferenceText() {
        const referenceElement = document.querySelector('.reference-number');
        if (referenceElement) {
            const range = document.createRange();
            range.selectNodeContents(referenceElement);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
        }
    }
    
    shareOnLinkedIn() {
        const message = this.generateShareMessage();
        const url = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(window.location.href)}&summary=${encodeURIComponent(message)}`;
        
        this.openShareWindow(url, 'LinkedIn');
        this.trackShareEvent('linkedin');
    }
    
    shareOnTwitter() {
        const message = this.generateShareMessage(280); // Twitter character limit
        const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(message)}`;
        
        this.openShareWindow(url, 'Twitter');
        this.trackShareEvent('twitter');
    }
    
    shareOnWhatsApp() {
        const message = this.generateShareMessage();
        const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
        
        this.openShareWindow(url, 'WhatsApp');
        this.trackShareEvent('whatsapp');
    }
    
    generateShareMessage(maxLength = null) {
        const baseMessage = `🎉 Just submitted my application for ${this.data.job_title} at ${this.data.company_name}! Excited about this opportunity. #JobSearch #CareerGrowth #JobFinders`;
        
        if (maxLength && baseMessage.length > maxLength) {
            return `🎉 Applied for ${this.data.job_title} at ${this.data.company_name}! #JobSearch #JobFinders`;
        }
        
        return baseMessage;
    }
    
    openShareWindow(url, platform) {
        const width = 600;
        const height = 400;
        const left = (window.innerWidth - width) / 2;
        const top = (window.innerHeight - height) / 2;
        
        const features = `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`;
        
        window.open(url, `share-${platform.toLowerCase()}`, features);
    }
    
    async setReminder() {
        const reminderDays = document.getElementById('reminder-days').value;
        const setReminderBtn = document.getElementById('set-reminder');
        
        this.setButtonLoading(setReminderBtn, true);
        
        try {
            const response = await fetch('/api/applications/workflow/reminders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    application_id: this.data.application_id,
                    reminder_days: parseInt(reminderDays),
                    reminder_type: 'follow_up'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess(`Reminder set for ${reminderDays} days from now!`);
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('reminderModal'));
                modal.hide();
            } else {
                this.showError(result.message || 'Failed to set reminder');
            }
        } catch (error) {
            console.error('Error setting reminder:', error);
            this.showError('An error occurred while setting the reminder');
        } finally {
            this.setButtonLoading(setReminderBtn, false);
        }
    }
    
    trackSubmissionEvent() {
        // Track application submission for analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'application_submitted', {
                'job_id': this.data.job_id,
                'job_title': this.data.job_title,
                'company_name': this.data.company_name,
                'application_id': this.data.application_id
            });
        }
        
        // Track with custom analytics if available
        if (typeof analytics !== 'undefined') {
            analytics.track('Application Submitted', {
                jobId: this.data.job_id,
                jobTitle: this.data.job_title,
                companyName: this.data.company_name,
                applicationId: this.data.application_id,
                submittedAt: this.data.submitted_at
            });
        }
    }
    
    trackShareEvent(platform) {
        // Track social sharing for analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'share', {
                'method': platform,
                'content_type': 'application_success',
                'item_id': this.data.application_id
            });
        }
        
        if (typeof analytics !== 'undefined') {
            analytics.track('Application Shared', {
                platform: platform,
                applicationId: this.data.application_id,
                jobTitle: this.data.job_title
            });
        }
    }
    
    setButtonLoading(button, loading) {
        if (!button) return;
        
        if (loading) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.dataset.originalText = originalText;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Setting...';
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
    new ApplicationConfirmation();
    
    // Add some celebration effects
    setTimeout(() => {
        createConfetti();
    }, 1000);
});

// Simple confetti effect
function createConfetti() {
    const colors = ['#198754', '#20c997', '#0d6efd', '#6610f2', '#ffc107'];
    const confettiCount = 50;
    
    for (let i = 0; i < confettiCount; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.style.position = 'fixed';
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.top = '-10px';
            confetti.style.width = '10px';
            confetti.style.height = '10px';
            confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.borderRadius = '50%';
            confetti.style.pointerEvents = 'none';
            confetti.style.zIndex = '9999';
            confetti.style.animation = `fall ${Math.random() * 3 + 2}s linear forwards`;
            
            document.body.appendChild(confetti);
            
            setTimeout(() => {
                confetti.remove();
            }, 5000);
        }, i * 100);
    }
}

// Add CSS for confetti animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fall {
        0% {
            transform: translateY(-10px) rotate(0deg);
            opacity: 1;
        }
        100% {
            transform: translateY(100vh) rotate(360deg);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);