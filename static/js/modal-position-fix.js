/**
 * Modal Position Fix
 * Prevents modals from appearing in multiple locations simultaneously
 */

(function($) {
    'use strict';

    // Modal Position Fix Manager
    const ModalPositionFix = {
        
        // Initialize the position fix system
        init: function() {
            console.log('🎯 Initializing Modal Position Fix');
            
            // Wait for DOM to be ready
            $(document).ready(() => {
                this.enforceModalPositioning();
                this.preventDualPositioning();
                this.bindPositionEvents();
                console.log('✅ Modal Position Fix initialized');
            });
        },

        // Enforce consistent modal positioning
        enforceModalPositioning: function() {
            const modals = $('.modal');
            console.log(`🔧 Enforcing positioning for ${modals.length} modals`);

            modals.each((index, modal) => {
                const $modal = $(modal);
                const modalId = $modal.attr('id');
                
                // CRITICAL: Force single positioning context
                $modal.css({
                    'position': 'fixed !important',
                    'top': '0 !important',
                    'left': '0 !important',
                    'right': 'auto !important',
                    'bottom': 'auto !important',
                    'z-index': '1050 !important',
                    'transform': 'none !important',
                    'transition': 'none !important',
                    'animation': 'none !important'
                });

                // Force modal-dialog positioning
                const $dialog = $modal.find('.modal-dialog');
                if ($dialog.length) {
                    $dialog.css({
                        'position': 'relative !important',
                        'transform': 'none !important',
                        'transition': 'none !important',
                        'animation': 'none !important',
                        'margin': '1.75rem auto !important'
                    });
                }

                console.log(`✅ Position enforced for modal: ${modalId}`);
            });
        },

        // Prevent dual positioning conflicts
        preventDualPositioning: function() {
            console.log('🛡️ Preventing dual positioning conflicts');

            // Remove any conflicting CSS classes
            $('.modal').removeClass('fade');
            
            // Override Bootstrap's default modal positioning
            $('<style id="modal-position-override">')
                .prop('type', 'text/css')
                .html(`
                    /* CRITICAL: Override all modal positioning conflicts */
                    .modal {
                        position: fixed !important;
                        top: 0 !important;
                        left: 0 !important;
                        z-index: 1050 !important;
                        width: 100% !important;
                        height: 100% !important;
                        transform: none !important;
                        transition: none !important;
                        animation: none !important;
                        opacity: 1 !important;
                        display: none;
                    }
                    
                    .modal.show {
                        display: block !important;
                        opacity: 1 !important;
                    }
                    
                    .modal-dialog {
                        position: relative !important;
                        transform: none !important;
                        transition: none !important;
                        animation: none !important;
                        margin: 1.75rem auto !important;
                        max-width: 500px !important;
                    }
                    
                    .modal-content {
                        transform: none !important;
                        transition: none !important;
                        animation: none !important;
                    }
                    
                    /* Prevent any fade or animation effects */
                    .modal.fade,
                    .modal.fade .modal-dialog,
                    .modal * {
                        animation: none !important;
                        transition: none !important;
                        transform: none !important;
                    }
                    
                    /* Force backdrop positioning */
                    .modal-backdrop {
                        position: fixed !important;
                        top: 0 !important;
                        left: 0 !important;
                        z-index: 1040 !important;
                        width: 100vw !important;
                        height: 100vh !important;
                    }
                `)
                .appendTo('head');
        },

        // Bind position-related events
        bindPositionEvents: function() {
            console.log('🔗 Binding position events');

            // Override modal show events to enforce positioning
            $(document).on('show.bs.modal', '.modal', (e) => {
                const $modal = $(e.currentTarget);
                const modalId = $modal.attr('id');
                
                console.log(`🎯 Enforcing position for showing modal: ${modalId}`);
                
                // Force positioning before show
                setTimeout(() => {
                    $modal.css({
                        'position': 'fixed',
                        'top': '0',
                        'left': '0',
                        'z-index': '1050',
                        'transform': 'none',
                        'transition': 'none'
                    });
                }, 1);
            });

            // Override modal shown events to verify positioning
            $(document).on('shown.bs.modal', '.modal', (e) => {
                const $modal = $(e.currentTarget);
                const modalId = $modal.attr('id');
                
                console.log(`✅ Modal shown with stable position: ${modalId}`);
                
                // Verify positioning is correct
                const position = $modal.css('position');
                const top = $modal.css('top');
                const left = $modal.css('left');
                
                if (position !== 'fixed' || top !== '0px' || left !== '0px') {
                    console.warn(`⚠️ Position correction needed for ${modalId}`);
                    $modal.css({
                        'position': 'fixed',
                        'top': '0',
                        'left': '0',
                        'z-index': '1050'
                    });
                }
            });

            // Handle modal trigger clicks with position enforcement
            $(document).on('click', '[data-toggle="modal"]', (e) => {
                const $trigger = $(e.currentTarget);
                const targetSelector = $trigger.data('target');
                const $targetModal = $(targetSelector);
                
                if ($targetModal.length) {
                    console.log(`🎯 Pre-enforcing position for: ${targetSelector}`);
                    
                    // Pre-enforce positioning before Bootstrap handles the click
                    $targetModal.css({
                        'position': 'fixed',
                        'top': '0',
                        'left': '0',
                        'z-index': '1050',
                        'transform': 'none',
                        'transition': 'none'
                    });
                }
            });
        },

        // Public API: Fix specific modal position
        fixModalPosition: function(modalId) {
            const $modal = $(`#${modalId}`);
            if ($modal.length) {
                console.log(`🔧 Fixing position for modal: ${modalId}`);
                
                $modal.css({
                    'position': 'fixed !important',
                    'top': '0 !important',
                    'left': '0 !important',
                    'z-index': '1050 !important',
                    'transform': 'none !important',
                    'transition': 'none !important'
                });
                
                const $dialog = $modal.find('.modal-dialog');
                if ($dialog.length) {
                    $dialog.css({
                        'transform': 'none !important',
                        'transition': 'none !important'
                    });
                }
                
                console.log(`✅ Position fixed for modal: ${modalId}`);
            } else {
                console.error(`❌ Modal not found: ${modalId}`);
            }
        },

        // Public API: Fix all modal positions
        fixAllModalPositions: function() {
            console.log('🔧 Fixing all modal positions');
            this.enforceModalPositioning();
            this.preventDualPositioning();
        }
    };

    // Auto-initialize
    ModalPositionFix.init();

    // Make available globally
    window.ModalPositionFix = ModalPositionFix;

})(jQuery);