/**
 * Job Statistics Tooltips
 * 
 * Handles explanatory tooltips and help text for job statistics
 */

class JobStatisticsTooltips {
    constructor() {
        this.tooltips = new Map();
        this.initializeTooltips();
        this.setupEventListeners();
    }

    initializeTooltips() {
        // Define tooltip content for different statistics
        this.tooltipContent = {
            'total-applications': {
                title: 'Total Applications',
                content: 'The total number of applications received for this job since it was posted. A higher number indicates more competition.'
            },
            'applications-per-day': {
                title: 'Applications per Day',
                content: 'Average number of applications received daily. This helps gauge the job\'s popularity and urgency of applying.'
            },
            'competition-level': {
                title: 'Competition Level',
                content: 'Based on application rate: Low (< 2/day) - good opportunity, Medium (2-5/day) - moderate competition, High (> 5/day) - many applicants. Higher competition means you should tailor your application carefully and apply quickly.'
            },
            'match-score': {
                title: 'Average Match Score',
                content: 'Average ATS (Applicant Tracking System) score of all applicants. Scores above 75% indicate strong matches, 50-75% are good matches, while below 50% suggests opportunity for well-qualified candidates to stand out.'
            },
            'ats-readiness': {
                title: 'Well-Matched Applicants',
                content: 'Percentage of applicants with ATS scores of 75% or higher. This indicates the quality of competition you\'re facing.'
            },
            'application-velocity': {
                title: 'Application Velocity',
                content: 'Whether applications are accelerating (increasing rapidly), decelerating (slowing down), or steady. Accelerating trends suggest growing interest.'
            },
            'trend-direction': {
                title: 'Overall Trend',
                content: 'Long-term direction of applications: Increasing (growing interest), Decreasing (declining interest), or Stable (consistent interest).'
            },
            'company-response-rate': {
                title: 'Company Response Rate',
                content: 'Percentage of applications that receive some form of employer response. Higher rates indicate better communication and professionalism.'
            },
            'hiring-activity': {
                title: 'Hiring Activity Level',
                content: 'Based on recent job postings: High (20+ jobs/year), Medium (5-19 jobs/year), Low (< 5 jobs/year). More active companies may have faster hiring processes.'
            },
            'time-to-fill': {
                title: 'Average Time to Fill',
                content: 'Average number of days from job posting to hiring. This gives you an idea of how long the hiring process typically takes at this company.'
            },
            'application-sources': {
                title: 'Application Sources',
                content: 'Shows where applications are coming from (company website, job boards, referrals). This indicates the job\'s visibility and reach across different platforms.'
            },
            'peak-days': {
                title: 'Peak Application Days',
                content: 'Days of the week when this job receives the most applications. Applying on less busy days might help your application get more attention.'
            },
            'industry-comparison': {
                title: 'Industry Comparison',
                content: 'How this job\'s application rate compares to similar positions in the same industry. Above average indicates higher interest or better positioning.'
            }
        };

        // Create tooltip elements
        this.createTooltipElements();
    }

    createTooltipElements() {
        // Find all elements that need tooltips
        const tooltipTriggers = document.querySelectorAll('[data-tooltip]');
        
        tooltipTriggers.forEach(trigger => {
            const tooltipId = trigger.getAttribute('data-tooltip');
            const content = this.tooltipContent[tooltipId];
            
            if (content) {
                // Add tooltip icon
                const icon = document.createElement('i');
                icon.className = 'fas fa-info-circle text-muted ms-1';
                icon.style.cursor = 'pointer';
                icon.style.fontSize = '0.8em';
                
                // Add tooltip attributes for Bootstrap or custom tooltip
                icon.setAttribute('data-bs-toggle', 'tooltip');
                icon.setAttribute('data-bs-placement', 'top');
                icon.setAttribute('data-bs-title', content.content);
                icon.setAttribute('data-bs-html', 'true');
                
                trigger.appendChild(icon);
                
                // Store reference
                this.tooltips.set(tooltipId, {
                    element: icon,
                    content: content
                });
            }
        });
    }

    setupEventListeners() {
        // Initialize Bootstrap tooltips if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl, {
                    delay: { show: 300, hide: 100 },
                    trigger: 'hover focus'
                });
            });
        } else {
            // Fallback to custom tooltip implementation
            this.setupCustomTooltips();
        }

        // Add click handlers for detailed explanations
        this.setupDetailedExplanations();
    }

    setupCustomTooltips() {
        // Create custom tooltip container
        const tooltipContainer = document.createElement('div');
        tooltipContainer.id = 'custom-tooltip';
        tooltipContainer.className = 'custom-tooltip';
        tooltipContainer.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            max-width: 250px;
            z-index: 1000;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            word-wrap: break-word;
        `;
        document.body.appendChild(tooltipContainer);

        // Add event listeners for custom tooltips
        this.tooltips.forEach((tooltip, id) => {
            const element = tooltip.element;
            
            element.addEventListener('mouseenter', (e) => {
                tooltipContainer.textContent = tooltip.content.content;
                tooltipContainer.style.opacity = '1';
                this.positionTooltip(e, tooltipContainer);
            });

            element.addEventListener('mouseleave', () => {
                tooltipContainer.style.opacity = '0';
            });

            element.addEventListener('mousemove', (e) => {
                this.positionTooltip(e, tooltipContainer);
            });
        });
    }

    positionTooltip(event, tooltip) {
        const x = event.clientX;
        const y = event.clientY;
        const tooltipRect = tooltip.getBoundingClientRect();
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;

        let left = x + 10;
        let top = y - tooltipRect.height - 10;

        // Adjust if tooltip goes off screen
        if (left + tooltipRect.width > windowWidth) {
            left = x - tooltipRect.width - 10;
        }
        
        if (top < 0) {
            top = y + 10;
        }

        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    }

    setupDetailedExplanations() {
        // Add click handlers for "Learn More" functionality
        const learnMoreButtons = document.querySelectorAll('[data-learn-more]');
        
        learnMoreButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const topic = button.getAttribute('data-learn-more');
                this.showDetailedExplanation(topic);
            });
        });
    }

    showDetailedExplanation(topic) {
        const explanations = {
            'ats-scores': {
                title: 'Understanding ATS Scores',
                content: `
                    <p><strong>ATS (Applicant Tracking System) scores</strong> measure how well a resume matches a job posting:</p>
                    <ul>
                        <li><strong>81-100%:</strong> Excellent match - Strong alignment with job requirements</li>
                        <li><strong>61-80%:</strong> Good match - Most requirements met</li>
                        <li><strong>41-60%:</strong> Fair match - Some requirements met, room for improvement</li>
                        <li><strong>21-40%:</strong> Poor match - Few requirements met</li>
                        <li><strong>0-20%:</strong> Very poor match - Minimal alignment</li>
                    </ul>
                    <p><em>Tip: Aim for 75% or higher to increase your chances of getting noticed.</em></p>
                `
            },
            'competition-analysis': {
                title: 'Competition Analysis Guide',
                content: `
                    <p><strong>Understanding job competition levels:</strong></p>
                    <ul>
                        <li><strong>Low Competition:</strong> < 2 applications/day - Good opportunity to stand out</li>
                        <li><strong>Medium Competition:</strong> 2-5 applications/day - Moderate competition</li>
                        <li><strong>High Competition:</strong> > 5 applications/day - Many applicants, ensure your application is exceptional</li>
                    </ul>
                    <p><strong>Application trends:</strong></p>
                    <ul>
                        <li><strong>Increasing:</strong> Growing interest - Apply soon</li>
                        <li><strong>Stable:</strong> Consistent interest - Normal timeline</li>
                        <li><strong>Decreasing:</strong> Declining interest - May indicate issues or position being filled</li>
                    </ul>
                `
            },
            'company-insights': {
                title: 'Company Hiring Insights',
                content: `
                    <p><strong>Response Rate Indicators:</strong></p>
                    <ul>
                        <li><strong>Excellent (70%+):</strong> Company actively communicates with applicants</li>
                        <li><strong>Good (50-69%):</strong> Reasonable communication practices</li>
                        <li><strong>Fair (30-49%):</strong> Limited communication, consider following up</li>
                        <li><strong>Poor (<30%):</strong> Minimal communication, manage expectations</li>
                    </ul>
                    <p><strong>Hiring Activity Levels:</strong></p>
                    <ul>
                        <li><strong>High Activity:</strong> 20+ jobs/year - Fast-growing company, potentially quicker decisions</li>
                        <li><strong>Medium Activity:</strong> 5-19 jobs/year - Steady growth, standard processes</li>
                        <li><strong>Low Activity:</strong> < 5 jobs/year - Selective hiring, potentially longer process</li>
                    </ul>
                `
            }
        };

        const explanation = explanations[topic];
        if (explanation) {
            this.createModal(explanation.title, explanation.content);
        }
    }

    createModal(title, content) {
        // Create modal backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';
        backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1050;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        // Create modal content
        const modal = document.createElement('div');
        modal.className = 'explanation-modal';
        modal.style.cssText = `
            background: white;
            border-radius: 8px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            margin: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        `;

        modal.innerHTML = `
            <div style="padding: 20px; border-bottom: 1px solid #dee2e6;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h5 style="margin: 0; color: #333;">${title}</h5>
                    <button type="button" class="close-modal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">×</button>
                </div>
            </div>
            <div style="padding: 20px;">
                ${content}
            </div>
        `;

        backdrop.appendChild(modal);
        document.body.appendChild(backdrop);

        // Add close functionality
        const closeBtn = modal.querySelector('.close-modal');
        const closeModal = () => {
            document.body.removeChild(backdrop);
        };

        closeBtn.addEventListener('click', closeModal);
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                closeModal();
            }
        });

        // Close on escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    }

    // Public method to add new tooltips dynamically
    addTooltip(elementId, content) {
        const element = document.getElementById(elementId);
        if (element) {
            this.tooltipContent[elementId] = content;
            
            const icon = document.createElement('i');
            icon.className = 'fas fa-info-circle text-muted ms-1';
            icon.style.cursor = 'pointer';
            icon.style.fontSize = '0.8em';
            
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                icon.setAttribute('data-bs-toggle', 'tooltip');
                icon.setAttribute('data-bs-placement', 'top');
                icon.setAttribute('data-bs-title', content.content);
                new bootstrap.Tooltip(icon);
            }
            
            element.appendChild(icon);
            this.tooltips.set(elementId, { element: icon, content: content });
        }
    }

    // Public method to destroy all tooltips
    destroy() {
        // Remove custom tooltip container
        const customTooltip = document.getElementById('custom-tooltip');
        if (customTooltip) {
            customTooltip.remove();
        }

        // Clear tooltips map
        this.tooltips.clear();
    }
}

// Initialize tooltips when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.jobStatisticsTooltips = new JobStatisticsTooltips();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JobStatisticsTooltips;
}