/**
 * Job Statistics Charts
 * 
 * Handles Chart.js integration and chart rendering for job statistics
 */

class JobStatisticsCharts {
    constructor() {
        this.charts = {};
        this.initializeCharts();
    }

    initializeCharts() {
        // Initialize application trend chart
        this.initApplicationTrendChart();
        
        // Initialize match score distribution chart
        this.initMatchScoreChart();
        
        // Initialize responsive behavior
        this.setupResponsiveCharts();
    }

    initApplicationTrendChart() {
        const canvas = document.getElementById('applicationTrendChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Get data from template (passed via data attributes or global variables)
        const chartData = window.jobStatisticsData?.trends?.daily_applications || [];
        
        if (chartData.length === 0) {
            this.showNoDataMessage(canvas, 'No application trend data available');
            return;
        }

        const config = {
            type: 'line',
            data: {
                labels: chartData.map(point => this.formatDate(point.date)),
                datasets: [{
                    label: 'Applications',
                    data: chartData.map(point => point.count),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1,
                    fill: true,
                    pointBackgroundColor: 'rgb(75, 192, 192)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1,
                        callbacks: {
                            title: function(context) {
                                return `Date: ${context[0].label}`;
                            },
                            label: function(context) {
                                const count = context.parsed.y;
                                return `${count} application${count !== 1 ? 's' : ''}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Applications',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                return Number.isInteger(value) ? value : '';
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            }
        };

        this.charts.applicationTrend = new Chart(ctx, config);
    }

    initMatchScoreChart() {
        const canvas = document.getElementById('matchScoreChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const distributionData = window.jobStatisticsData?.competitiveness?.match_score_distribution || {};
        
        if (Object.keys(distributionData).length === 0) {
            this.showNoDataMessage(canvas, 'No match score data available');
            return;
        }

        const labels = Object.keys(distributionData);
        const data = Object.values(distributionData);
        const colors = [
            'rgba(220, 53, 69, 0.8)',   // Red for 0-20
            'rgba(255, 193, 7, 0.8)',   // Yellow for 21-40
            'rgba(255, 193, 7, 0.8)',   // Yellow for 41-60
            'rgba(40, 167, 69, 0.8)',   // Green for 61-80
            'rgba(40, 167, 69, 0.8)'    // Green for 81-100
        ];

        const config = {
            type: 'doughnut',
            data: {
                labels: labels.map(label => `${label}%`),
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderColor: '#fff',
                    borderWidth: 2,
                    hoverOffset: 4
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
                            usePointStyle: true,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        callbacks: {
                            label: function(context) {
                                const label = context.label;
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} applicants (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        };

        this.charts.matchScore = new Chart(ctx, config);
    }

    setupResponsiveCharts() {
        // Handle window resize
        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        });

        // Handle mobile-specific adjustments
        if (window.innerWidth < 768) {
            this.adjustChartsForMobile();
        }
    }

    adjustChartsForMobile() {
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.options) {
                // Reduce font sizes for mobile
                if (chart.options.scales) {
                    Object.values(chart.options.scales).forEach(scale => {
                        if (scale.title && scale.title.font) {
                            scale.title.font.size = 10;
                        }
                    });
                }
                
                // Update chart
                chart.update();
            }
        });
    }

    showNoDataMessage(canvas, message) {
        const ctx = canvas.getContext('2d');
        const container = canvas.parentElement;
        
        // Create no-data message
        const noDataDiv = document.createElement('div');
        noDataDiv.className = 'text-center py-4';
        noDataDiv.innerHTML = `
            <i class="fas fa-chart-line fa-2x text-muted mb-2"></i>
            <p class="text-muted mb-0">${message}</p>
        `;
        
        // Hide canvas and show message
        canvas.style.display = 'none';
        container.appendChild(noDataDiv);
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
    }

    // Public method to update charts with new data
    updateCharts(newData) {
        window.jobStatisticsData = newData;
        
        // Destroy existing charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        // Reinitialize with new data
        this.charts = {};
        this.initializeCharts();
    }

    // Public method to destroy all charts
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we have chart containers
    if (document.querySelector('#applicationTrendChart, #matchScoreChart')) {
        window.jobStatisticsCharts = new JobStatisticsCharts();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JobStatisticsCharts;
}