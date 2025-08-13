/**
 * Employer Applications Dashboard JavaScript
 * 
 * Handles the employer application management interface including:
 * - Filtering and sorting
 * - Bulk actions
 * - Application status updates
 * - Notes and ratings
 */

class ApplicationsDashboard {
    constructor() {
        this.data = window.applicationsData || {};
        this.selectedApplications = new Set();
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initializeFilters();
        this.updateBulkActionsVisibility();
    }
    
    bindEvents() {
        // Filter controls
        const applyFiltersBtn = document.getElementById('apply-filters');
        const clearFiltersBtn = document.getElementById('clear-filters');
        const clearFiltersEmptyBtn = document.getElementById('clear-filters-empty');
        
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }
        
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }
        
        if (clearFiltersEmptyBtn) {
            clearFiltersEmptyBtn.addEventListener('click', () => this.clearFilters());
        }
        
        // Select all checkbox
        const selectAllCheckbox = document.getElementById('select-all');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => this.handleSelectAll(e));
        }
        
        // Individual checkboxes
        const applicationCheckboxes = document.querySelectorAll('.application-checkbox');
        applicationCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.handleApplicationSelect(e));
        });
        
        // Bulk action buttons
        const bulkShortlistBtn = document.getElementById('bulk-shortlist');
        const bulkInterviewBtn = document.getElementById('bulk-interview');
        const bulkRejectBtn = document.getElementById('bulk-reject');
        const bulkExportBtn = document.getElementById('bulk-export');
        
        if (bulkShortlistBtn) {
            bulkShortlistBtn.addEventListener('click', () => this.handleBulkAction('shortlist'));
        }
        
        if (bulkInterviewBtn) {
            bulkInterviewBtn.addEventListener('click', () => this.handleBulkAction('interview'));
        }
        
        if (bulkRejectBtn) {
            bulkRejectBtn.addEventListener('click', () => this.handleBulkAction('reject'));
        }
        
        if (bulkExportBtn) {
            bulkExportBtn.addEventListener('click', () => this.handleBulkExport());
        }
        
        // Notes modal
        const saveNotesBtn = document.getElementById('save-notes');
        if (saveNotesBtn) {
            saveNotesBtn.addEventListener('click', () => this.saveNotes());
        }
        
        // Auto-apply filters on change
        const filterSelects = document.querySelectorAll('#job-filter, #status-filter, #date-filter, #quality-filter, #sort-by');
        filterSelects.forEach(select => {
            select.addEventListener('change', () => {
                // Debounce the filter application
                clearTimeout(this.filterTimeout);
                this.filterTimeout = setTimeout(() => this.applyFilters(), 500);
            });
        });
    }
    
    initializeFilters() {
        // Set filter values from URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        
        const filters = ['job_id', 'status', 'date_range', 'quality_score', 'sort_by'];
        filters.forEach(filter => {
            const value = urlParams.get(filter);
            const element = document.getElementById(filter.replace('_', '-') + (filter === 'sort_by' ? '' : '-filter'));
            if (element && value) {
                element.value = value;
            }
        });
    }
    
    applyFilters() {
        const filters = {
            job_id: document.getElementById('job-filter').value,
            status: document.getElementById('status-filter').value,
            date_range: document.getElementById('date-filter').value,
            quality_score: document.getElementById('quality-filter').value,
            sort_by: document.getElementById('sort-by').value
        };
        
        // Build query string
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value) {
                params.append(key, value);
            }
        });
        
        // Update URL and reload
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.location.href = newUrl;
    }
    
    clearFilters() {
        // Clear all filter selects
        document.getElementById('job-filter').value = '';
        document.getElementById('status-filter').value = '';
        document.getElementById('date-filter').value = '';
        document.getElementById('quality-filter').value = '';
        document.getElementById('sort-by').value = 'date_desc';
        
        // Redirect to clean URL
        window.location.href = window.location.pathname;
    }
    
    handleSelectAll(event) {
        const isChecked = event.target.checked;
        const applicationCheckboxes = document.querySelectorAll('.application-checkbox');
        
        applicationCheckboxes.forEach(checkbox => {
            checkbox.checked = isChecked;
            const applicationId = checkbox.value;
            
            if (isChecked) {
                this.selectedApplications.add(applicationId);
            } else {
                this.selectedApplications.delete(applicationId);
            }
        });
        
        this.updateBulkActionsVisibility();
    }
    
    handleApplicationSelect(event) {
        const applicationId = event.target.value;
        const isChecked = event.target.checked;
        
        if (isChecked) {
            this.selectedApplications.add(applicationId);
        } else {
            this.selectedApplications.delete(applicationId);
        }
        
        // Update select all checkbox
        const selectAllCheckbox = document.getElementById('select-all');
        const applicationCheckboxes = document.querySelectorAll('.application-checkbox');
        const checkedCount = document.querySelectorAll('.application-checkbox:checked').length;
        
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = checkedCount === applicationCheckboxes.length;
            selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < applicationCheckboxes.length;
        }
        
        this.updateBulkActionsVisibility();
    }
    
    updateBulkActionsVisibility() {
        const bulkActions = document.getElementById('bulk-actions');
        const selectedCount = document.getElementById('selected-count');
        
        if (this.selectedApplications.size > 0) {
            bulkActions.style.display = 'block';
            selectedCount.textContent = this.selectedApplications.size;
        } else {
            bulkActions.style.display = 'none';
        }
    }
    
    async handleBulkAction(action) {
        if (this.selectedApplications.size === 0) {
            this.showError('Please select applications first');
            return;
        }
        
        const actionText = action === 'shortlist' ? 'shortlist' : 
                          action === 'interview' ? 'schedule interviews for' : 'reject';
        
        if (!confirm(`Are you sure you want to ${actionText} ${this.selectedApplications.size} application(s)?`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/employers/applications/bulk-action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    action: action,
                    application_ids: Array.from(this.selectedApplications)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess(`Successfully ${actionText}ed ${result.updated_count} application(s)`);
                
                // Refresh the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.showError(result.message || `Failed to ${action} applications`);
            }
        } catch (error) {
            console.error('Error performing bulk action:', error);
            this.showError('An error occurred while processing the bulk action');
        }
    }
    
    async handleBulkExport() {
        if (this.selectedApplications.size === 0) {
            this.showError('Please select applications to export');
            return;
        }
        
        try {
            const response = await fetch('/api/employers/applications/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    application_ids: Array.from(this.selectedApplications),
                    format: 'csv'
                })
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `applications_export_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showSuccess('Applications exported successfully');
            } else {
                this.showError('Failed to export applications');
            }
        } catch (error) {
            console.error('Error exporting applications:', error);
            this.showError('An error occurred while exporting applications');
        }
    }
    
    saveNotes() {
        const applicationId = document.getElementById('notes-application-id').value;
        const notes = document.getElementById('application-notes').value;
        const rating = document.getElementById('application-rating').value;
        
        if (!applicationId) {
            this.showError('Application ID not found');
            return;
        }
        
        this.updateApplicationNotes(applicationId, notes, rating);
    }
    
    async updateApplicationNotes(applicationId, notes, rating) {
        try {
            const response = await fetch(`/api/employers/applications/${applicationId}/notes`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    notes: notes,
                    rating: rating ? parseInt(rating) : null
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Notes saved successfully');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('notesModal'));
                modal.hide();
            } else {
                this.showError(result.message || 'Failed to save notes');
            }
        } catch (error) {
            console.error('Error saving notes:', error);
            this.showError('An error occurred while saving notes');
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

// Global functions for template onclick handlers
function viewApplication(applicationId) {
    window.location.href = `/employers/applications/${applicationId}`;
}

async function shortlistApplication(applicationId) {
    if (!confirm('Are you sure you want to shortlist this application?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/employers/applications/${applicationId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                status: 'shortlisted'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update the status badge in the table
            const row = document.querySelector(`[data-application-id="${applicationId}"]`);
            if (row) {
                const statusCell = row.querySelector('.application-status');
                statusCell.innerHTML = `
                    <span class="status-badge status-shortlisted">
                        <i class="fas fa-star"></i>Shortlisted
                    </span>
                `;
            }
            
            dashboard.showSuccess('Application shortlisted successfully');
        } else {
            dashboard.showError(result.message || 'Failed to shortlist application');
        }
    } catch (error) {
        console.error('Error shortlisting application:', error);
        dashboard.showError('An error occurred while shortlisting the application');
    }
}

async function scheduleInterview(applicationId) {
    // For now, just update status to interview
    // In a full implementation, this would open a scheduling modal
    try {
        const response = await fetch(`/api/employers/applications/${applicationId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                status: 'interview'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update the status badge in the table
            const row = document.querySelector(`[data-application-id="${applicationId}"]`);
            if (row) {
                const statusCell = row.querySelector('.application-status');
                statusCell.innerHTML = `
                    <span class="status-badge status-interview">
                        <i class="fas fa-calendar"></i>Interview
                    </span>
                `;
            }
            
            dashboard.showSuccess('Application moved to interview stage');
        } else {
            dashboard.showError(result.message || 'Failed to schedule interview');
        }
    } catch (error) {
        console.error('Error scheduling interview:', error);
        dashboard.showError('An error occurred while scheduling the interview');
    }
}

async function rejectApplication(applicationId) {
    if (!confirm('Are you sure you want to reject this application? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/employers/applications/${applicationId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                status: 'rejected'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update the status badge in the table
            const row = document.querySelector(`[data-application-id="${applicationId}"]`);
            if (row) {
                const statusCell = row.querySelector('.application-status');
                statusCell.innerHTML = `
                    <span class="status-badge status-rejected">
                        <i class="fas fa-times"></i>Rejected
                    </span>
                `;
            }
            
            dashboard.showSuccess('Application rejected');
        } else {
            dashboard.showError(result.message || 'Failed to reject application');
        }
    } catch (error) {
        console.error('Error rejecting application:', error);
        dashboard.showError('An error occurred while rejecting the application');
    }
}

function downloadCV(applicationId) {
    window.open(`/api/employers/applications/${applicationId}/cv/download`, '_blank');
}

function addNotes(applicationId) {
    // Set the application ID in the modal
    document.getElementById('notes-application-id').value = applicationId;
    
    // Clear previous values
    document.getElementById('application-notes').value = '';
    document.getElementById('application-rating').value = '';
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('notesModal'));
    modal.show();
}

// Initialize dashboard when DOM is loaded
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new ApplicationsDashboard();
});