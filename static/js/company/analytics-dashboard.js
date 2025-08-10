/**
 * Job Actions Analytics Dashboard JavaScript
 * Handles chart rendering, data updates, and user interactions
 */

let engagementTrendsChart = null;
let conversionChart = null;
let currentDashboardData = null;

/**
 * Initialize the analytics dashboard
 */
function initializeAnalyticsDashboard(data) {
    currentDashboardData = data;

    // Initialize charts
    initializeEngagementTrendsChart(data.actionsReport.engagement_trends || {});
    initializeConversionChart(data.actionsReport.conversion_metrics || {});

    // Set up event listeners
    setupEventListeners();

    console.log('Analytics dashboard initialized');
}

/**
 * Initialize the engagement trends chart
 */
function initializeEngagementTrendsChart(trendsData) {
    const ctx = document.getElementById('engagementTrendsChart');
    if (!ctx) return;

    const likes = trendsData.likes || [];
    const saves = trendsData.saves || [];
    const shares = trendsData.shares || [];

    // Generate labels for the last N days
    const labels = generateDateLabels(likes.length || 30);

    engagementTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Likes',
                    data: likes,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Saves',
                    data: saves,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Shares',
                    data: shares,
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Date'
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Engagement Count'
                    },
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

/**
 * Initialize the conversion metrics chart
 */
function initializeConversionChart(conversionData) {
    const ctx = document.getElementById('conversionChart');
    if (!ctx) return;

    const data = [
        conversionData.save_to_apply_rate || 0,
        conversionData.like_to_apply_rate || 0,
        conversionData.share_to_apply_rate || 0,
        conversionData.overall_engagement_to_apply_rate || 0
    ];

    const labels = [
        'Save to Apply',
        'Like to Apply',
        'Share to Apply',
        'Overall Conversion'
    ];

    conversionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#3498db',
                    '#e74c3c',
                    '#2ecc71',
                    '#f39c12'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return context.label + ': ' + context.parsed.toFixed(1) + '%';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Generate date labels for the chart
 */
function generateDateLabels(days) {
    const labels = [];
    const today = new Date();

    for (let i = days - 1; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
        }));
    }

    return labels;
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Period selector change
    const periodSelect = document.getElementById('periodSelect');
    if (periodSelect) {
        periodSelect.addEventListener('change', updateDashboard);
    }
}

/**
 * Update dashboard data based on selected period
 */
async function updateDashboard() {
    const periodSelect = document.getElementById('periodSelect');
    const selectedPeriod = periodSelect ? periodSelect.value : '30';

    showLoadingOverlay();

    try {
        // Fetch updated data
        const response = await fetch(`/api/company/${currentDashboardData.companyId}/analytics-report?days=${selectedPeriod}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch analytics data');
        }

        const result = await response.json();

        if (result.success) {
            // Update dashboard with new data
            updateDashboardMetrics(result.data);
            updateCharts(result.data);
            updateTopJobsTable(result.data.top_performing_jobs || []);
        } else {
            showError('Failed to load analytics data: ' + result.message);
        }

    } catch (error) {
        console.error('Error updating dashboard:', error);
        showError('Failed to load analytics data. Please try again.');
    } finally {
        hideLoadingOverlay();
    }
}

/**
 * Update dashboard metrics
 */
function updateDashboardMetrics(data) {
    // Update engagement stats if available
    const engagementStats = data.engagement_stats || {};

    updateMetricValue('totalLikes', engagementStats.total_job_likes || 0);
    updateMetricValue('totalSaves', engagementStats.total_job_saves || 0);
    updateMetricValue('totalShares', engagementStats.total_job_shares || 0);
    updateMetricValue('avgEngagement', (engagementStats.average_engagement_per_job || 0).toFixed(1));

    // Update growth indicators
    const growthRate = engagementStats.engagement_growth_rate || 0;
    updateGrowthIndicators(growthRate);
}

/**
 * Update a metric value in the UI
 */
function updateMetricValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

/**
 * Update growth indicators
 */
function updateGrowthIndicators(growthRate) {
    const indicators = ['likesChange', 'savesChange', 'sharesChange'];

    indicators.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = `${growthRate >= 0 ? '+' : ''}${growthRate.toFixed(1)}%`;
            element.className = `metric-change ${growthRate >= 0 ? 'positive' : 'negative'}`;
        }
    });
}

/**
 * Update charts with new data
 */
function updateCharts(data) {
    // Update engagement trends chart
    if (engagementTrendsChart && data.engagement_trends) {
        const trends = data.engagement_trends;
        const labels = generateDateLabels(trends.likes?.length || 30);

        engagementTrendsChart.data.labels = labels;
        engagementTrendsChart.data.datasets[0].data = trends.likes || [];
        engagementTrendsChart.data.datasets[1].data = trends.saves || [];
        engagementTrendsChart.data.datasets[2].data = trends.shares || [];
        engagementTrendsChart.update();
    }

    // Update conversion chart
    if (conversionChart && data.conversion_metrics) {
        const metrics = data.conversion_metrics;
        conversionChart.data.datasets[0].data = [
            metrics.save_to_apply_rate || 0,
            metrics.like_to_apply_rate || 0,
            metrics.share_to_apply_rate || 0,
            metrics.overall_engagement_to_apply_rate || 0
        ];
        conversionChart.update();
    }
}

/**
 * Update top jobs table
 */
function updateTopJobsTable(jobs) {
    const tableBody = document.getElementById('topJobsTable');
    if (!tableBody) return;

    if (jobs.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="no-data">
                    No engagement data available for the selected period.
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = jobs.slice(0, 10).map(job => `
        <tr>
            <td>
                <div class="job-title">
                    <strong>${escapeHtml(job.title)}</strong>
                </div>
            </td>
            <td>
                <span class="engagement-count likes">
                    <i class="fas fa-heart"></i> ${job.total_likes}
                </span>
            </td>
            <td>
                <span class="engagement-count saves">
                    <i class="fas fa-bookmark"></i> ${job.total_saves}
                </span>
            </td>
            <td>
                <span class="engagement-count shares">
                    <i class="fas fa-share"></i> ${job.total_shares}
                </span>
            </td>
            <td>
                <strong>${job.total_engagement}</strong>
            </td>
            <td>
                <a href="/jobs/${job.job_id}/performance" class="btn btn-sm btn-outline">
                    View Details
                </a>
            </td>
        </tr>
    `).join('');
}

/**
 * Show loading overlay
 */
function showLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

/**
 * Hide loading overlay
 */
function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Show error message
 */
function showError(message) {
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <span>${escapeHtml(message)}</span>
    `;

    // Add toast styles
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #e74c3c;
        color: white;
        padding: 12px 16px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        max-width: 300px;
    `;

    document.body.appendChild(toast);

    // Remove toast after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Export data functionality
 */
function exportAnalyticsData(format = 'csv') {
    if (!currentDashboardData) {
        showError('No data available to export');
        return;
    }

    const data = currentDashboardData.actionsReport;

    if (format === 'csv') {
        exportToCSV(data);
    } else if (format === 'json') {
        exportToJSON(data);
    }
}

/**
 * Export data to CSV
 */
function exportToCSV(data) {
    const jobs = data.top_performing_jobs || [];

    if (jobs.length === 0) {
        showError('No job data available to export');
        return;
    }

    const headers = ['Job Title', 'Job ID', 'Likes', 'Saves', 'Shares', 'Total Engagement'];
    const csvContent = [
        headers.join(','),
        ...jobs.map(job => [
            `"${job.title.replace(/"/g, '""')}"`,
            job.job_id,
            job.total_likes,
            job.total_saves,
            job.total_shares,
            job.total_engagement
        ].join(','))
    ].join('\n');

    downloadFile(csvContent, 'job-analytics.csv', 'text/csv');
}

/**
 * Export data to JSON
 */
function exportToJSON(data) {
    const jsonContent = JSON.stringify(data, null, 2);
    downloadFile(jsonContent, 'job-analytics.json', 'application/json');
}

/**
 * Download file
 */
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], {type: contentType});
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}

// Make functions available globally
window.initializeAnalyticsDashboard = initializeAnalyticsDashboard;
window.updateDashboard = updateDashboard;
window.exportAnalyticsData = exportAnalyticsData;