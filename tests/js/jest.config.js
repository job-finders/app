/**
 * Jest Configuration for Job Actions JavaScript Tests
 *
 * Configures Jest testing framework for frontend JavaScript testing
 * including unit tests, integration tests, and end-to-end tests.
 */

module.exports = {
    // Test environment
    testEnvironment: 'jsdom',

    // Test file patterns
    testMatch: [
        '**/tests/js/**/*.test.js',
        '**/tests/js/**/test_*.js'
    ],

    // Setup files
    setupFilesAfterEnv: [
        '<rootDir>/tests/js/setup.js'
    ],

    // Module paths
    moduleNameMapping: {
        '^@/(.*)$': '<rootDir>/static/js/$1',
        '^@components/(.*)$': '<rootDir>/static/js/components/$1',
        '^@utils/(.*)$': '<rootDir>/static/js/utils/$1'
    },

    // Coverage configuration
    collectCoverage: true,
    collectCoverageFrom: [
        'static/js/**/*.js',
        '!static/js/lib/**',
        '!static/js/vendor/**',
        '!static/js/**/*.min.js'
    ],
    coverageDirectory: 'tests/js/coverage',
    coverageReporters: [
        'text',
        'html',
        'lcov',
        'json-summary'
    ],
    coverageThreshold: {
        global: {
            branches: 80,
            functions: 85,
            lines: 85,
            statements: 85
        },
        './static/js/jobs/job-actions.js': {
            branches: 90,
            functions: 95,
            lines: 95,
            statements: 95
        },
        './static/js/components/share-modal.js': {
            branches: 85,
            functions: 90,
            lines: 90,
            statements: 90
        }
    },

    // Transform configuration
    transform: {
        '^.+\\.js$': 'babel-jest'
    },

    // Module file extensions
    moduleFileExtensions: [
        'js',
        'json'
    ],

    // Test timeout
    testTimeout: 10000,

    // Verbose output
    verbose: true,

    // Clear mocks between tests
    clearMocks: true,

    // Restore mocks after each test
    restoreMocks: true,

    // Mock configuration
    moduleNameMapping: {
        '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
    },

    // Global variables
    globals: {
        'window': {},
        'document': {},
        'navigator': {},
        'fetch': jest.fn()
    },

    // Test results processor
    testResultsProcessor: 'jest-sonar-reporter',

    // Reporters
    reporters: [
        'default',
        ['jest-html-reporters', {
            publicPath: './tests/js/coverage/html-report',
            filename: 'report.html',
            expand: true
        }]
    ],

    // Watch plugins
    watchPlugins: [
        'jest-watch-typeahead/filename',
        'jest-watch-typeahead/testname'
    ],

    // Error handling
    errorOnDeprecated: true,

    // Performance monitoring
    detectOpenHandles: true,
    detectLeaks: true,

    // Snapshot configuration
    snapshotSerializers: [
        'jest-serializer-html'
    ]
};