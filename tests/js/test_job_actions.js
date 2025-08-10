/**
 * JavaScript Tests for Job Actions Functionality
 *
 * Tests for job actions including like, save, share functionality,
 * AJAX requests, UI state management, and error handling.
 * Run with Jest testing framework.
 */

// Mock DOM elements and global objects
const mockDOM = {
    getElementById: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(),
    createElement: jest.fn(),
    addEventListener: jest.fn(),
    body: {classList: {add: jest.fn(), remove: jest.fn()}}
};

// Mock fetch API
global.fetch = jest.fn();

// Mock window object
global.window = {
    location: {href: 'https://jobfinders.site/jobs/test-job-123'},
    navigator: {share: jest.fn()},
    open: jest.fn()
};

// Mock document object
global.document = {
    ...mockDOM,
    getElementById: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(),
    createElement: jest.fn(),
    body: mockDOM.body
};

// Mock console for testing
global.console = {
    log: jest.fn(),
    error: jest.fn(),
    warn: jest.fn()
};

// Import the job actions JavaScript (assuming it's modularized)
// In a real scenario, you'd import the actual functions
const {
    toggleLike,
    toggleSave,
    openShareModal,
    closeShareModal,
    shareJob,
    copyJobUrl,
    updateJobActionsState,
    showToast,
    handleJobActionError
} = require('../../static/js/jobs/job-actions.js');

describe('Job Actions JavaScript Tests', () => {

    beforeEach(() => {
        // Reset all mocks before each test
        jest.clearAllMocks();

        // Reset fetch mock
        fetch.mockClear();

        // Mock DOM elements that are commonly used
        document.getElementById.mockImplementation((id) => {
            const mockElement = {
                id: id,
                classList: {
                    add: jest.fn(),
                    remove: jest.fn(),
                    contains: jest.fn(),
                    toggle: jest.fn()
                },
                innerHTML: '',
                textContent: '',
                style: {},
                addEventListener: jest.fn(),
                removeEventListener: jest.fn(),
                setAttribute: jest.fn(),
                getAttribute: jest.fn(),
                disabled: false,
                click: jest.fn()
            };

            // Specific mock behaviors for different elements
            if (id === 'likeButton') {
                mockElement.dataset = {jobId: 'test-job-123'};
                mockElement.querySelector = jest.fn(() => ({textContent: '5'}));
            } else if (id === 'saveButton') {
                mockElement.dataset = {jobId: 'test-job-123'};
            } else if (id === 'shareModal') {
                mockElement.style.display = 'none';
            }

            return mockElement;
        });
    });

    describe('toggleLike function', () => {

        test('should like a job successfully', async () => {
            // Mock successful API response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {like_id: 'like-123', like_count: 6}
                })
            });

            const mockButton = document.getElementById('likeButton');
            mockButton.classList.contains.mockReturnValue(false); // Not liked initially

            await toggleLike('test-job-123');

            // Verify API call was made
            expect(fetch).toHaveBeenCalledWith('/api/jobs/test-job-123/like', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // Verify UI updates
            expect(mockButton.classList.add).toHaveBeenCalledWith('liked');
            expect(mockButton.disabled).toBe(false);
        });

        test('should unlike a job successfully', async () => {
            // Mock successful API response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {like_count: 4}
                })
            });

            const mockButton = document.getElementById('likeButton');
            mockButton.classList.contains.mockReturnValue(true); // Already liked

            await toggleLike('test-job-123');

            // Verify API call was made
            expect(fetch).toHaveBeenCalledWith('/api/jobs/test-job-123/like', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // Verify UI updates
            expect(mockButton.classList.remove).toHaveBeenCalledWith('liked');
        });

        test('should handle like error gracefully', async () => {
            // Mock API error
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 401,
                json: async () => ({
                    success: false,
                    message: 'Authentication required'
                })
            });

            const mockButton = document.getElementById('likeButton');

            await toggleLike('test-job-123');

            // Verify error handling
            expect(mockButton.disabled).toBe(false);
            expect(console.error).toHaveBeenCalled();
        });

        test('should show loading state during API call', async () => {
            // Mock delayed API response
            fetch.mockImplementation(() =>
                new Promise(resolve =>
                    setTimeout(() => resolve({
                        ok: true,
                        json: async () => ({success: true, data: {like_count: 5}})
                    }), 100)
                )
            );

            const mockButton = document.getElementById('likeButton');

            const likePromise = toggleLike('test-job-123');

            // Verify loading state is set
            expect(mockButton.disabled).toBe(true);
            expect(mockButton.classList.add).toHaveBeenCalledWith('loading');

            await likePromise;

            // Verify loading state is removed
            expect(mockButton.classList.remove).toHaveBeenCalledWith('loading');
        });
    });

    describe('toggleSave function', () => {

        test('should save a job successfully', async () => {
            // Mock successful API response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {saved_job_id: 'save-123'}
                })
            });

            const mockButton = document.getElementById('saveButton');
            mockButton.classList.contains.mockReturnValue(false); // Not saved initially

            await toggleSave('test-job-123');

            // Verify API call was made
            expect(fetch).toHaveBeenCalledWith('/api/jobs/test-job-123/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // Verify UI updates
            expect(mockButton.classList.add).toHaveBeenCalledWith('saved');
        });

        test('should unsave a job successfully', async () => {
            // Mock successful API response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    message: 'Job unsaved successfully'
                })
            });

            const mockButton = document.getElementById('saveButton');
            mockButton.classList.contains.mockReturnValue(true); // Already saved

            await toggleSave('test-job-123');

            // Verify API call was made
            expect(fetch).toHaveBeenCalledWith('/api/jobs/test-job-123/save', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // Verify UI updates
            expect(mockButton.classList.remove).toHaveBeenCalledWith('saved');
        });

        test('should handle authentication error', async () => {
            // Mock authentication error
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 401,
                json: async () => ({
                    success: false,
                    message: 'Please log in to save jobs'
                })
            });

            await toggleSave('test-job-123');

            // Verify error handling (should redirect to login or show modal)
            expect(console.error).toHaveBeenCalled();
        });
    });

    describe('Share Modal functionality', () => {

        test('should open share modal', () => {
            const mockModal = document.getElementById('shareModal');
            const mockJobTitle = document.getElementById('shareJobTitle');

            openShareModal('test-job-123', 'Software Engineer Position');

            // Verify modal is shown
            expect(mockModal.style.display).toBe('flex');
            expect(mockJobTitle.textContent).toBe('Software Engineer Position');
            expect(document.body.classList.add).toHaveBeenCalledWith('modal-open');
        });

        test('should close share modal', () => {
            const mockModal = document.getElementById('shareModal');

            closeShareModal();

            // Verify modal is hidden
            expect(mockModal.style.display).toBe('none');
            expect(document.body.classList.remove).toHaveBeenCalledWith('modal-open');
        });

        test('should close modal when clicking outside', () => {
            const mockModal = document.getElementById('shareModal');
            mockModal.addEventListener = jest.fn();

            openShareModal('test-job-123', 'Test Job');

            // Simulate click outside modal
            const clickHandler = mockModal.addEventListener.mock.calls.find(
                call => call[0] === 'click'
            )[1];

            const mockEvent = {
                target: mockModal,
                stopPropagation: jest.fn()
            };

            clickHandler(mockEvent);

            expect(mockModal.style.display).toBe('none');
        });
    });

    describe('shareJob function', () => {

        test('should share job via email', async () => {
            // Mock successful API response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {share_id: 'share-123', share_count: 1}
                })
            });

            await shareJob('test-job-123', 'email');

            // Verify API call was made
            expect(fetch).toHaveBeenCalledWith('/api/jobs/test-job-123/share', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({share_method: 'email'})
            });

            // Verify email client is opened
            expect(window.open).toHaveBeenCalledWith(
                expect.stringContaining('mailto:')
            );
        });

        test('should share job via LinkedIn', async () => {
            // Mock successful API response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {share_id: 'share-123', share_count: 1}
                })
            });

            await shareJob('test-job-123', 'linkedin');

            // Verify LinkedIn share URL is opened
            expect(window.open).toHaveBeenCalledWith(
                expect.stringContaining('linkedin.com/sharing/share-offsite'),
                '_blank'
            );
        });

        test('should use native Web Share API when available', async () => {
            // Mock Web Share API support
            window.navigator.share.mockResolvedValueOnce();

            await shareJob('test-job-123', 'native');

            // Verify native share was called
            expect(window.navigator.share).toHaveBeenCalledWith({
                title: expect.any(String),
                text: expect.any(String),
                url: expect.any(String)
            });
        });

        test('should handle share API error', async () => {
            // Mock API error
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                json: async () => ({
                    success: false,
                    message: 'Internal server error'
                })
            });

            await shareJob('test-job-123', 'email');

            // Verify error handling
            expect(console.error).toHaveBeenCalled();
        });
    });

    describe('copyJobUrl function', () => {

        test('should copy job URL to clipboard', async () => {
            // Mock clipboard API
            global.navigator.clipboard = {
                writeText: jest.fn().mockResolvedValue()
            };

            await copyJobUrl('test-job-123');

            // Verify clipboard API was called
            expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
                expect.stringContaining('test-job-123')
            );
        });

        test('should fallback to legacy copy method', async () => {
            // Mock clipboard API not available
            global.navigator.clipboard = undefined;

            // Mock document methods for legacy copy
            document.createElement.mockReturnValue({
                value: '',
                select: jest.fn(),
                setSelectionRange: jest.fn(),
                style: {}
            });
            document.execCommand = jest.fn().mockReturnValue(true);

            await copyJobUrl('test-job-123');

            // Verify legacy copy method was used
            expect(document.execCommand).toHaveBeenCalledWith('copy');
        });

        test('should show success toast after copying', async () => {
            global.navigator.clipboard = {
                writeText: jest.fn().mockResolvedValue()
            };

            await copyJobUrl('test-job-123');

            // Verify success feedback is shown
            // This would depend on your toast implementation
            expect(console.log).toHaveBeenCalledWith(
                expect.stringContaining('copied')
            );
        });
    });

    describe('updateJobActionsState function', () => {

        test('should update UI state from API response', () => {
            const mockLikeButton = document.getElementById('likeButton');
            const mockSaveButton = document.getElementById('saveButton');
            const mockLikeCount = {textContent: '0'};

            mockLikeButton.querySelector.mockReturnValue(mockLikeCount);

            const stateData = {
                user_has_liked: true,
                user_has_saved: false,
                like_count: 10,
                share_count: 3
            };

            updateJobActionsState(stateData);

            // Verify UI updates
            expect(mockLikeButton.classList.add).toHaveBeenCalledWith('liked');
            expect(mockSaveButton.classList.remove).toHaveBeenCalledWith('saved');
            expect(mockLikeCount.textContent).toBe('10');
        });

        test('should handle missing UI elements gracefully', () => {
            document.getElementById.mockReturnValue(null);

            const stateData = {
                user_has_liked: true,
                like_count: 5
            };

            // Should not throw error
            expect(() => updateJobActionsState(stateData)).not.toThrow();
        });
    });

    describe('Error handling', () => {

        test('should handle network errors', async () => {
            // Mock network error
            fetch.mockRejectedValueOnce(new Error('Network error'));

            await toggleLike('test-job-123');

            // Verify error is handled
            expect(console.error).toHaveBeenCalledWith(
                expect.stringContaining('Network error')
            );
        });

        test('should handle malformed JSON response', async () => {
            // Mock invalid JSON response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => {
                    throw new Error('Invalid JSON');
                }
            });

            await toggleLike('test-job-123');

            // Verify error is handled
            expect(console.error).toHaveBeenCalled();
        });

        test('should show user-friendly error messages', async () => {
            // Mock API error with user message
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 429,
                json: async () => ({
                    success: false,
                    message: 'Too many requests. Please try again later.'
                })
            });

            await toggleLike('test-job-123');

            // Verify user-friendly error is shown
            expect(console.error).toHaveBeenCalledWith(
                expect.stringContaining('Too many requests')
            );
        });
    });

    describe('UI State Management', () => {

        test('should disable buttons during API calls', async () => {
            // Mock delayed API response
            let resolvePromise;
            fetch.mockImplementation(() =>
                new Promise(resolve => {
                    resolvePromise = resolve;
                })
            );

            const mockButton = document.getElementById('likeButton');

            const likePromise = toggleLike('test-job-123');

            // Verify button is disabled during API call
            expect(mockButton.disabled).toBe(true);

            // Resolve the promise
            resolvePromise({
                ok: true,
                json: async () => ({success: true, data: {like_count: 5}})
            });

            await likePromise;

            // Verify button is re-enabled
            expect(mockButton.disabled).toBe(false);
        });

        test('should show loading animations', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true, data: {like_count: 5}})
            });

            const mockButton = document.getElementById('likeButton');

            await toggleLike('test-job-123');

            // Verify loading class was added and removed
            expect(mockButton.classList.add).toHaveBeenCalledWith('loading');
            expect(mockButton.classList.remove).toHaveBeenCalledWith('loading');
        });

        test('should update button text and icons', () => {
            const mockButton = document.getElementById('likeButton');
            const mockIcon = {className: 'fas fa-heart-o'};
            const mockText = {textContent: 'Like'};

            mockButton.querySelector = jest.fn()
                .mockReturnValueOnce(mockIcon)
                .mockReturnValueOnce(mockText);

            // Simulate liking
            mockButton.classList.contains.mockReturnValue(true);
            updateJobActionsState({user_has_liked: true, like_count: 1});

            // Verify icon and text updates
            expect(mockIcon.className).toBe('fas fa-heart');
            expect(mockText.textContent).toBe('Liked');
        });
    });

    describe('Accessibility', () => {

        test('should update ARIA attributes', () => {
            const mockButton = document.getElementById('likeButton');

            updateJobActionsState({user_has_liked: true, like_count: 5});

            // Verify ARIA attributes are updated
            expect(mockButton.setAttribute).toHaveBeenCalledWith(
                'aria-pressed', 'true'
            );
            expect(mockButton.setAttribute).toHaveBeenCalledWith(
                'aria-label', expect.stringContaining('Unlike')
            );
        });

        test('should maintain keyboard navigation', () => {
            const mockButton = document.getElementById('likeButton');

            // Simulate keyboard event
            const keyboardEvent = new KeyboardEvent('keydown', {key: 'Enter'});
            mockButton.addEventListener.mock.calls[0][1](keyboardEvent);

            // Verify keyboard interaction works
            expect(mockButton.click).toHaveBeenCalled();
        });
    });

    describe('Performance', () => {

        test('should debounce rapid clicks', async () => {
            fetch.mockResolvedValue({
                ok: true,
                json: async () => ({success: true, data: {like_count: 5}})
            });

            // Simulate rapid clicks
            const promises = [
                toggleLike('test-job-123'),
                toggleLike('test-job-123'),
                toggleLike('test-job-123')
            ];

            await Promise.all(promises);

            // Verify only one API call was made
            expect(fetch).toHaveBeenCalledTimes(1);
        });

        test('should cache job action states', async () => {
            // Mock localStorage
            global.localStorage = {
                getItem: jest.fn(),
                setItem: jest.fn(),
                removeItem: jest.fn()
            };

            const stateData = {user_has_liked: true, like_count: 5};

            updateJobActionsState(stateData);

            // Verify state is cached
            expect(localStorage.setItem).toHaveBeenCalledWith(
                'job_actions_test-job-123',
                JSON.stringify(stateData)
            );
        });
    });
});