/**
 * Jest Setup File for Job Actions JavaScript Tests
 *
 * Global setup and configuration for all JavaScript tests.
 * Includes mocks, polyfills, and test utilities.
 */

// Import Jest DOM matchers
import '@testing-library/jest-dom';

// Global test utilities
global.testUtils = {
    // Create mock DOM element
    createMockElement: (tagName, attributes = {}) => {
        const element = {
            tagName: tagName.toUpperCase(),
            classList: {
                add: jest.fn(),
                remove: jest.fn(),
                contains: jest.fn(() => false),
                toggle: jest.fn()
            },
            style: {},
            dataset: {},
            innerHTML: '',
            textContent: '',
            value: '',
            disabled: false,
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            setAttribute: jest.fn(),
            getAttribute: jest.fn(),
            querySelector: jest.fn(),
            querySelectorAll: jest.fn(() => []),
            appendChild: jest.fn(),
            removeChild: jest.fn(),
            click: jest.fn(),
            focus: jest.fn(),
            blur: jest.fn(),
            select: jest.fn(),
            setSelectionRange: jest.fn(),
            ...attributes
        };

        return element;
    },

    // Create mock fetch response
    createMockResponse: (data, options = {}) => ({
        ok: options.ok !== false,
        status: options.status || 200,
        statusText: options.statusText || 'OK',
        json: async () => data,
        text: async () => JSON.stringify(data),
        headers: new Map(Object.entries(options.headers || {}))
    }),

    // Create mock job data
    createMockJobData: (overrides = {}) => ({
        id: 'test-job-123',
        title: 'Senior Software Engineer',
        company: 'Tech Corp',
        location: 'Cape Town',
        url: 'https://jobfinders.site/jobs/test-job-123',
        salary: 'R50,000 - R80,000',
        posted_date: '2024-01-15',
        ...overrides
    }),

    // Create mock user context
    createMockUserContext: (overrides = {}) => ({
        isAuthenticated: true,
        userId: 'user-456',
        preferences: {
            notifications: true,
            analytics: true
        },
        ...overrides
    }),

    // Wait for async operations
    waitFor: (condition, timeout = 1000) => {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            const check = () => {
                if (condition()) {
                    resolve();
                } else if (Date.now() - startTime > timeout) {
                    reject(new Error('Timeout waiting for condition'));
                } else {
                    setTimeout(check, 10);
                }
            };
            check();
        });
    },

    // Simulate user interaction
    simulateClick: (element) => {
        const event = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        element.dispatchEvent(event);
    },

    // Simulate keyboard interaction
    simulateKeyPress: (element, key) => {
        const event = new KeyboardEvent('keydown', {
            key: key,
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(event);
    }
};

// Global mocks
global.fetch = jest.fn();

// Mock window object
Object.defineProperty(window, 'location', {
    value: {
        href: 'https://jobfinders.site/jobs/test-job-123',
        origin: 'https://jobfinders.site',
        pathname: '/jobs/test-job-123',
        search: '',
        hash: ''
    },
    writable: true
});

Object.defineProperty(window, 'navigator', {
    value: {
        userAgent: 'Mozilla/5.0 (compatible; test)',
        share: jest.fn(),
        clipboard: {
            writeText: jest.fn()
        }
    },
    writable: true
});

// Mock performance API
Object.defineProperty(window, 'performance', {
    value: {
        now: jest.fn(() => Date.now()),
        mark: jest.fn(),
        measure: jest.fn(),
        getEntriesByType: jest.fn(() => []),
        getEntriesByName: jest.fn(() => [])
    },
    writable: true
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
    constructor() {
    }

    observe() {
    }

    unobserve() {
    }

    disconnect() {
    }
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
    constructor() {
    }

    observe() {
    }

    unobserve() {
    }

    disconnect() {
    }
};

// Mock localStorage
Object.defineProperty(window, 'localStorage', {
    value: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
        clear: jest.fn(),
        length: 0,
        key: jest.fn()
    },
    writable: true
});

// Mock sessionStorage
Object.defineProperty(window, 'sessionStorage', {
    value: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
        clear: jest.fn(),
        length: 0,
        key: jest.fn()
    },
    writable: true
});

// Mock console methods for testing
const originalConsole = global.console;
global.console = {
    ...originalConsole,
    log: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    info: jest.fn(),
    debug: jest.fn()
};

// Mock timers
jest.useFakeTimers();

// Custom matchers
expect.extend({
    toHaveBeenCalledWithFetch(received, url, options = {}) {
        const pass = received.mock.calls.some(call => {
            const [callUrl, callOptions] = call;
            return callUrl === url &&
                (!options.method || callOptions?.method === options.method);
        });

        return {
            message: () =>
                `expected fetch to have been called with URL "${url}"${
                    options.method ? ` and method "${options.method}"` : ''
                }`,
            pass
        };
    },

    toHaveClass(received, className) {
        const pass = received.classList.contains(className);
        return {
            message: () =>
                `expected element to ${pass ? 'not ' : ''}have class "${className}"`,
            pass
        };
    },

    toBeVisible(received) {
        const pass = received.style.display !== 'none' &&
            received.style.visibility !== 'hidden';
        return {
            message: () =>
                `expected element to ${pass ? 'not ' : ''}be visible`,
            pass
        };
    }
});

// Global error handler for unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Clean up after each test
afterEach(() => {
    // Clear all mocks
    jest.clearAllMocks();

    // Reset timers
    jest.clearAllTimers();

    // Clear localStorage and sessionStorage
    localStorage.clear();
    sessionStorage.clear();

    // Reset fetch mock
    fetch.mockClear();

    // Reset console mocks
    console.log.mockClear();
    console.error.mockClear();
    console.warn.mockClear();

    // Reset DOM
    document.body.innerHTML = '';
    document.head.innerHTML = '';
});

// Global setup
beforeAll(() => {
    // Set up global test environment
    global.testStartTime = Date.now();
});

// Global teardown
afterAll(() => {
    // Clean up global test environment
    const testDuration = Date.now() - global.testStartTime;
    console.log(`Total test duration: ${testDuration}ms`);
});