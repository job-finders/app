function initCandidateAnalysis() {
    let analysisHistory = [];
    let currentAnalysis = null;

    function logEvent(event, data = {}) {
        const jobIdMeta = document.querySelector('meta[name="job_id"]');
        const userIdMeta = document.querySelector('meta[name="user_id"]');

        const logData = {
            timestamp: new Date().toISOString(),
            event: event,
            jobId: jobIdMeta?.getAttribute('content') || null,
            userId: userIdMeta?.getAttribute('content') || null,
            ...data
        };

        console.log('[CandidateAnalysis]', logData);

        if (window.analytics && typeof window.analytics.track === 'function') {
            window.analytics.track('Candidate Analysis ' + event, logData);
        }
    }

    const cvSelect = document.getElementById('cv_select');
    const analyzeBtn = document.getElementById('analyze-btn');
    const matchResults = document.getElementById('match-results');
    const matchSummary = document.getElementById('match-summary');
    const matchScore = document.getElementById('match-score');

    if (cvSelect && analyzeBtn) {
        const cvOptions = cvSelect.querySelectorAll('option[value]:not([value=""])');

        if (cvOptions.length === 0) {
            logEvent('Empty State Detected', {reason: 'no_cvs_available'});

            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Upload CV First';
            analyzeBtn.classList.add('btn-secondary');
            analyzeBtn.classList.remove('btn-outline-primary');

            matchResults.classList.remove('d-none');
            matchSummary.innerHTML = `
                <div class="alert alert-info" role="alert">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>CV Required</strong>
                    <div class="small mt-1">
                        To analyze your match for this position, you need to upload your CV first.
                    </div>
                    <div class="mt-2">
                        <a href="/jobseekers/resumes" class="btn btn-sm btn-primary">
                            <i class="fas fa-upload me-1"></i>Upload CV
                        </a>
                    </div>
                </div>
            `;
            matchScore.innerHTML = '';
            return;
        }

        cvSelect.addEventListener('change', function () {
            logEvent('CV Selection Changed', {
                cvId: this.value,
                cvName: this.options[this.selectedIndex].text
            });

            if (this.value) {
                this.classList.remove('is-invalid');
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-search me-2"></i>Analyze Match';
                analyzeBtn.classList.remove('btn-secondary');
                analyzeBtn.classList.add('btn-outline-primary');

                if (matchResults.classList.contains('d-none') === false) {
                    const currentContent = matchSummary.innerHTML;
                    if (currentContent.includes('CV Required') || currentContent.includes('Please select a CV')) {
                        matchResults.classList.add('d-none');
                    } else if (currentContent.includes('Analysis Summary') || currentContent.includes('Analysis Error')) {
                        matchSummary.innerHTML = `
                            <div class="alert alert-info" role="alert">
                                <i class="fas fa-sync-alt me-2"></i>
                                <strong>CV Changed</strong>
                                <div class="small mt-1">You've selected a different CV. Click "Analyze Match" to run a new analysis.</div>
                            </div>
                        `;
                        matchScore.innerHTML = '';
                    }
                }
            } else {
                analyzeBtn.disabled = true;
                analyzeBtn.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>Select CV';
                analyzeBtn.classList.add('btn-secondary');
                analyzeBtn.classList.remove('btn-outline-primary');
            }
        });

        if (!cvSelect.value) {
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>Select CV';
            analyzeBtn.classList.add('btn-secondary');
            analyzeBtn.classList.remove('btn-outline-primary');
        }

        const helpText = document.createElement('div');
        helpText.className = 'small text-muted mt-1';
        helpText.innerHTML = '<i class="fas fa-info-circle me-1"></i>Select a CV to see how well you match this position';
        cvSelect.parentNode.appendChild(helpText);
    }

    const analysisForm = document.getElementById('analysis-form');
    if (analysisForm) {
        analysisForm.addEventListener('submit', async function (event) {
            event.preventDefault();

            const startTime = performance.now();
            logEvent('Analysis Started', {
                cvId: cvSelect.value,
                cvName: cvSelect.options[cvSelect.selectedIndex].text
            });

            const cvId = cvSelect.value;
            const jobIdMeta = document.querySelector('meta[name="job_id"]');
            const jobId = jobIdMeta?.getAttribute('content');

            if (!jobId) {
                matchResults.classList.remove('d-none');
                matchSummary.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>System Error</strong>
                        <div class="small mt-1">Job information is missing. Please refresh the page and try again.</div>
                    </div>
                `;
                matchScore.innerHTML = '';
                return;
            }

            if (!cvId) {
                matchResults.classList.remove('d-none');
                matchSummary.innerHTML = `
                    <div class="alert alert-warning" role="alert">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        <strong>CV Required</strong>
                        <div class="small mt-1">Please select a CV from the dropdown to analyze your match for this position.</div>
                    </div>
                `;
                matchScore.innerHTML = '';

                cvSelect.focus();
                cvSelect.classList.add('is-invalid');

                cvSelect.addEventListener('change', function () {
                    this.classList.remove('is-invalid');
                }, {once: true});

                return;
            }

            matchResults.classList.add('d-none');

            const selectedCvText = cvSelect.options[cvSelect.selectedIndex].text;
            const selectedCvId = cvSelect.value;

            const recentAnalysis = analysisHistory.find(analysis =>
                analysis.cvId === selectedCvId &&
                (new Date() - analysis.timestamp) < 5 * 60 * 1000
            );

            if (recentAnalysis) {
                logEvent('Cache Hit', {
                    cvId: selectedCvId,
                    cacheAge: (new Date() - recentAnalysis.timestamp) / 1000
                });

                matchResults.classList.remove('d-none');

                matchSummary.innerHTML = `
                    <div class="alert alert-info mb-3" role="alert">
                        <i class="fas fa-clock me-2"></i>
                        <strong>Recent Analysis</strong>
                        <div class="small mt-1">
                            Showing recent analysis from ${recentAnalysis.timestamp.toLocaleTimeString()}. 
                            <button type="button" class="btn btn-sm btn-outline-primary ms-2" onclick="this.closest('.alert').remove(); document.getElementById('analysis-form').dispatchEvent(new Event('submit'));">
                                Run New Analysis
                            </button>
                        </div>
                    </div>
                `;

                const data = recentAnalysis.results;
                currentAnalysis = recentAnalysis;

                matchSummary.innerHTML += `
                    <div class="mb-3">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <h6 class="fw-semibold mb-0">Analysis Results</h6>
                            <small class="text-muted">
                                <i class="fas fa-file-alt me-1"></i>${selectedCvText}
                            </small>
                        </div>
                        <p class="small text-muted mb-0">${data.summary}</p>
                    </div>
                `;

                const percentile = Math.round(data.percentile_rank || 0);
                let scoreClass = 'text-danger';
                let scoreLabel = 'Needs Improvement';

                if (percentile >= 75) {
                    scoreClass = 'text-success';
                    scoreLabel = 'Excellent Match';
                } else if (percentile >= 50) {
                    scoreClass = 'text-warning';
                    scoreLabel = 'Good Match';
                } else if (percentile >= 25) {
                    scoreClass = 'text-info';
                    scoreLabel = 'Fair Match';
                }

                matchScore.innerHTML = `
                    <div class="d-flex align-items-center justify-content-between">
                        <span class="fw-semibold">Competitive Position:</span>
                        <span class="${scoreClass} fw-bold">${percentile}th percentile</span>
                    </div>
                    <div class="small ${scoreClass} mt-1">${scoreLabel}</div>
                `;

                return;
            }

            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyzing...';
            analyzeBtn.classList.add('btn-loading');

            matchResults.classList.remove('d-none');

            matchSummary.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="text-muted">
                        <div class="fw-semibold mb-1">Analyzing Your Match</div>
                        <div class="small">Our AI is comparing your CV with the job requirements...</div>
                    </div>
                </div>
            `;
            matchScore.innerHTML = '';

            try {
                logEvent('API Request Started', {endpoint: 'candidate-fit-analysis'});

                const response = await fetch(`/agents/employee/v1/jobs/${jobId}/candidate-fit-analysis`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        cv_id: cvId
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    const duration = performance.now() - startTime;

                    logEvent('Analysis Completed', {
                        cvId: selectedCvId,
                        duration: Math.round(duration),
                        percentileRank: data.percentile_rank,
                        hasKeyStrengths: data.key_strengths && data.key_strengths.length > 0,
                        hasDevelopmentAreas: data.development_areas && data.development_areas.length > 0
                    });

                    currentAnalysis = {
                        cvId: selectedCvId,
                        cvName: selectedCvText,
                        timestamp: new Date(),
                        results: data
                    };

                    analysisHistory.unshift(currentAnalysis);
                    if (analysisHistory.length > 5) {
                        analysisHistory = analysisHistory.slice(0, 5);
                    }

                    analyzeBtn.innerHTML = '<i class="fas fa-check me-2"></i>Analysis Complete';
                    analyzeBtn.classList.add('btn-success');

                    setTimeout(() => {
                        analyzeBtn.innerHTML = '<i class="fas fa-search me-2"></i>Analyze Match';
                        analyzeBtn.classList.remove('btn-success');
                    }, 2000);

                    matchResults.classList.remove('d-none');

                    matchSummary.innerHTML = `
                        <div class="mb-3">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <h6 class="fw-semibold mb-0">Analysis Results</h6>
                                <small class="text-muted">
                                    <i class="fas fa-file-alt me-1"></i>${selectedCvText}
                                </small>
                            </div>
                            <p class="small text-muted mb-0">${data.summary}</p>
                        </div>
                        ${data.key_strengths && data.key_strengths.length > 0 ? `
                        <div class="mb-3">
                            <h6 class="fw-semibold mb-2 text-success">Key Strengths</h6>
                            <ul class="small mb-0">
                                ${data.key_strengths.map(strength => `<li>${strength}</li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        ${data.development_areas && data.development_areas.length > 0 ? `
                        <div class="mb-3">
                            <h6 class="fw-semibold mb-2 text-warning">Areas for Development</h6>
                            <ul class="small mb-0">
                                ${data.development_areas.map(area => `<li>${area}</li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        ${data.candidate_insights && data.candidate_insights.length > 0 ? `
                        <div class="mb-3">
                            <h6 class="fw-semibold mb-2 text-info">Career Insights</h6>
                            <ul class="small mb-0">
                                ${data.candidate_insights.map(insight => `<li>${insight}</li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        ${data.cv_optimization_tips && data.cv_optimization_tips.length > 0 ? `
                        <div class="mb-3">
                            <h6 class="fw-semibold mb-2 text-primary">CV Optimization Tips</h6>
                            <ul class="small mb-0">
                                ${data.cv_optimization_tips.map(tip => `<li>${tip}</li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        ${analysisHistory.length > 1 ? `
                        <div class="mb-3">
                            <h6 class="fw-semibold mb-2 text-secondary">
                                <i class="fas fa-chart-bar me-2"></i>Previous Analyses
                            </h6>
                            <div class="small">
                                ${analysisHistory.slice(1).map(analysis => `
                                    <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                                        <span class="text-muted">${analysis.cvName}</span>
                                        <span class="badge badge-neutral">${Math.round(analysis.results.percentile_rank || 0)}th percentile</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                    `;

                    const percentile = Math.round(data.percentile_rank || 0);
                    let scoreClass = 'text-danger';
                    let scoreLabel = 'Needs Improvement';

                    if (percentile >= 75) {
                        scoreClass = 'text-success';
                        scoreLabel = 'Excellent Match';
                    } else if (percentile >= 50) {
                        scoreClass = 'text-warning';
                        scoreLabel = 'Good Match';
                    } else if (percentile >= 25) {
                        scoreClass = 'text-info';
                        scoreLabel = 'Fair Match';
                    }

                    matchScore.innerHTML = `
                        <div class="d-flex align-items-center justify-content-between">
                            <span class="fw-semibold">Competitive Position:</span>
                            <span class="${scoreClass} fw-bold">${percentile}th percentile</span>
                        </div>
                        <div class="small ${scoreClass} mt-1">${scoreLabel}</div>
                    `;

                } else {
                    const duration = performance.now() - startTime;

                    const errorData = await response.json().catch(() => ({}));

                    logEvent('Analysis Failed', {
                        cvId: selectedCvId,
                        duration: Math.round(duration),
                        statusCode: response.status,
                        errorMessage: errorData.error || 'Unknown error'
                    });

                    matchResults.classList.remove('d-none');
                    matchScore.innerHTML = '';

                    let errorMessage = errorData.error || 'Analysis failed';
                    let errorClass = 'alert-danger';
                    let errorIcon = 'fas fa-exclamation-triangle';
                    let actionButton = '';

                    if (response.status === 401) {
                        errorMessage = 'Please log in to analyze job matches';
                        errorIcon = 'fas fa-sign-in-alt';
                        actionButton = '<div class="mt-2"><a href="/auth/login" class="btn btn-sm btn-primary">Log In</a></div>';
                    } else if (response.status === 400) {
                        if (errorData.error && errorData.error.includes('CV')) {
                            errorMessage = 'There seems to be an issue with your selected CV. Please try selecting a different CV or upload a new one.';
                            errorClass = 'alert-warning';
                            errorIcon = 'fas fa-file-alt';
                            actionButton = '<div class="mt-2"><a href="/jobseekers/resumes" class="btn btn-sm btn-outline-primary">Manage CVs</a></div>';
                        } else {
                            errorMessage = errorData.error || 'Please check your CV selection and try again';
                            errorClass = 'alert-warning';
                            errorIcon = 'fas fa-exclamation-circle';
                        }
                    } else if (response.status === 404) {
                        if (errorData.error && errorData.error.includes('CV')) {
                            errorMessage = 'The selected CV could not be found. It may have been deleted. Please select a different CV.';
                            errorIcon = 'fas fa-file-times';
                            actionButton = '<div class="mt-2"><button type="button" class="btn btn-sm btn-outline-primary" onclick="location.reload()">Refresh Page</button></div>';
                        } else {
                            errorMessage = 'Job information not found. Please refresh the page and try again.';
                            errorIcon = 'fas fa-search';
                            actionButton = '<div class="mt-2"><button type="button" class="btn btn-sm btn-outline-primary" onclick="location.reload()">Refresh Page</button></div>';
                        }
                    } else if (response.status === 500) {
                        errorMessage = 'Our analysis service is temporarily unavailable. Please try again in a few minutes.';
                        errorIcon = 'fas fa-server';
                        actionButton = '<div class="mt-2"><button type="button" class="btn btn-sm btn-outline-primary" onclick="location.reload()">Try Again</button></div>';
                    }

                    matchSummary.innerHTML = `
                        <div class="alert ${errorClass}" role="alert">
                            <i class="${errorIcon} me-2"></i>
                            <strong>Analysis Error</strong>
                            <div class="small mt-1">${errorMessage}</div>
                            ${errorData.details ? `<div class="small mt-2 text-muted">Technical details: ${errorData.details}</div>` : ''}
                            ${actionButton}
                        </div>
                    `;
                }
            } catch (error) {
                const duration = performance.now() - startTime;

                logEvent('Network Error', {
                    cvId: selectedCvId,
                    duration: Math.round(duration),
                    errorType: error.name,
                    errorMessage: error.message
                });

                console.error('Error during candidate analysis:', error);

                let errorMessage = 'An error occurred during the analysis. Please try again.';

                if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    errorMessage = 'Network error. Please check your connection and try again.';
                } else if (error.name === 'AbortError') {
                    errorMessage = 'Request timed out. Please try again.';
                }

                matchResults.classList.remove('d-none');
                matchSummary.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>Analysis Failed</strong>
                        <div class="small mt-1">${errorMessage}</div>
                    </div>
                `;
                matchScore.innerHTML = '';

            } finally {
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-search me-2"></i>Analyze Match';
                analyzeBtn.classList.remove('btn-loading');
            }
        });
    }
}


document.addEventListener('DOMContentLoaded', function () {
    initCandidateAnalysis();
});

