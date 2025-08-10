/**
 * Job Actions Monitoring Dashboard JavaScript
 *
 * Handles real-time monitoring dashboard functionality including:
 * - Metrics visualization with Chart.js
 * - Real-time data updates
 * - Alert management
 * - Health status monitoring
 * - Data export functionality
 */

class JobActionsMonitoringDashboard {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.currentTimeRange = 60; // minutes
        this.isLoading = false;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.loadDashboardData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadDashboardData();
        });

        // Export button
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportData();
        });

        // Time range selector
        document.getElementById('timeRangeSelect').addEventListener('change', (e) => {
            this.currentTimeRange = parseInt(e.target.value);
            this.loadDashboardData();
        });

        // Chart toggle buttons
        document.querySelectorAll('.chart-toggle').forEach(button => {
            button.addEventListener('click', (e) => {
                this.toggleChartMetric(e.target.dataset.metric);

                // Update active state
                document.querySelectorAll('.chart-toggle').forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
            });
        });

        // Alert dismiss
        document.getElementById('dismissAlert').addEventListener('click', () => {
            this.hideAlert();
        });
    }

    initializeCharts() {
        // Actions Over Time Chart
        const actionsCtx = document.getElementById('actionsChart').getContext('2d');
        this.charts.actions = new Chart(actionsCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Total Actions',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        // Response Time Chart
        const responseTimeCtx = document.getElementById('responseTimeChart').getContext('2d');
        this.charts.responseTime = new Chart(responseTimeCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Response Time (ms)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Response Time (ms)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        // Error Rate Chart
        const errorRateCtx = document.getElementById('errorRateChart').getContext('2d');
        this.charts.errorRate = new Chart(errorRateCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Error Rate (%)',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Error Rate (%)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        // System Resources Chart
        const systemResourcesCtx = document.getElementById('systemResourcesChart').getContext('2d');
        this.charts.systemResources = new Chart(systemResourcesCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Memory Usage (%)',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.4
                    },
                    {
                        label: 'CPU Usage (%)',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Usage (%)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    }

    async loadDashboardData() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading();

        try {
            // Load main metrics
            const metricsResponse = await fetch(`/admin/job-actions-monitoring/api/metrics?time_window=${this.currentTimeRange}`);
            const metricsData = await metricsResponse.json();

            if (metricsData.success) {
                this.updateSummaryCards(metricsData.data.summary);
                this.updateCharts(metricsData.data.metrics_history);
                this.updateAlertsTable(metricsData.data.active_alerts, metricsData.data.alert_definitions);
            }

            // Load database stats
            const dbStatsResponse = await fetch('/admin/job-actions-monitoring/api/database-stats');
            const dbStatsData = await dbStatsResponse.json();

            if (dbStatsData.success) {
                this.updateTopJobsTable(dbStatsData.data.top_jobs);
                this.updatePlatformStatsTable(dbStatsData.data.platform_stats);
                this.updateDatabaseStatsTable(dbStatsData.data.table_stats);
            }

            // Load health status
            const healthResponse = await fetch('/admin/job-actions-monitoring/api/health');
            const healthData = await healthResponse.json();

            if (healthData.success) {
                this.updateHealthStatus(healthData.data);
            }

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showAlert('Error loading dashboard data. Please try again.', 'error');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    updateSummaryCards(summary) {
        document.getElementById('totalActions').textContent = this.formatNumber(summary.total_actions);
        document.getElementById('errorRate').textContent = `${summary.error_rate_percent}%`;
        document.getElementById('avgResponseTime').textContent = `${summary.avg_response_time_ms}ms`;
        document.getElementById('activeAlerts').textContent = summary.active_alerts;

        // Update change indicators (placeholder - would need historical data)
        document.getElementById('totalActionsChange').textContent = '+5.2%';
        document.getElementById('errorRateChange').textContent = '-0.3%';
        document.getElementById('responseTimeChange').textContent = '+12ms';
        document.getElementById('alertsChange').textContent = summary.active_alerts > 0 ? '+' + summary.active_alerts : '0';

        // Apply styling based on values
        this.updateCardStyling('errorRate', summary.error_rate_percent, 5, 10);
        this.updateCardStyling('avgResponseTime', summary.avg_response_time_ms, 1000, 2000);
        this.updateCardStyling('activeAlerts', summary.active_alerts, 1, 3);
    }

    updateCardStyling(cardId, value, warningThreshold, criticalThreshold) {
        const card = document.getElementById(cardId).closest('.summary-card');
        card.classList.remove('warning', 'critical');

        if (value >= criticalThreshold) {
            card.classList.add('critical');
        } else if (value >= warningThreshold) {
            card.classList.add('warning');
        }
    }

    updateCharts(metricsHistory) {
        // Update Actions Chart
        if (metricsHistory.job_actions_total) {
            const actionsData = metricsHistory.job_actions_total;
            this.charts.actions.data.labels = actionsData.map(point => new Date(point.timestamp));
            this.charts.actions.data.datasets[0].data = actionsData.map(point => point.value);
            this.charts.actions.update('none');
        }

        // Update Response Time Chart
        if (metricsHistory.job_actions_response_time) {
            const responseTimeData = metricsHistory.job_actions_response_time;
            this.charts.responseTime.data.labels = responseTimeData.map(point => new Date(point.timestamp));
            this.charts.responseTime.data.datasets[0].data = responseTimeData.map(point => point.value);
            this.charts.responseTime.update('none');
        }

        // Update Error Rate Chart
        if (metricsHistory.job_actions_errors && metricsHistory.job_actions_total) {
            const errorData = metricsHistory.job_actions_errors;
            const totalData = metricsHistory.job_actions_total;

            // Calculate error rate over time
            const errorRateData = errorData.map((errorPoint, index) => {
                const totalPoint = totalData[index];
                if (totalPoint && totalPoint.value > 0) {
                    return {
                        timestamp: errorPoint.timestamp,
                        value: (errorPoint.value / totalPoint.value) * 100
                    };
                }
                return {timestamp: errorPoint.timestamp, value: 0};
            });

            this.charts.errorRate.data.labels = errorRateData.map(point => new Date(point.timestamp));
            this.charts.errorRate.data.datasets[0].data = errorRateData.map(point => point.value);
            this.charts.errorRate.update('none');
        }

        // Update System Resources Chart (placeholder data)
        if (metricsHistory.memory_usage_percent) {
            const memoryData = metricsHistory.memory_usage_percent;
            this.charts.systemResources.data.labels = memoryData.map(point => new Date(point.timestamp));
            this.charts.systemResources.data.datasets[0].data = memoryData.map(point => point.value);

            // Add CPU data if available
            if (metricsHistory.cpu_usage_percent) {
                const cpuData = metricsHistory.cpu_usage_percent;
                this.charts.systemResources.data.datasets[1].data = cpuData.map(point => point.value);
            }

            this.charts.systemResources.update('none');
        }
    }

    updateTopJobsTable(topJobs) {
        const tbody = document.querySelector('#topJobsTable tbody');
        tbody.innerHTML = '';

        topJobs.forEach(job => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="job-title">${this.escapeHtml(job.title)}</div>
                    <div class="job-id">ID: ${job.job_id}</div>
                </td>
                <td><span class="metric-badge likes">${job.like_count}</span></td>
                <td><span class="metric-badge shares">${job.share_count}</span></td>
                <td><span class="metric-badge total">${job.total_engagement}</span></td>
            `;
            tbody.appendChild(row);
        });
    }

    updatePlatformStatsTable(platformStats) {
        const tbody = document.querySelector('#platformStatsTable tbody');
        tbody.innerHTML = '';

        const totalShares = platformStats.reduce((sum, platform) => sum + platform.total_shares, 0);

        platformStats.forEach(platform => {
            const percentage = totalShares > 0 ? ((platform.total_shares / totalShares) * 100).toFixed(1) : 0;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="platform-name">
                        <i class="fab fa-${platform.platform.toLowerCase()}"></i>
                        ${this.capitalizeFirst(platform.platform)}
                    </div>
                </td>
                <td>${this.formatNumber(platform.total_shares)}</td>
                <td>${this.formatNumber(platform.recent_shares)}</td>
                <td>
                    <div class="percentage-bar">
                        <div class="percentage-fill" style="width: ${percentage}%"></div>
                        <span class="percentage-text">${percentage}%</span>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updateAlertsTable(activeAlerts, alertDefinitions) {
        const tbody = document.querySelector('#alertsTable tbody');
        tbody.innerHTML = '';

        if (activeAlerts.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="4" class="no-data">No active alerts</td>';
            tbody.appendChild(row);
            return;
        }

        activeAlerts.forEach(alertName => {
            const alertDef = alertDefinitions[alertName];
            if (alertDef) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${this.escapeHtml(alertDef.name)}</td>
                    <td><span class="severity-badge ${alertDef.severity}">${alertDef.severity}</span></td>
                    <td><span class="status-badge active">Active</span></td>
                    <td>${alertDef.last_triggered ? this.formatDateTime(alertDef.last_triggered) : 'N/A'}</td>
                `;
                tbody.appendChild(row);
            }
        });

        // Show alert banner if there are critical alerts
        const criticalAlerts = activeAlerts.filter(name =>
            alertDefinitions[name] && alertDefinitions[name].severity === 'critical'
        );

        if (criticalAlerts.length > 0) {
            this.showAlert(`${criticalAlerts.length} critical alert(s) active`, 'critical');
        }
    }

    updateDatabaseStatsTable(tableStats) {
        const tbody = document.querySelector('#databaseStatsTable tbody');
        tbody.innerHTML = '';

        tableStats.forEach(table => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.escapeHtml(table.table_name)}</td>
                <td>${this.formatNumber(table.row_count)}</td>
                <td>${table.size_mb.toFixed(2)}</td>
                <td>${table.index_mb.toFixed(2)}</td>
            `;
            tbody.appendChild(row);
        });
    }

    updateHealthStatus(healthData) {
        const monitorHealth = healthData.monitor_health;
        const detailedHealth = healthData.detailed_health;

        // Update health score
        const healthScore = monitorHealth.health_score;
        document.getElementById('healthScoreValue').textContent = healthScore;

        const scoreCircle = document.getElementById('healthScoreCircle');
        scoreCircle.className = 'score-circle';

        if (healthScore >= 90) {
            scoreCircle.classList.add('excellent');
        } else if (healthScore >= 70) {
            scoreCircle.classList.add('good');
        } else if (healthScore >= 50) {
            scoreCircle.classList.add('warning');
        } else {
            scoreCircle.classList.add('critical');
        }

        // Update individual health checks
        this.updateHealthCheck('databaseCheck', detailedHealth.checks.database);
        this.updateHealthCheck('tablesCheck', detailedHealth.checks.tables);
        this.updateHealthCheck('indexesCheck', detailedHealth.checks.indexes);
        this.updateHealthCheck('alertsCheck', {status: 'healthy'}); // Placeholder

        // Show issues if any
        if (monitorHealth.issues.length > 0) {
            const issuesContainer = document.getElementById('healthIssues');
            const issuesList = document.getElementById('issuesList');

            issuesList.innerHTML = '';
            monitorHealth.issues.forEach(issue => {
                const li = document.createElement('li');
                li.textContent = issue;
                issuesList.appendChild(li);
            });

            issuesContainer.style.display = 'block';
        } else {
            document.getElementById('healthIssues').style.display = 'none';
        }
    }

    updateHealthCheck(checkId, checkData) {
        const checkElement = document.getElementById(checkId);
        const statusElement = checkElement.querySelector('.check-status');

        checkElement.className = 'health-check';

        if (checkData.status === 'healthy') {
            checkElement.classList.add('healthy');
            statusElement.innerHTML = '<i class="fas fa-check"></i> Healthy';
        } else {
            checkElement.classList.add('unhealthy');
            statusElement.innerHTML = '<i class="fas fa-times"></i> Unhealthy';
        }
    }

    toggleChartMetric(metric) {
        // This would switch between different metrics in the actions chart
        // For now, it's a placeholder for future functionality
        console.log('Toggling chart metric:', metric);
    }

    async exportData() {
        try {
            const response = await fetch(`/admin/job-actions-monitoring/api/export-metrics?time_window=${this.currentTimeRange}&format=json`);
            const data = await response.json();

            if (data.success) {
                // Create and download file
                const blob = new Blob([JSON.stringify(data.data, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `job_actions_metrics_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                this.showAlert('Metrics data exported successfully', 'success');
            } else {
                this.showAlert('Failed to export data', 'error');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showAlert('Error exporting data', 'error');
        }
    }

    startAutoRefresh() {
        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showAlert(message, type = 'info') {
        const alertBanner = document.getElementById('alertBanner');
        const alertMessage = document.getElementById('alertMessage');

        alertMessage.textContent = message;
        alertBanner.className = `alert-banner ${type}`;
        alertBanner.style.display = 'block';

        // Auto-hide after 5 seconds for non-critical alerts
        if (type !== 'critical') {
            setTimeout(() => {
                this.hideAlert();
            }, 5000);
        }
    }

    hideAlert() {
        document.getElementById('alertBanner').style.display = 'none';
    }

    showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }

    // Utility functions
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    formatDateTime(dateString) {
        return new Date(dateString).toLocaleString();
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.monitoringDashboard = new JobActionsMonitoringDashboard();
});

// Handle page visibility changes to pause/resume auto-refresh
document.addEventListener('visibilitychange', () => {
    if (window.monitoringDashboard) {
        if (document.hidden) {
            window.monitoringDashboard.stopAutoRefresh();
        } else {
            window.monitoringDashboard.startAutoRefresh();
        }
    }
});