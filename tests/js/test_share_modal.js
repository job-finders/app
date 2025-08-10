/**
 * JavaScript Tests for Share Modal Functionality
 *
 * Tests for share modal component including:
 * - Modal open/close behavior
 * - Social media sharing
 * - Email sharing
 * - Copy to clipboard
 * - Responsive design
 * - Accessibility features
 */

// Mock DOM and global objects
global.document = {
    getElementById: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(),
    createElement: jest.fn(),
    body: {
        classList: {
            add: jest.fn(),
            remove: jest.fn()
        }
    },
    addEventListener: jest.fn(),
    execCommand: jest.fn()
};

global.window = {
    location: {
        href: 'https://jobfinders.site/jobs/test-job-123',
        origin: 'https://jobfinders.site'
    },
    open: jest.fn(),
    navigator: {
        share: jest.fn(),
        clipboard: {
            writeText: jest.fn()
        }
    },
    encodeURIComponent: encodeURIComponent
};

global.fetch = jest.fn();

// Import share modal functions
const {
    openShareModal,
    closeShareModal,
    shareViaEmail,
    shareViaLinkedIn,
    shareViaTwitter,
    shareViaFacebook,
    shareViaWhatsApp,
    copyJobUrl,
    initializeShareModal,
    generateShareUrl,
    trackShareEvent
} = require('../../static/js/components/share-modal.js');

describe('Share Modal Tests', () => {

    let mockModal, mockOverlay, mockCloseButton, mockJobTitle, mockJobUrl;

    beforeEach(() => {
        jest.clearAllMocks();

        // Mock modal elements
        mockModal = {
            id: 'shareModal',
            style: {display: 'none'},
            classList: {
                add: jest.fn(),
                remove: jest.fn(),
                contains: jest.fn()
            },
            addEventListener: jest.fn(),
            querySelector: jest.fn(),
            querySelectorAll: jest.fn()
        };

        mockOverlay = {
            addEventListener: jest.fn()
        };

        mockCloseButton = {
            addEventListener: jest.fn()
        };

        mockJobTitle = {
            textContent: ''
        };

        mockJobUrl = {
            value: '',
            select: jest.fn(),
            setSelectionRange: jest.fn()
        };

        // Setup DOM element mocks
        document.getElementById.mockImplementation((id) => {
            switch (id) {
                case 'shareModal':
                    return mockModal;
                case 'shareModalOverlay':
                    return mockOverlay;
                case 'shareModalClose':
                    return mockCloseButton;
                case 'shareJobTitle':
                    return mockJobTitle;
                case 'shareJobUrl':
                    return mockJobUrl;
                default:
                    return null;
            }
        });

        mockModal.querySelector.mockImplementation((selector) => {
            if (selector === '.modal-overlay') return mockOverlay;
            if (selector === '.close-button') return mockCloseButton;
            return null;
        });
    });

    describe('Modal Open/Close Behavior', () => {

        test('should open share modal with job details', () => {
            const jobData = {
                id: 'test-job-123',
                title: 'Senior Software Engineer',
                company: 'Tech Corp',
                url: 'https://jobfinders.site/jobs/test-job-123'
            };

            openShareModal(jobData);

            // Verify modal is shown
            expect(mockModal.style.display).toBe('flex');
            expect(mockModal.classList.add).toHaveBeenCalledWith('active');
            expect(document.body.classList.add).toHaveBeenCalledWith('modal-open');

            // Verify job details are populated
            expect(mockJobTitle.textContent).toBe('Senior Software Engineer');
            expect(mockJobUrl.value).toBe('https://jobfinders.site/jobs/test-job-123');
        });

        test('should close share modal', () => {
            // First open the modal
            openShareModal({id: 'test-job', title: 'Test Job'});

            closeShareModal();

            // Verify modal is hidden
            expect(mockModal.style.display).toBe('none');
            expect(mockModal.classList.remove).toHaveBeenCalledWith('active');
            expect(document.body.classList.remove).toHaveBeenCalledWith('modal-open');
        });

        test('should close modal when clicking overlay', () => {
            openShareModal({id: 'test-job', title: 'Test Job'});

            // Get the click handler for overlay
            const overlayClickHandler = mockOverlay.addEventListener.mock.calls
                .find(call => call[0] === 'click')[1];

            // Simulate overlay click
            overlayClickHandler({target: mockOverlay});

            expect(mockModal.style.display).toBe('none');
        });

        test('should close modal when clicking close button', () => {
            openShareModal({id: 'test-job', title: 'Test Job'});

            // Get the click handler for close button
            const closeClickHandler = mockCloseButton.addEventListener.mock.calls
                .find(call => call[0] === 'click')[1];

            // Simulate close button click
            closeClickHandler();

            expect(mockModal.style.display).toBe('none');
        });

        test('should close modal on Escape key press', () => {
            openShareModal({id: 'test-job', title: 'Test Job'});

            // Get the keydown handler
            const keydownHandler = document.addEventListener.mock.calls
                .find(call => call[0] === 'keydown')[1];

            // Simulate Escape key press
            keydownHandler({key: 'Escape'});

            expect(mockModal.style.display).toBe('none');
        });

        test('should prevent modal content clicks from closing modal', () => {
            const mockModalContent = {
                addEventListener: jest.fn()
            };

            mockModal.querySelector.mockReturnValue(mockModalContent);

            openShareModal({id: 'test-job', title: 'Test Job'});

            // Get the click handler for modal content
            const contentClickHandler = mockModalContent.addEventListener.mock.calls
                .find(call => call[0] === 'click')[1];

            const mockEvent = {
                stopPropagation: jest.fn()
            };

            // Simulate modal content click
            contentClickHandler(mockEvent);

            // Verify event propagation is stopped
            expect(mockEvent.stopPropagation).toHaveBeenCalled();

            // Modal should still be open
            expect(mockModal.style.display).toBe('flex');
        });
    });

    describe('Social Media Sharing', () => {

        const jobData = {
            id: 'test-job-123',
            title: 'Senior Software Engineer',
            company: 'Tech Corp',
            location: 'Cape Town',
            url: 'https://jobfinders.site/jobs/test-job-123'
        };

        test('should share via LinkedIn', async () => {
            // Mock successful share tracking
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true})
            });

            await shareViaLinkedIn(jobData);

            // Verify LinkedIn share URL is opened
            expect(window.open).toHaveBeenCalledWith(
                expect.stringContaining('linkedin.com/sharing/share-offsite'),
                '_blank',
                'width=600,height=400'
            );

            // Verify share tracking API call
            expect(fetch).toHaveBeenCalledWith(
                `/api/jobs/${jobData.id}/share`,
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({share_method: 'linkedin'})
                })
            );
        });

        test('should share via Twitter', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true})
            });

            await shareViaTwitter(jobData);

            // Verify Twitter share URL is opened
            expect(window.open).toHaveBeenCalledWith(
                expect.stringContaining('twitter.com/intent/tweet'),
                '_blank',
                'width=600,height=400'
            );

            // Verify share tracking
            expect(fetch).toHaveBeenCalledWith(
                `/api/jobs/${jobData.id}/share`,
                expect.objectContaining({
                    body: JSON.stringify({share_method: 'twitter'})
                })
            );
        });

        test('should share via Facebook', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true})
            });

            await shareViaFacebook(jobData);

            // Verify Facebook share URL is opened
            expect(window.open).toHaveBeenCalledWith(
                expect.stringContaining('facebook.com/sharer/sharer.php'),
                '_blank',
                'width=600,height=400'
            );

            // Verify share tracking
            expect(fetch).toHaveBeenCalledWith(
                `/api/jobs/${jobData.id}/share`,
                expect.objectContaining({
                    body: JSON.stringify({share_method: 'facebook'})
                })
            );
        });

        test('should share via WhatsApp', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true})
            });

            await shareViaWhatsApp(jobData);

            // Verify WhatsApp share URL is opened
            expect(window.open).toHaveBeenCalledWith(
                expect.stringContaining('wa.me'),
                '_blank'
            );

            // Verify share tracking
            expect(fetch).toHaveBeenCalledWith(
                `/api/jobs/${jobData.id}/share`,
                expect.objectContaining({
                    body: JSON.stringify({share_method: 'whatsapp'})
                })
            );
        });

        test('should handle share tracking errors gracefully', async () => {
            // Mock API error
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 500
            });

            await shareViaLinkedIn(jobData);

            // Should still open share window despite tracking error
            expect(window.open).toHaveBeenCalled();

            // Should log error
            expect(console.error).toHaveBeenCalled();
        });
    });

    describe('Email Sharing', () => {

        const jobData = {
            id: 'test-job-123',
            title: 'Senior Software Engineer',
            company: 'Tech Corp',
            location: 'Cape Town',
            url: 'https://jobfinders.site/jobs/test-job-123'
        };

        test('should generate email share with pre-populated content', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true})
            });

            await shareViaEmail(jobData);

            // Verify email client is opened with correct parameters
            const emailCall = window.open.mock.calls[0][0];

            expect(emailCall).toContain('mailto:');
            expect(emailCall).toContain('subject=');
            expect(emailCall).toContain('body=');
            expect(emailCall).toContain(encodeURIComponent(jobData.title));
            expect(emailCall).toContain(encodeURIComponent(jobData.company));
            expect(emailCall).toContain(encodeURIComponent(jobData.url));

            // Verify share tracking
            expect(fetch).toHaveBeenCalledWith(
                `/api/jobs/${jobData.id}/share`,
                expect.objectContaining({
                    body: JSON.stringify({share_method: 'email'})
                })
            );
        });

        test('should handle special characters in job title', async () => {
            const jobDataWithSpecialChars = {
                ...jobData,
                title: 'Senior C++ Developer & Team Lead',
                company: 'Tech & Innovation Corp'
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true})
            });

            await shareViaEmail(jobDataWithSpecialChars);

            // Verify special characters are properly encoded
            const emailCall = window.open.mock.calls[0][0];
            expect(emailCall).toContain(encodeURIComponent('Senior C++ Developer & Team Lead'));
            expect(emailCall).toContain(encodeURIComponent('Tech & Innovation Corp'));
        });
    });

    describe('Copy to Clipboard', () => {

        test('should copy job URL using modern clipboard API', async () => {
            window.navigator.clipboard.writeText.mockResolvedValueOnce();

            const result = await copyJobUrl('https://jobfinders.site/jobs/test-job-123');

            // Verify clipboard API was used
            expect(window.navigator.clipboard.writeText).toHaveBeenCalledWith(
                'https://jobfinders.site/jobs/test-job-123'
            );

            expect(result).toBe(true);
        });

        test('should fallback to legacy copy method when clipboard API unavailable', async () => {
            // Mock clipboard API not available
            window.navigator.clipboard = undefined;

            // Mock document methods for legacy copy
            const mockTextArea = {
                value: '',
                select: jest.fn(),
                setSelectionRange: jest.fn(),
                style: {}
            };

            document.createElement.mockReturnValue(mockTextArea);
            document.execCommand.mockReturnValue(true);

            const result = await copyJobUrl('https://jobfinders.site/jobs/test-job-123');

            // Verify legacy copy method was used
            expect(document.createElement).toHaveBeenCalledWith('textarea');
            expect(mockTextArea.value).toBe('https://jobfinders.site/jobs/test-job-123');
            expect(mockTextArea.select).toHaveBeenCalled();
            expect(document.execCommand).toHaveBeenCalledWith('copy');

            expect(result).toBe(true);
        });

        test('should handle copy failure gracefully', async () => {
            // Mock clipboard API failure
            window.navigator.clipboard.writeText.mockRejectedValueOnce(
                new Error('Clipboard access denied')
            );

            const result = await copyJobUrl('https://jobfinders.site/jobs/test-job-123');

            expect(result).toBe(false);
            expect(console.error).toHaveBeenCalled();
        });

        test('should show success feedback after copying', async () => {
            window.navigator.clipboard.writeText.mockResolvedValueOnce();

            // Mock toast notification function
            global.showToast = jest.fn();

            await copyJobUrl('https://jobfinders.site/jobs/test-job-123');

            // Verify success feedback is shown
            expect(global.showToast).toHaveBeenCalledWith(
                'Job URL copied to clipboard!',
                'success'
            );
        });
    });

    describe('Native Web Share API', () => {

        test('should use native share when available', async () => {
            // Mock Web Share API support
            window.navigator.share.mockResolvedValueOnce();

            const jobData = {
                id: 'test-job-123',
                title: 'Senior Software Engineer',
                company: 'Tech Corp',
                url: 'https://jobfinders.site/jobs/test-job-123'
            };

            const result = await shareViaWebAPI(jobData);

            // Verify native share was called
            expect(window.navigator.share).toHaveBeenCalledWith({
                title: `${jobData.title} at ${jobData.company}`,
                text: expect.stringContaining(jobData.title),
                url: jobData.url
            });

            expect(result).toBe(true);
        });

        test('should handle native share cancellation', async () => {
            // Mock user cancelling share
            window.navigator.share.mockRejectedValueOnce(
                new Error('AbortError')
            );

            const jobData = {
                id: 'test-job-123',
                title: 'Test Job',
                url: 'https://jobfinders.site/jobs/test-job-123'
            };

            const result = await shareViaWebAPI(jobData);

            // Should handle cancellation gracefully
            expect(result).toBe(false);
            expect(console.log).toHaveBeenCalledWith('Share cancelled by user');
        });

        test('should detect Web Share API support', () => {
            // Test with support
            window.navigator.share = jest.fn();
            expect(isWebShareSupported()).toBe(true);

            // Test without support
            window.navigator.share = undefined;
            expect(isWebShareSupported()).toBe(false);
        });
    });

    describe('URL Generation', () => {

        test('should generate correct LinkedIn share URL', () => {
            const jobData = {
                title: 'Senior Software Engineer',
                company: 'Tech Corp',
                url: 'https://jobfinders.site/jobs/test-job-123'
            };

            const linkedInUrl = generateShareUrl('linkedin', jobData);

            expect(linkedInUrl).toContain('linkedin.com/sharing/share-offsite');
            expect(linkedInUrl).toContain(encodeURIComponent(jobData.url));
        });

        test('should generate correct Twitter share URL', () => {
            const jobData = {
                title: 'Senior Software Engineer',
                company: 'Tech Corp',
                url: 'https://jobfinders.site/jobs/test-job-123'
            };

            const twitterUrl = generateShareUrl('twitter', jobData);

            expect(twitterUrl).toContain('twitter.com/intent/tweet');
            expect(twitterUrl).toContain('text=');
            expect(twitterUrl).toContain('url=');
            expect(twitterUrl).toContain(encodeURIComponent(jobData.url));
        });

        test('should generate correct Facebook share URL', () => {
            const jobData = {
                url: 'https://jobfinders.site/jobs/test-job-123'
            };

            const facebookUrl = generateShareUrl('facebook', jobData);

            expect(facebookUrl).toContain('facebook.com/sharer/sharer.php');
            expect(facebookUrl).toContain('u=' + encodeURIComponent(jobData.url));
        });

        test('should generate correct WhatsApp share URL', () => {
            const jobData = {
                title: 'Senior Software Engineer',
                company: 'Tech Corp',
                url: 'https://jobfinders.site/jobs/test-job-123'
            };

            const whatsappUrl = generateShareUrl('whatsapp', jobData);

            expect(whatsappUrl).toContain('wa.me');
            expect(whatsappUrl).toContain('text=');
            expect(whatsappUrl).toContain(encodeURIComponent(jobData.title));
            expect(whatsappUrl).toContain(encodeURIComponent(jobData.url));
        });
    });

    describe('Modal Initialization', () => {

        test('should initialize share modal event listeners', () => {
            const mockShareButtons = [
                {dataset: {shareMethod: 'linkedin'}, addEventListener: jest.fn()},
                {dataset: {shareMethod: 'twitter'}, addEventListener: jest.fn()},
                {dataset: {shareMethod: 'facebook'}, addEventListener: jest.fn()}
            ];

            mockModal.querySelectorAll.mockReturnValue(mockShareButtons);

            initializeShareModal();

            // Verify event listeners are added to share buttons
            mockShareButtons.forEach(button => {
                expect(button.addEventListener).toHaveBeenCalledWith(
                    'click',
                    expect.any(Function)
                );
            });

            // Verify modal event listeners
            expect(mockOverlay.addEventListener).toHaveBeenCalledWith(
                'click',
                expect.any(Function)
            );
            expect(mockCloseButton.addEventListener).toHaveBeenCalledWith(
                'click',
                expect.any(Function)
            );
        });

        test('should handle missing modal elements gracefully', () => {
            document.getElementById.mockReturnValue(null);

            // Should not throw error
            expect(() => initializeShareModal()).not.toThrow();
        });
    });

    describe('Accessibility', () => {

        test('should manage focus when opening modal', () => {
            const mockFocusableElement = {
                focus: jest.fn()
            };

            mockModal.querySelector.mockReturnValue(mockFocusableElement);

            openShareModal({id: 'test-job', title: 'Test Job'});

            // Verify focus is set to first focusable element
            expect(mockFocusableElement.focus).toHaveBeenCalled();
        });

        test('should trap focus within modal', () => {
            const mockFocusableElements = [
                {focus: jest.fn()},
                {focus: jest.fn()},
                {focus: jest.fn()}
            ];

            mockModal.querySelectorAll.mockReturnValue(mockFocusableElements);

            openShareModal({id: 'test-job', title: 'Test Job'});

            // Get the keydown handler
            const keydownHandler = document.addEventListener.mock.calls
                .find(call => call[0] === 'keydown')[1];

            // Simulate Tab key on last element
            const mockEvent = {
                key: 'Tab',
                shiftKey: false,
                target: mockFocusableElements[2],
                preventDefault: jest.fn()
            };

            keydownHandler(mockEvent);

            // Should focus first element
            expect(mockFocusableElements[0].focus).toHaveBeenCalled();
            expect(mockEvent.preventDefault).toHaveBeenCalled();
        });

        test('should restore focus when closing modal', () => {
            const mockTriggerElement = {
                focus: jest.fn()
            };

            // Mock the element that opened the modal
            document.activeElement = mockTriggerElement;

            openShareModal({id: 'test-job', title: 'Test Job'});
            closeShareModal();

            // Verify focus is restored
            expect(mockTriggerElement.focus).toHaveBeenCalled();
        });

        test('should have proper ARIA attributes', () => {
            openShareModal({id: 'test-job', title: 'Test Job'});

            // Verify ARIA attributes are set
            expect(mockModal.setAttribute).toHaveBeenCalledWith('aria-hidden', 'false');
            expect(mockModal.setAttribute).toHaveBeenCalledWith('role', 'dialog');
            expect(mockModal.setAttribute).toHaveBeenCalledWith('aria-modal', 'true');
        });
    });

    describe('Responsive Design', () => {

        test('should adapt to mobile viewport', () => {
            // Mock mobile viewport
            Object.defineProperty(window, 'innerWidth', {
                writable: true,
                configurable: true,
                value: 375
            });

            openShareModal({id: 'test-job', title: 'Test Job'});

            // Verify mobile-specific classes are added
            expect(mockModal.classList.add).toHaveBeenCalledWith('mobile');
        });

        test('should use native share on mobile when available', async () => {
            // Mock mobile environment with Web Share API
            Object.defineProperty(window, 'innerWidth', {value: 375});
            window.navigator.share = jest.fn().mockResolvedValue();

            const jobData = {id: 'test-job', title: 'Test Job', url: 'https://example.com'};

            await shareViaWebAPI(jobData);

            expect(window.navigator.share).toHaveBeenCalled();
        });
    });

    describe('Error Handling', () => {

        test('should handle network errors in share tracking', async () => {
            // Mock network error
            fetch.mockRejectedValueOnce(new Error('Network error'));

            const jobData = {id: 'test-job', title: 'Test Job'};

            await shareViaLinkedIn(jobData);

            // Should still open share window
            expect(window.open).toHaveBeenCalled();

            // Should log error
            expect(console.error).toHaveBeenCalledWith(
                expect.stringContaining('Network error')
            );
        });

        test('should handle malformed job data', () => {
            const invalidJobData = null;

            // Should not throw error
            expect(() => openShareModal(invalidJobData)).not.toThrow();

            // Should log warning
            expect(console.warn).toHaveBeenCalledWith(
                'Invalid job data provided to share modal'
            );
        });
    });
});