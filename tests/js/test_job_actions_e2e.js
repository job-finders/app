/**
 * End-to-End JavaScript Tests for Job Actions
 *
 * Tests complete user workflows including:
 * - Job discovery to engagement flow
 * - Company profile to job actions flow
 * - Share to application conversion flow
 * - Error recovery flows
 * - Performance and accessibility validation
 */

// Mock browser environment for E2E testing
global.window = {
    location: {
        href: 'https://jobfinders.site/jobs/test-job-123',
        origin: 'https://jobfinders.site',
        pathname: '/jobs/test-job-123'
    },
    history: {
        pushState: jest.fn(),
        replaceState: jest.fn()
    },
    navigator: {
        userAgent: 'Mozilla/5.0 (compatible; test)',
        share: jest.fn(),
        clipboard: {writeText: jest.fn()}
    },
    open: jest.fn(),
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    innerWidth: 1024,
    innerHeight: 768
};

global.document = {
    getElementById: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(),
    createElement: jest.fn(),
    body: {
        classList: {add: jest.fn(), remove: jest.fn()},
        appendChild: jest.fn(),
        removeChild: jest.fn()
    },
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: 'complete'
};

global.fetch = jest.fn();
global.console = {
    log: jest.fn(),
    error: jest.fn(),
    warn: jest.fn()
};

// Mock performance API
global.performance = {
    now: jest.fn(() => Date.now()),
    mark: jest.fn(),
    measure: jest.fn()
};

// Import job actions modules
const {
    initializeJobActions,
    JobActionsManager,
    ShareModalManager,
    AnalyticsTracker,
    ErrorHandler,
    PerformanceMonitor
} = require('../../static/js/jobs/job-actions-manager.js');

describe('Job Actions End-to-End Tests', () => {

    let jobActionsManager;
    let mockJobData;
    let mockUserContext;

    beforeEach(() => {
        jest.clearAllMocks();

        // Mock job data
        mockJobData = {
            id: 'test-job-123',
            title: 'Senior Software Engineer',
            company: 'Tech Corp',
            location: 'Cape Town',
            url: 'https://jobfinders.site/jobs/test-job-123',
            salary: 'R50,000 - R80,000',
            posted_date: '2024-01-15'
        };

        // Mock user context
        mockUserContext = {
            isAuthenticated: true,
            userId: 'user-456',
            preferences: {
                notifications: true,
                analytics: true
            }
        };

        // Initialize job actions manager
        jobActionsManager = new JobActionsManager(mockJobData, mockUserContext);

        // Mock DOM elements
        setupMockDOM();
    });

    function setupMockDOM() {
        const mockElements = {
            'likeButton': createMockButton('like', false),
            'saveButton': createMockButton('save', false),
            'shareButton': createMockButton('share', false),
            'companyButton': createMockButton('company', false),
            'shareModal': createMockModal(),
            'jobActionsPanel': createMockPanel(),
            'toastContainer': createMockToastContainer()
        };

        document.getElementById.mockImplementation(id => mockElements[id] || null);
        document.querySelector.mockImplementation(selector => {
            if (selector === '.job-actions-panel') return mockElements.jobActionsPanel;
            if (selector === '.toast-container') return mockElements.toastContainer;
            return null;
        });
    }

    function createMockButton(type, active) {
        return {
            id: `${type}Button`,
            classList: {
                add: jest.fn(),
                remove: jest.fn(),
                contains: jest.fn(() => active),
                toggle: jest.fn()
            },
            dataset: {jobId: mockJobData.id},
            disabled: false,
            innerHTML: '',
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            setAttribute: jest.fn(),
            getAttribute: jest.fn(),
            querySelector: jest.fn(() => ({textContent: '5'})),
            click: jest.fn()
        };
    }

    function createMockModal() {
        return {
            style: {display: 'none'},
            classList: {add: jest.fn(), remove: jest.fn()},
            addEventListener: jest.fn(),
            querySelector: jest.fn(),
            querySelectorAll: jest.fn(() => [])
        };
    }

    function createMockPanel() {
        return {
            classList: {add: jest.fn(), remove: jest.fn()},
            querySelector: jest.fn(),
            querySelectorAll: jest.fn(() => [])
        };
    }

    function createMockToastContainer() {
        return {
            appendChild: jest.fn(),
            removeChild: jest.fn()
        };
    }

    describe('Complete Job Engagement Flow', () => {

        test('should handle complete user engagement workflow', async () => {
            // Mock API responses
            fetch
                .mockResolvedValueOnce({ // Initial state
                    ok: true,
                    json: async () => ({
                        success: true,
                        data: {
                            user_has_liked: false,
                            user_has_saved: false,
                            like_count: 5,
                            share_count: 2
                        }
                    })
                })
                .mockResolvedValueOnce({ // Like action
                    ok: true,
                    json: async () => ({
                        success: true,
                        data: {like_id: 'like-123', like_count: 6}
                    })
                })
                .mockResolvedValueOnce({ // Save action
                    ok: true,
                    json: async () => ({
                        success: true,
                        data: {saved_job_id: 'save-123'}
                    })
                })
                .mockResolvedValueOnce({ // Share action
                    ok: true,
                    json: async () => ({
                        success: true,
                        data: {share_id: 'share-123', share_count: 3}
                    })
                });

            // Initialize job actions
            await jobActionsManager.initialize();

            // Step 1: User likes the job
            await jobActionsManager.toggleLike();

            // Verify like API call and UI update
            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/like',
                expect.objectContaining({method: 'POST'})
            );

            const likeButton = document.getElementById('likeButton');
            expect(likeButton.classList.add).toHaveBeenCalledWith('liked');

            // Step 2: User saves the job
            await jobActionsManager.toggleSave();

            // Verify save API call and UI update
            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/save',
                expect.objectContaining({method: 'POST'})
            );

            const saveButton = document.getElementById('saveButton');
            expect(saveButton.classList.add).toHaveBeenCalledWith('saved');

            // Step 3: User shares the job
            await jobActionsManager.shareJob('linkedin');

            // Verify share API call
            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/share',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({share_method: 'linkedin'})
                })
            );

            // Verify LinkedIn share window opened
            expect(window.open).toHaveBeenCalledWith(
                expect.stringContaining('linkedin.com'),
                '_blank'
            );

            // Verify analytics tracking
            expect(jobActionsManager.analytics.trackEvent).toHaveBeenCalledTimes(3);
        });

        test('should handle anonymous user workflow', async () => {
            // Create anonymous user context
            const anonymousContext = {
                isAuthenticated: false,
                userId: null
            };

            const anonymousManager = new JobActionsManager(mockJobData, anonymousContext);

            // Mock share API response (anonymous sharing allowed)
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {share_id: 'share-123', referral_code: null}
                })
            });

            await anonymousManager.initialize();

            // Anonymous user tries to like (should prompt login)
            await anonymousManager.toggleLike();

            // Verify login modal is shown instead of API call
            expect(document.getElementById('loginModal').style.display).toBe('flex');

            // Anonymous user can share
            await anonymousManager.shareJob('email');

            // Verify share works for anonymous users
            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/share',
                expect.objectContaining({
                    body: JSON.stringify({share_method: 'email'})
                })
            );
        });

        test('should handle rapid user interactions', async () => {
            // Mock API responses
            fetch.mockResolvedValue({
                ok: true,
                json: async () => ({success: true, data: {like_count: 5}})
            });

            await jobActionsManager.initialize();

            // Simulate rapid clicks
            const promises = [
                jobActionsManager.toggleLike(),
                jobActionsManager.toggleLike(),
                jobActionsManager.toggleLike()
            ];

            await Promise.all(promises);

            // Verify debouncing - only one API call should be made
            expect(fetch).toHaveBeenCalledTimes(2); // 1 for init, 1 for like
        });
    });

    describe('Company Profile to Job Actions Flow', () => {

        test('should handle navigation from company profile to job engagement', async () => {
            // Mock company profile context
            const companyProfileContext = {
                companyId: 'tech-corp-123',
                fromCompanyProfile: true
            };

            jobActionsManager.setContext(companyProfileContext);

            // Mock API responses
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {user_has_liked: false, like_count: 5}
                })
            });

            await jobActionsManager.initialize();

            // Verify company context is tracked
            expect(jobActionsManager.analytics.trackEvent).toHaveBeenCalledWith(
                'job_view_from_company_profile',
                expect.objectContaining({
                    company_id: 'tech-corp-123',
                    job_id: 'test-job-123'
                })
            );

            // User likes job from company profile
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true, data: {like_count: 6}})
            });

            await jobActionsManager.toggleLike();

            // Verify company attribution is included
            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/like',
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'X-Source-Context': 'company_profile'
                    })
                })
            );
        });

        test('should track company profile engagement funnel', async () => {
            const funnelTracker = jobActionsManager.analytics.funnelTracker;

            // Step 1: View company profile
            funnelTracker.trackStep('company_profile_view', {
                company_id: 'tech-corp-123'
            });

            // Step 2: View job from company profile
            funnelTracker.trackStep('job_view_from_company', {
                job_id: 'test-job-123',
                company_id: 'tech-corp-123'
            });

            // Step 3: Engage with job
            await jobActionsManager.toggleLike();

            funnelTracker.trackStep('job_engagement', {
                action: 'like',
                job_id: 'test-job-123'
            });

            // Verify funnel tracking
            expect(funnelTracker.getConversionRate()).toBeGreaterThan(0);
            expect(funnelTracker.getCurrentStep()).toBe('job_engagement');
        });
    });

    describe('Share to Application Conversion Flow', () => {

        test('should track share conversion to application', async () => {
            // Mock share with referral code
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    data: {
                        share_id: 'share-123',
                        referral_code: 'REF123',
                        share_count: 1
                    }
                })
            });

            await jobActionsManager.shareJob('linkedin');

            // Simulate user coming back via shared link
            const referralContext = {
                referralCode: 'REF123',
                source: 'linkedin_share'
            };

            jobActionsManager.setReferralContext(referralContext);

            // Mock application submission
            const applicationManager = jobActionsManager.getApplicationManager();
            await applicationManager.submitApplication({
                jobId: 'test-job-123',
                userId: 'user-789'
            });

            // Verify conversion tracking
            expect(jobActionsManager.analytics.trackConversion).toHaveBeenCalledWith(
                'share_to_application',
                {
                    share_id: 'share-123',
                    referral_code: 'REF123',
                    source: 'linkedin_share',
                    job_id: 'test-job-123'
                }
            );
        });

        test('should handle share link attribution', async () => {
            // Mock URL with referral parameters
            window.location.search = '?ref=REF123&source=linkedin';

            await jobActionsManager.initialize();

            // Verify referral attribution is captured
            expect(jobActionsManager.referralTracker.getReferralData()).toEqual({
                referralCode: 'REF123',
                source: 'linkedin',
                timestamp: expect.any(Number)
            });

            // Verify attribution is included in subsequent actions
            await jobActionsManager.toggleLike();

            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/like',
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'X-Referral-Code': 'REF123'
                    })
                })
            );
        });
    });

    describe('Error Recovery Flows', () => {

        test('should handle network errors gracefully', async () => {
            // Mock network error
            fetch.mockRejectedValueOnce(new Error('Network error'));

            await jobActionsManager.initialize();

            // Attempt action that fails
            await jobActionsManager.toggleLike();

            // Verify error handling
            expect(jobActionsManager.errorHandler.getLastError()).toEqual(
                expect.objectContaining({
                    type: 'network_error',
                    action: 'like_job',
                    recoverable: true
                })
            );

            // Verify retry mechanism
            expect(jobActionsManager.retryManager.getRetryCount('like_job')).toBe(1);

            // Verify user feedback
            const toastContainer = document.querySelector('.toast-container');
            expect(toastContainer.appendChild).toHaveBeenCalledWith(
                expect.objectContaining({
                    className: expect.stringContaining('error')
                })
            );
        });

        test('should handle authentication errors', async () => {
            // Mock authentication error
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 401,
                json: async () => ({
                    success: false,
                    message: 'Authentication required'
                })
            });

            await jobActionsManager.toggleLike();

            // Verify login modal is shown
            expect(document.getElementById('loginModal').style.display).toBe('flex');

            // Verify action is queued for after login
            expect(jobActionsManager.actionQueue.getPendingActions()).toContain(
                expect.objectContaining({
                    type: 'like_job',
                    jobId: 'test-job-123'
                })
            );
        });

        test('should handle rate limiting errors', async () => {
            // Mock rate limiting error
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 429,
                json: async () => ({
                    success: false,
                    message: 'Rate limit exceeded',
                    retry_after: 60
                })
            });

            await jobActionsManager.toggleLike();

            // Verify rate limit handling
            expect(jobActionsManager.rateLimitManager.isRateLimited('like_job')).toBe(true);
            expect(jobActionsManager.rateLimitManager.getRetryAfter('like_job')).toBe(60);

            // Verify user feedback includes retry time
            expect(console.warn).toHaveBeenCalledWith(
                expect.stringContaining('Please try again in 60 seconds')
            );
        });

        test('should recover from temporary failures', async () => {
            // Mock temporary failure followed by success
            fetch
                .mockRejectedValueOnce(new Error('Temporary failure'))
                .mockResolvedValueOnce({
                    ok: true,
                    json: async () => ({success: true, data: {like_count: 6}})
                });

            await jobActionsManager.toggleLike();

            // Wait for retry
            await new Promise(resolve => setTimeout(resolve, 1100));

            // Verify retry was successful
            expect(fetch).toHaveBeenCalledTimes(2);
            expect(jobActionsManager.errorHandler.getLastError()).toBeNull();
        });
    });

    describe('Performance and Accessibility', () => {

        test('should meet performance benchmarks', async () => {
            const performanceMonitor = jobActionsManager.performanceMonitor;

            // Start performance measurement
            performanceMonitor.startMeasurement('job_actions_init');

            await jobActionsManager.initialize();

            // End performance measurement
            const initTime = performanceMonitor.endMeasurement('job_actions_init');

            // Verify initialization is fast
            expect(initTime).toBeLessThan(100); // Less than 100ms

            // Test action performance
            performanceMonitor.startMeasurement('like_action');

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({success: true, data: {like_count: 6}})
            });

            await jobActionsManager.toggleLike();

            const actionTime = performanceMonitor.endMeasurement('like_action');

            // Verify action is responsive
            expect(actionTime).toBeLessThan(50); // Less than 50ms for UI response
        });

        test('should maintain accessibility standards', async () => {
            await jobActionsManager.initialize();

            const likeButton = document.getElementById('likeButton');

            // Verify ARIA attributes
            expect(likeButton.setAttribute).toHaveBeenCalledWith('aria-pressed', 'false');
            expect(likeButton.setAttribute).toHaveBeenCalledWith('aria-label', expect.any(String));

            // Test keyboard navigation
            const keyboardEvent = new KeyboardEvent('keydown', {key: 'Enter'});
            likeButton.addEventListener.mock.calls
                .find(call => call[0] === 'keydown')[1](keyboardEvent);

            // Verify keyboard interaction works
            expect(likeButton.click).toHaveBeenCalled();

            // Test focus management
            await jobActionsManager.shareModalManager.openModal(mockJobData);

            const shareModal = document.getElementById('shareModal');
            const focusableElement = shareModal.querySelector('[tabindex="0"]');

            expect(focusableElement.focus).toHaveBeenCalled();
        });

        test('should handle mobile interactions', async () => {
            // Mock mobile environment
            Object.defineProperty(window, 'innerWidth', {value: 375});
            Object.defineProperty(window, 'ontouchstart', {value: true});

            await jobActionsManager.initialize();

            // Verify mobile-specific optimizations
            const jobActionsPanel = document.querySelector('.job-actions-panel');
            expect(jobActionsPanel.classList.add).toHaveBeenCalledWith('mobile');

            // Test touch interactions
            const likeButton = document.getElementById('likeButton');
            const touchEvent = new TouchEvent('touchstart');

            likeButton.addEventListener.mock.calls
                .find(call => call[0] === 'touchstart')[1](touchEvent);

            // Verify touch feedback
            expect(likeButton.classList.add).toHaveBeenCalledWith('touch-active');
        });

        test('should optimize for slow networks', async () => {
            // Mock slow network
            Object.defineProperty(navigator, 'connection', {
                value: {effectiveType: '2g'}
            });

            await jobActionsManager.initialize();

            // Verify optimizations for slow networks
            expect(jobActionsManager.networkOptimizer.isSlowNetwork()).toBe(true);
            expect(jobActionsManager.config.enableOptimisticUI).toBe(true);
            expect(jobActionsManager.config.requestTimeout).toBe(10000); // Longer timeout

            // Test optimistic UI updates
            const likeButton = document.getElementById('likeButton');

            // Mock delayed API response
            fetch.mockImplementation(() =>
                new Promise(resolve =>
                    setTimeout(() => resolve({
                        ok: true,
                        json: async () => ({success: true, data: {like_count: 6}})
                    }), 2000)
                )
            );

            await jobActionsManager.toggleLike();

            // Verify optimistic UI update happened immediately
            expect(likeButton.classList.add).toHaveBeenCalledWith('liked');
        });
    });

    describe('Analytics and Tracking', () => {

        test('should track comprehensive user journey', async () => {
            const analytics = jobActionsManager.analytics;

            await jobActionsManager.initialize();

            // Track page view
            analytics.trackPageView('job_detail', {
                job_id: 'test-job-123',
                company_id: 'tech-corp-123'
            });

            // Track engagement actions
            await jobActionsManager.toggleLike();
            await jobActionsManager.toggleSave();
            await jobActionsManager.shareJob('linkedin');

            // Verify comprehensive tracking
            expect(analytics.getEventHistory()).toEqual([
                expect.objectContaining({event: 'page_view', page: 'job_detail'}),
                expect.objectContaining({event: 'job_like', job_id: 'test-job-123'}),
                expect.objectContaining({event: 'job_save', job_id: 'test-job-123'}),
                expect.objectContaining({event: 'job_share', method: 'linkedin'})
            ]);

            // Verify user journey mapping
            const userJourney = analytics.getUserJourney();
            expect(userJourney.steps).toHaveLength(4);
            expect(userJourney.totalEngagementTime).toBeGreaterThan(0);
        });

        test('should track performance metrics', async () => {
            const performanceTracker = jobActionsManager.performanceTracker;

            await jobActionsManager.initialize();

            // Perform actions and track performance
            await jobActionsManager.toggleLike();

            const metrics = performanceTracker.getMetrics();

            expect(metrics).toEqual(
                expect.objectContaining({
                    apiResponseTimes: expect.any(Array),
                    uiUpdateTimes: expect.any(Array),
                    errorRates: expect.any(Object),
                    cacheHitRates: expect.any(Object)
                })
            );
        });

        test('should respect user privacy preferences', async () => {
            // Mock user with analytics disabled
            const privacyContext = {
                ...mockUserContext,
                preferences: {
                    analytics: false,
                    tracking: false
                }
            };

            const privacyManager = new JobActionsManager(mockJobData, privacyContext);
            await privacyManager.initialize();

            // Perform actions
            await privacyManager.toggleLike();

            // Verify no analytics tracking
            expect(privacyManager.analytics.trackEvent).not.toHaveBeenCalled();

            // Verify essential functionality still works
            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/like',
                expect.any(Object)
            );
        });
    });
});