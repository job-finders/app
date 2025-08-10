/**
 * Job Actions JavaScript
 * Handles job interaction functionality (like, save, share)
 */

class JobActions {
    constructor() {
        this.csrfToken = null;
        this.init();
        this.bindEvents();
    }

    init() {
        // Initialize toast notifications
        this.initToasts();

        // Load CSRF token
        this.loadCSRFToken();

        // Load initial job actions state
        this.loadJobActionsState();

        // Initialize share modal
        this.initShareModal();
    }

    bindEvents() {
        // Like button events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.like-btn')) {
                e.preventDefault();
                this.handleLikeClick(e.target.closest('.like-btn'));
            }
        });

        // Save button events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.save-btn')) {
                e.preventDefault();
                this.handleSaveClick(e.target.closest('.save-btn'));
            }
        });

        // Share option events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.share-option')) {
                e.preventDefault();
                this.handleShareClick(e.target.closest('.share-option'));
            }
        });

        // Share modal events
        const shareModal = document.getElementById('shareJobModal');
        if (shareModal) {
            shareModal.addEventListener('show.bs.modal', (e) => {
                this.prepareShareModal(e.relatedTarget);
            });
        }
    }

    initToasts() {
        // Initialize Bootstrap toasts
        this.toasts = {
            likeSuccess: new bootstrap.Toast(document.getElementById('likeSuccessToast')),
            saveSuccess: new bootstrap.Toast(document.getElementById('saveSuccessToast')),
            error: new bootstrap.Toast(document.getElementById('errorToast'))
        };
    }

    async loadCSRFToken() {
        try {
            const response = await fetch('/api/jobs/csrf-token', {
                method: 'GET',
                credentials: 'same-origin'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.csrfToken = result.csrf_token;
                }
            }
        } catch (error) {
            console.error('Error loading CSRF token:', error);
        }
    }

    async loadJobActionsState() {
        const panel = document.querySelector('.job-actions-panel');
        if (!panel) return;

        const jobId = panel.dataset.jobId;
        if (!jobId) return;

        try {
            const response = await fetch(`/api/jobs/${jobId}/actions`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-Token': this.csrfToken
                },
                credentials: 'same-origin'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.updateJobActionsUI(result.data);
                }
            }
        } catch (error) {
            console.error('Error loading job actions state:', error);
        }
    }

    updateJobActionsUI(data) {
        // Update like button
        const likeBtn = document.querySelector('.like-btn');
        if (likeBtn) {
            likeBtn.dataset.liked = data.user_has_liked.toString();
            const likeCount = likeBtn.querySelector('.like-count');
            if (likeCount) {
                likeCount.textContent = data.like_count;
            }
        }

        // Update save button
        const saveBtn = document.querySelector('.save-btn');
        if (saveBtn) {
            saveBtn.dataset.saved = data.user_has_saved.toString();
            const saveText = saveBtn.querySelector('.save-text');
            if (saveText) {
                saveText.textContent = data.user_has_saved ? 'Saved' : 'Save Job';
            }
        }

        // Update engagement stats
        const totalLikes = document.querySelector('.total-likes');
        if (totalLikes) {
            totalLikes.textContent = data.like_count;
        }

        const totalShares = document.querySelector('.total-shares');
        if (totalShares) {
            totalShares.textContent = data.share_count;
        }
    }

    async handleLikeClick(button) {
        const jobId = button.dataset.jobId;
        const isLiked = button.dataset.liked === 'true';

        if (!jobId) return;

        // Show loading state
        this.setLoadingState(true);

        try {
            const method = isLiked ? 'DELETE' : 'POST';
            const response = await fetch(`/api/jobs/${jobId}/like`, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-Token': this.csrfToken
                },
                credentials: 'same-origin'
            });

            const result = await response.json();

            if (result.success) {
                // Update button state
                button.dataset.liked = (!isLiked).toString();

                // Update like count
                const likeCount = button.querySelector('.like-count');
                if (likeCount && result.data && typeof result.data.like_count !== 'undefined') {
                    likeCount.textContent = result.data.like_count;

                    // Update total likes in stats
                    const totalLikes = document.querySelector('.total-likes');
                    if (totalLikes) {
                        totalLikes.textContent = result.data.like_count;
                    }
                }

                // Show success toast
                if (!isLiked) {
                    this.showToast('likeSuccess');
                }

                // Trigger animation
                this.triggerLikeAnimation(button);
            } else {
                this.showErrorToast(result.message || 'Failed to update like status');
            }
        } catch (error) {
            console.error('Error handling like:', error);
            this.showErrorToast('Network error. Please try again.');
        } finally {
            this.setLoadingState(false);
        }
    }

    async handleSaveClick(button) {
        const jobId = button.dataset.jobId;
        const isSaved = button.dataset.saved === 'true';

        if (!jobId) return;

        // Show loading state
        this.setLoadingState(true);

        try {
            const method = isSaved ? 'DELETE' : 'POST';
            const response = await fetch(`/api/jobs/${jobId}/save`, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-Token': this.csrfToken
                },
                credentials: 'same-origin'
            });

            const result = await response.json();

            if (result.success) {
                // Update button state
                button.dataset.saved = (!isSaved).toString();

                // Update button text
                const saveText = button.querySelector('.save-text');
                if (saveText) {
                    saveText.textContent = !isSaved ? 'Saved' : 'Save Job';
                }

                // Show success toast
                if (!isSaved) {
                    this.showToast('saveSuccess');
                }

                // Trigger animation
                this.triggerSaveAnimation(button);
            } else {
                this.showErrorToast(result.message || 'Failed to update save status');
            }
        } catch (error) {
            console.error('Error handling save:', error);
            this.showErrorToast('Network error. Please try again.');
        } finally {
            this.setLoadingState(false);
        }
    }

    async handleShareClick(button) {
        const shareMethod = button.dataset.method;
        const modal = button.closest('.modal');
        const jobId = modal ? modal.dataset.jobId : null;

        if (!shareMethod || !jobId) return;

        // Show loading state on button
        const originalContent = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin fa-2x mb-2"></i><div class="small">Sharing...</div>';
        button.disabled = true;

        try {
            const response = await fetch(`/api/jobs/${jobId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-Token': this.csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    share_method: shareMethod
                })
            });

            const result = await response.json();

            if (result.success) {
                // Update share count
                if (result.data && typeof result.data.share_count !== 'undefined') {
                    const totalShares = document.querySelector('.total-shares');
                    if (totalShares) {
                        totalShares.textContent = result.data.share_count;
                    }
                }

                // Handle different share methods
                await this.executeShare(shareMethod, jobId, result.data);

                // Show success message
                this.showShareSuccess(shareMethod);
            } else {
                this.showErrorToast(result.message || 'Failed to share job');
            }
        } catch (error) {
            console.error('Error sharing job:', error);
            this.showErrorToast('Network error. Please try again.');
        } finally {
            // Restore button
            button.innerHTML = originalContent;
            button.disabled = false;
        }
    }

    async executeShare(method, jobId, data) {
        const jobUrl = `${window.location.origin}/jobs/${jobId}`;
        const jobTitle = document.querySelector('h1')?.textContent || 'Job Opportunity';
        const companyName = document.querySelector('.text-primary')?.textContent || 'Company';

        // Add referral code if available
        const shareUrl = data && data.referral_code
            ? `${jobUrl}?ref=${data.referral_code}`
            : jobUrl;

        const shareText = `Check out this job opportunity: ${jobTitle} at ${companyName}`;

        switch (method) {
            case 'email':
                const emailSubject = encodeURIComponent(`Job Opportunity: ${jobTitle}`);
                const emailBody = encodeURIComponent(`${shareText}\n\n${shareUrl}`);
                window.open(`mailto:?subject=${emailSubject}&body=${emailBody}`);
                break;

            case 'linkedin':
                const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;
                window.open(linkedinUrl, '_blank', 'width=600,height=400');
                break;

            case 'twitter':
                const twitterText = encodeURIComponent(`${shareText} ${shareUrl}`);
                const twitterUrl = `https://twitter.com/intent/tweet?text=${twitterText}`;
                window.open(twitterUrl, '_blank', 'width=600,height=400');
                break;

            case 'facebook':
                const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
                window.open(facebookUrl, '_blank', 'width=600,height=400');
                break;

            case 'whatsapp':
                const whatsappText = encodeURIComponent(`${shareText} ${shareUrl}`);
                const whatsappUrl = `https://wa.me/?text=${whatsappText}`;
                window.open(whatsappUrl, '_blank');
                break;

            case 'copy_link':
                try {
                    await navigator.clipboard.writeText(shareUrl);
                    this.showCopySuccess();
                } catch (error) {
                    // Fallback for older browsers
                    this.fallbackCopyToClipboard(shareUrl);
                }
                break;
        }
    }

    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            document.execCommand('copy');
            this.showCopySuccess();
        } catch (error) {
            console.error('Fallback copy failed:', error);
            this.showErrorToast('Failed to copy link');
        }

        document.body.removeChild(textArea);
    }

    initShareModal() {
        const shareModal = document.getElementById('shareJobModal');
        if (!shareModal) return;

        // Set job ID on modal when share button is clicked
        document.addEventListener('click', (e) => {
            if (e.target.closest('.share-btn')) {
                const jobId = e.target.closest('.share-btn').dataset.jobId;
                shareModal.dataset.jobId = jobId;
            }
        });
    }

    prepareShareModal(triggerButton) {
        const modal = document.getElementById('shareJobModal');
        if (!modal || !triggerButton) return;

        const jobId = triggerButton.dataset.jobId;
        if (jobId) {
            modal.dataset.jobId = jobId;
        }
    }

    setLoadingState(loading) {
        const panel = document.querySelector('.job-actions-panel');
        if (!panel) return;

        if (loading) {
            panel.classList.add('loading');
            panel.querySelector('.loading-overlay')?.classList.remove('d-none');
        } else {
            panel.classList.remove('loading');
            panel.querySelector('.loading-overlay')?.classList.add('d-none');
        }
    }

    triggerLikeAnimation(button) {
        const icon = button.querySelector('.like-icon');
        if (icon && button.dataset.liked === 'true') {
            icon.style.animation = 'none';
            setTimeout(() => {
                icon.style.animation = 'heartBeat 0.6s ease-in-out';
            }, 10);
        }
    }

    triggerSaveAnimation(button) {
        const icon = button.querySelector('.save-icon');
        if (icon && button.dataset.saved === 'true') {
            icon.style.animation = 'none';
            setTimeout(() => {
                icon.style.animation = 'bookmarkFill 0.4s ease-in-out';
            }, 10);
        }
    }

    showToast(type) {
        if (this.toasts[type]) {
            this.toasts[type].show();
        }
    }

    showErrorToast(message) {
        const errorToastMessage = document.getElementById('errorToastMessage');
        if (errorToastMessage) {
            errorToastMessage.textContent = message;
        }
        this.showToast('error');
    }

    showShareSuccess(method) {
        const successAlert = document.getElementById('shareSuccessAlert');
        const successMessage = document.getElementById('shareSuccessMessage');

        if (successAlert && successMessage) {
            const methodNames = {
                email: 'Email',
                linkedin: 'LinkedIn',
                twitter: 'Twitter',
                facebook: 'Facebook',
                whatsapp: 'WhatsApp',
                copy_link: 'Link copied to clipboard'
            };

            successMessage.textContent = method === 'copy_link'
                ? methodNames[method]
                : `Job shared via ${methodNames[method]}!`;

            successAlert.classList.remove('d-none');

            // Hide after 3 seconds
            setTimeout(() => {
                successAlert.classList.add('d-none');
            }, 3000);
        }
    }

    showCopySuccess() {
        this.showShareSuccess('copy_link');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new JobActions();
});

// Export for potential use in other scripts
window.JobActions = JobActions;