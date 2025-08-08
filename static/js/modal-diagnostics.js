/**
 * Modal Diagnostics Utility
 * Comprehensive diagnostic tools for identifying modal stability issues
 */

const ModalDiagnostics = {
    
    /**
     * Check for duplicate IDs in the document
     * @returns {Array} Array of duplicate ID objects
     */
    checkForDuplicateIds: function() {
        const ids = {};
        const duplicates = [];
        
        // Get all elements with IDs
        const elementsWithIds = document.querySelectorAll('[id]');
        
        elementsWithIds.forEach(element => {
            const id = element.id;
            if (ids[id]) {
                duplicates.push({
                    id: id,
                    elements: [ids[id], element],
                    count: ids[id].count ? ids[id].count + 1 : 2
                });
                ids[id].count = ids[id].count ? ids[id].count + 1 : 2;
            } else {
                ids[id] = element;
            }
        });
        
        return duplicates;
    },

    /**
     * Analyze event handlers attached to modal elements
     * @returns {Object} Event handler analysis
     */
    analyzeEventHandlers: function() {
        const analysis = {
            modalTriggers: [],
            modalElements: [],
            eventConflicts: []
        };
        
        // Find all modal trigger buttons
        const triggers = document.querySelectorAll('[data-toggle="modal"]');
        triggers.forEach(trigger => {
            const targetModal = trigger.getAttribute('data-target');
            const events = this.getElementEvents(trigger);
            
            analysis.modalTriggers.push({
                element: trigger,
                target: targetModal,
                events: events,
                hasMultipleClickHandlers: events.click && events.click.length > 1
            });
        });
        
        // Find all modal elements
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            const events = this.getElementEvents(modal);
            const bootstrapData = modal._modal || null;
            
            analysis.modalElements.push({
                element: modal,
                id: modal.id,
                events: events,
                bootstrapInstance: bootstrapData,
                isInitialized: !!bootstrapData
            });
        });
        
        return analysis;
    },

    /**
     * Get events attached to an element (simplified version)
     * @param {Element} element 
     * @returns {Object} Events object
     */
    getElementEvents: function(element) {
        // This is a simplified version - in reality, getting all events is complex
        const events = {};
        
        // Check for common event attributes
        ['onclick', 'onshow', 'onhide', 'onshown', 'onhidden'].forEach(attr => {
            if (element[attr]) {
                events[attr.substring(2)] = [element[attr]];
            }
        });
        
        return events;
    },

    /**
     * Validate Bootstrap integration
     * @returns {Object} Bootstrap validation results
     */
    validateBootstrapIntegration: function() {
        const validation = {
            jqueryLoaded: typeof jQuery !== 'undefined',
            bootstrapLoaded: typeof jQuery !== 'undefined' && typeof jQuery.fn.modal !== 'undefined',
            jqueryVersion: typeof jQuery !== 'undefined' ? jQuery.fn.jquery : null,
            bootstrapVersion: null,
            modalPlugin: typeof jQuery !== 'undefined' && typeof jQuery.fn.modal !== 'undefined',
            issues: []
        };
        
        // Try to detect Bootstrap version
        if (validation.bootstrapLoaded) {
            try {
                // Bootstrap 4/5 version detection
                if (jQuery.fn.modal.Constructor && jQuery.fn.modal.Constructor.VERSION) {
                    validation.bootstrapVersion = jQuery.fn.modal.Constructor.VERSION;
                }
            } catch (e) {
                validation.issues.push('Could not detect Bootstrap version: ' + e.message);
            }
        }
        
        // Check for common issues
        if (!validation.jqueryLoaded) {
            validation.issues.push('jQuery is not loaded');
        }
        
        if (!validation.bootstrapLoaded) {
            validation.issues.push('Bootstrap modal plugin is not loaded');
        }
        
        if (validation.jqueryLoaded && validation.bootstrapLoaded) {
            // Check for version compatibility
            const jqVersion = validation.jqueryVersion.split('.');
            const majorVersion = parseInt(jqVersion[0]);
            
            if (majorVersion < 3) {
                validation.issues.push('jQuery version may be too old for Bootstrap 4/5');
            }
        }
        
        return validation;
    },

    /**
     * Detect CSS conflicts that might affect modals
     * @returns {Array} Array of potential CSS conflicts
     */
    detectCSSConflicts: function() {
        const conflicts = [];
        
        // Check for common conflicting CSS properties on modal elements
        const modals = document.querySelectorAll('.modal');
        
        modals.forEach(modal => {
            const computedStyle = window.getComputedStyle(modal);
            const modalDialog = modal.querySelector('.modal-dialog');
            const dialogStyle = modalDialog ? window.getComputedStyle(modalDialog) : null;
            
            // Check for problematic CSS properties
            const checks = [
                {
                    property: 'transform',
                    element: modal,
                    style: computedStyle,
                    issue: 'Custom transforms can interfere with modal positioning'
                },
                {
                    property: 'transition',
                    element: modal,
                    style: computedStyle,
                    issue: 'Custom transitions can conflict with Bootstrap modal animations'
                },
                {
                    property: 'z-index',
                    element: modal,
                    style: computedStyle,
                    issue: 'Incorrect z-index can cause modal layering issues'
                }
            ];
            
            if (dialogStyle) {
                checks.push({
                    property: 'transform',
                    element: modalDialog,
                    style: dialogStyle,
                    issue: 'Custom transforms on modal-dialog can cause positioning issues'
                });
            }
            
            checks.forEach(check => {
                const value = check.style.getPropertyValue(check.property);
                if (value && value !== 'none' && value !== 'auto' && value !== 'initial') {
                    conflicts.push({
                        element: check.element,
                        property: check.property,
                        value: value,
                        issue: check.issue,
                        modalId: modal.id
                    });
                }
            });
        });
        
        return conflicts;
    },

    /**
     * Log modal events for debugging
     * @param {string} modalId - ID of the modal to monitor
     */
    logModalEvents: function(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error('Modal not found:', modalId);
            return;
        }
        
        const events = ['show.bs.modal', 'shown.bs.modal', 'hide.bs.modal', 'hidden.bs.modal'];
        
        events.forEach(eventName => {
            jQuery(modal).on(eventName, function(e) {
                console.log(`[Modal Event] ${eventName} on ${modalId}`, {
                    timestamp: new Date().toISOString(),
                    event: e,
                    modalElement: this,
                    relatedTarget: e.relatedTarget
                });
            });
        });
        
        console.log(`Modal event logging enabled for: ${modalId}`);
    },

    /**
     * Run comprehensive modal diagnostics
     * @returns {Object} Complete diagnostic report
     */
    runFullDiagnostics: function() {
        console.log('🔍 Running Modal Diagnostics...');
        
        const report = {
            timestamp: new Date().toISOString(),
            duplicateIds: this.checkForDuplicateIds(),
            eventHandlers: this.analyzeEventHandlers(),
            bootstrapValidation: this.validateBootstrapIntegration(),
            cssConflicts: this.detectCSSConflicts(),
            recommendations: []
        };
        
        // Generate recommendations based on findings
        if (report.duplicateIds.length > 0) {
            report.recommendations.push('Fix duplicate IDs - they can cause JavaScript conflicts');
        }
        
        if (report.bootstrapValidation.issues.length > 0) {
            report.recommendations.push('Resolve Bootstrap integration issues');
        }
        
        if (report.cssConflicts.length > 0) {
            report.recommendations.push('Review and resolve CSS conflicts affecting modals');
        }
        
        // Log detailed report
        console.group('📊 Modal Diagnostic Report');
        console.log('Duplicate IDs:', report.duplicateIds);
        console.log('Event Handlers:', report.eventHandlers);
        console.log('Bootstrap Validation:', report.bootstrapValidation);
        console.log('CSS Conflicts:', report.cssConflicts);
        console.log('Recommendations:', report.recommendations);
        console.groupEnd();
        
        return report;
    },

    /**
     * Monitor all modals for stability issues
     */
    monitorAllModals: function() {
        const modals = document.querySelectorAll('.modal');
        
        modals.forEach(modal => {
            if (modal.id) {
                this.logModalEvents(modal.id);
            }
        });
        
        console.log(`🔍 Monitoring ${modals.length} modals for stability issues`);
    },

    /**
     * Test modal functionality
     * @param {string} modalId - ID of modal to test
     */
    testModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error('Modal not found:', modalId);
            return;
        }
        
        console.log(`🧪 Testing modal: ${modalId}`);
        
        try {
            // Test show
            jQuery(modal).modal('show');
            
            setTimeout(() => {
                // Test hide
                jQuery(modal).modal('hide');
                console.log(`✅ Modal ${modalId} test completed`);
            }, 1000);
            
        } catch (error) {
            console.error(`❌ Modal ${modalId} test failed:`, error);
        }
    }
};

// Auto-run diagnostics when script loads
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for all scripts to load
    setTimeout(() => {
        if (window.location.pathname.includes('cv') || window.location.pathname.includes('resume')) {
            console.log('🚀 CV Editor detected - running modal diagnostics');
            ModalDiagnostics.runFullDiagnostics();
            ModalDiagnostics.monitorAllModals();
        }
    }, 1000);
});

// Make available globally for manual testing
window.ModalDiagnostics = ModalDiagnostics;