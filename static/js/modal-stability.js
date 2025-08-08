/**
 * Modal Stability Manager
 * Ensures proper Bootstrap modal initialization and prevents blinking issues
 */

(function($) {
    'use strict';

    // Modal Stability Manager
    const ModalStabilityManager = {
        
        // Configuration
        config: {
            debug: false,
            retryAttempts: 3,
            retryDelay: 100,
            animationDuration: 150
        },

        // Initialize the modal stability system
        init: function() {
            this.log('🚀 Initializing Modal Stability Manager');
            
            // Wait for DOM and Bootstrap to be ready
            this.waitForBootstrap(() => {
                this.setupModalStability();
                this.bindGlobalEventHandlers();
                this.preventConflicts();
                this.log('✅ Modal Stability Manager initialized successfully');
            });
        },

        // Wait for Bootstrap to be available
        waitForBootstrap: function(callback, attempts = 0) {
            if (typeof $ !== 'undefined' && typeof $.fn.modal !== 'undefined') {
                callback();
            } else if (attempts < this.config.retryAttempts) {
                this.log(`⏳ Waiting for Bootstrap... (attempt ${attempts + 1})`);
                setTimeout(() => {
                    this.waitForBootstrap(callback, attempts + 1);
                }, this.config.retryDelay);
            } else {
                console.error('❌ Bootstrap modal plugin not found after maximum attempts');
            }
        },

        // Setup modal stability for all modals
        setupModalStability: function() {
            const modals = $('.modal');
            this.log(`🔧 Setting up stability for ${modals.length} modals`);

            modals.each((index, modal) => {
                this.initializeModal($(modal));
            });
        },

        // Initialize individual modal
        initializeModal: function($modal) {
            const modalId = $modal.attr('id');
            this.log(`🔧 Initializing modal: ${modalId}`);

            try {
                // Ensure modal is properly configured
                this.configureModal($modal);
                
                // Bind modal-specific event handlers
                this.bindModalEvents($modal);
                
                // Prevent duplicate initialization
                $modal.data('stability-initialized', true);
                
                this.log(`✅ Modal initialized: ${modalId}`);
            } catch (error) {
                console.error(`❌ Failed to initialize modal ${modalId}:`, error);
            }
        },

        // Configure modal settings
        configureModal: function($modal) {
            const modalId = $modal.attr('id');
            
            // CRITICAL: Ensure proper modal configuration to prevent dual positioning
            const config = {
                backdrop: 'static', // Prevent accidental closure
                keyboard: true,     // Allow ESC key
                focus: true,        // Focus on modal when shown
                show: false         // Don't show immediately
            };

            // CRITICAL: Force single positioning context
            $modal.css({
                'position': 'fixed',
                'top': '0',
                'left': '0',
                'z-index': '1050',
                'transform': 'none',
                'transition': 'none'
            });

            // Initialize or reconfigure the modal
            try {
                $modal.modal(config);
            } catch (error) {
                this.log(`⚠️ Modal configuration warning for ${modalId}:`, error);
            }
        },

        // Bind modal-specific event handlers
        bindModalEvents: function($modal) {
            const modalId = $modal.attr('id');

            // Remove any existing event handlers to prevent duplicates
            $modal.off('.stability');

            // Bind stability event handlers
            $modal.on('show.bs.modal.stability', (e) => {
                this.handleModalShow(e, $modal);
            });

            $modal.on('shown.bs.modal.stability', (e) => {
                this.handleModalShown(e, $modal);
            });

            $modal.on('hide.bs.modal.stability', (e) => {
                this.handleModalHide(e, $modal);
            });

            $modal.on('hidden.bs.modal.stability', (e) => {
                this.handleModalHidden(e, $modal);
            });

            this.log(`🔗 Event handlers bound for modal: ${modalId}`);
        },

        // Handle modal show event
        handleModalShow: function(e, $modal) {
            const modalId = $modal.attr('id');
            this.log(`📖 Modal showing: ${modalId}`);

            // Prevent body scroll
            $('body').addClass('modal-open');
            
            // Ensure proper z-index
            $modal.css('z-index', 1050);
            
            // Clear any conflicting animations
            $modal.find('*').css('animation', 'none');
        },

        // Handle modal shown event
        handleModalShown: function(e, $modal) {
            const modalId = $modal.attr('id');
            this.log(`✅ Modal shown: ${modalId}`);

            // Focus on first input field
            setTimeout(() => {
                $modal.find('input, textarea, select').filter(':visible').first().focus();
            }, 100);
        },

        // Handle modal hide event
        handleModalHide: function(e, $modal) {
            const modalId = $modal.attr('id');
            this.log(`📕 Modal hiding: ${modalId}`);
        },

        // Handle modal hidden event
        handleModalHidden: function(e, $modal) {
            const modalId = $modal.attr('id');
            this.log(`✅ Modal hidden: ${modalId}`);

            // Clean up any modal-specific styles
            $modal.removeAttr('style');
            
            // Ensure body scroll is restored if no other modals are open
            if ($('.modal.show').length === 0) {
                $('body').removeClass('modal-open');
            }
        },

        // Bind global event handlers
        bindGlobalEventHandlers: function() {
            this.log('🌐 Binding global event handlers');

            // Handle modal trigger clicks
            $(document).off('click.stability', '[data-toggle="modal"]');
            $(document).on('click.stability', '[data-toggle="modal"]', (e) => {
                this.handleModalTrigger(e);
            });

            // Handle backdrop clicks
            $(document).off('click.stability', '.modal');
            $(document).on('click.stability', '.modal', (e) => {
                if (e.target === e.currentTarget) {
                    // Clicked on backdrop
                    const $modal = $(e.currentTarget);
                    if ($modal.data('bs.modal') && $modal.data('bs.modal')._config.backdrop !== 'static') {
                        $modal.modal('hide');
                    }
                }
            });
        },

        // Handle modal trigger clicks
        handleModalTrigger: function(e) {
            const $trigger = $(e.currentTarget);
            const targetSelector = $trigger.data('target') || $trigger.attr('href');
            const $targetModal = $(targetSelector);

            if ($targetModal.length === 0) {
                console.error(`❌ Modal target not found: ${targetSelector}`);
                return;
            }

            this.log(`🎯 Modal trigger clicked: ${targetSelector}`);

            // Prevent default action
            e.preventDefault();
            e.stopPropagation();

            // Ensure modal is initialized
            if (!$targetModal.data('stability-initialized')) {
                this.initializeModal($targetModal);
            }

            // Show the modal with a slight delay to prevent conflicts
            setTimeout(() => {
                try {
                    $targetModal.modal('show');
                } catch (error) {
                    console.error(`❌ Failed to show modal ${targetSelector}:`, error);
                }
            }, 10);
        },

        // Prevent conflicts with other scripts
        preventConflicts: function() {
            this.log('🛡️ Setting up conflict prevention');

            // Prevent multiple modal instances
            $('.modal').each(function() {
                const $modal = $(this);
                const modalId = $modal.attr('id');
                
                // Remove any duplicate modals
                const duplicates = $(`.modal[id="${modalId}"]`);
                if (duplicates.length > 1) {
                    console.warn(`⚠️ Found ${duplicates.length} modals with ID: ${modalId}`);
                    duplicates.slice(1).remove(); // Remove duplicates, keep first
                }
            });

            // Override any conflicting CSS animations
            $('<style>')
                .prop('type', 'text/css')
                .html(`
                    .modal * {
                        animation: none !important;
                        transition: none !important;
                    }
                    .modal.fade {
                        transition: opacity 0.15s linear !important;
                    }
                    .modal.fade .modal-dialog {
                        transition: transform 0.15s ease-out !important;
                    }
                `)
                .appendTo('head');
        },

        // Utility: Enhanced logging
        log: function(message, data = null) {
            if (this.config.debug || window.location.search.includes('modal-debug')) {
                const timestamp = new Date().toISOString().substr(11, 12);
                console.log(`[${timestamp}] ${message}`, data || '');
            }
        },

        // Public API: Manually show modal
        showModal: function(modalId) {
            const $modal = $(`#${modalId}`);
            if ($modal.length) {
                if (!$modal.data('stability-initialized')) {
                    this.initializeModal($modal);
                }
                $modal.modal('show');
            } else {
                console.error(`❌ Modal not found: ${modalId}`);
            }
        },

        // Public API: Manually hide modal
        hideModal: function(modalId) {
            const $modal = $(`#${modalId}`);
            if ($modal.length) {
                $modal.modal('hide');
            } else {
                console.error(`❌ Modal not found: ${modalId}`);
            }
        },

        // Public API: Get modal status
        getModalStatus: function(modalId) {
            const $modal = $(`#${modalId}`);
            if ($modal.length) {
                return {
                    exists: true,
                    initialized: $modal.data('stability-initialized') || false,
                    visible: $modal.hasClass('show'),
                    bootstrapInstance: $modal.data('bs.modal') || null
                };
            }
            return { exists: false };
        },

        // Public API: Reinitialize all modals
        reinitialize: function() {
            this.log('🔄 Reinitializing all modals');
            $('.modal').removeData('stability-initialized');
            this.setupModalStability();
        }
    };

    // Auto-initialize when DOM is ready
    $(document).ready(function() {
        // Enable debug mode for CV pages
        if (window.location.pathname.includes('cv') || window.location.pathname.includes('resume')) {
            ModalStabilityManager.config.debug = true;
        }
        
        // Initialize with a slight delay to ensure all scripts are loaded
        setTimeout(() => {
            ModalStabilityManager.init();
        }, 100);
    });

    // Make available globally
    window.ModalStabilityManager = ModalStabilityManager;

})(jQuery);