


window.pillContainers = [
    {id: 'education-list', jsonId: 'education-json', isDict: true},
    {id: 'required-skills-list', jsonId: 'required-skills-json', isDict: false},
    {id: 'preferred-skills-list', jsonId: 'preferred-skills-json', isDict: false}
];

/* --------------  shared helpers  -------------- */
function addPill(containerId, text) {
    const container = document.getElementById(containerId);
    const exists = [...container.children].some(
        p => p.textContent.trim().toLowerCase() === text.toLowerCase()
    );
    if (exists) return;
    const pill = document.createElement('span');
    pill.className = 'badge bg-secondary me-1 mb-1 fs-6 pill-hover';
    pill.style.cursor = 'pointer';
    pill.textContent = text;
    pill.addEventListener('click', () => {
        pill.remove();
        syncJson(containerId);
    });
    container.appendChild(pill);
}

function syncJson(containerId) {
    const cfg = window.pillContainers.find(c => c.id === containerId);
    const pills = [...document.getElementById(containerId).children]
        .map(p => p.textContent.trim());
    let json;
    if (cfg.isDict) {
        json = {};
        pills.forEach(p => {
            const [k, ...rest] = p.split(':');
            json[k.trim()] = rest.join(':').trim();
        });
    } else {
        json = pills;
    }
    document.getElementById(cfg.jsonId).value = JSON.stringify(json);
}
document.addEventListener('DOMContentLoaded', () => {
    const containers = [
        {id: 'education-list', jsonId: 'education-json', isDict: true},
        {id: 'required-skills-list', jsonId: 'required-skills-json', isDict: false},
        {id: 'preferred-skills-list', jsonId: 'preferred-skills-json', isDict: false}
    ];
    /* ----------  init pills from hidden JSON  ---------- */
    containers.forEach(c => {
        const raw = document.getElementById(c.jsonId).value || (c.isDict ? '{}' : '[]');
        let data;
        try {
            data = JSON.parse(raw);
        } catch {
            data = c.isDict ? {} : [];
        }
        const items = c.isDict ? Object.entries(data).map(([k, v]) => `${k}:${v}`) : data;
        items.forEach(text => addPill(c.id, text));
    });

    /* ----------  wire text inputs  ---------- */
    document.querySelectorAll('.js-list-input').forEach(input => {
        const containerId = input.dataset.listId;
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter' && input.value.trim()) {
                e.preventDefault();          // ← keep only this one
                addPill(containerId, input.value.trim());
                input.value = '';
                syncJson(containerId);
            }
        });
    });
});

// helper – build FormData from current form
function getFormData(extra = {}) {
    const fd = new FormData(document.getElementById('editForm'));
    Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
    return fd;
}
// 1. Calculate ATS
document.getElementById('calcAtsBtn').addEventListener('click', async () => {
    const btn = document.getElementById('calcAtsBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="ti-reload spin"></i> Calculating…';
    const res = await fetch('{{ url_for("jobs_workflow.calculate_ats", job_id=job.job_id) }}', {
        method: 'POST',
        body: getFormData()
    });
    btn.disabled = false;
    btn.innerHTML = '<i class="ti-stats-up me-1"></i>Calculate ATS';
    if (res.ok) {
        document.getElementById('atsPanel').innerHTML = await res.text();
    } else alert('Could not calculate ATS.');
});

// 2. AI Enhance
document.getElementById('aiEnhanceBtn').addEventListener('click', () => $('#aiPromptModal').modal('show'));
document.getElementById('doEnhanceBtn').addEventListener('click', async () => {
    const btn = document.getElementById('doEnhanceBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="ti-reload spin"></i> Enhancing…';
    const res = await fetch('{{ url_for("employer_agents.enhance_job_post", job_id=job.job_id) }}', {
        method: 'POST',
        body: getFormData({user_prompt: document.getElementById('userPrompt').value})
    });
    btn.disabled = false;
    btn.innerHTML = 'Enhancing....';
    $('#aiPromptModal').modal('hide');
    // inside the AI-enhance success handler (after fetch)
    if (res.ok) {
        const data = await res.json();   // EnhanceJobPostOutput

        // 1. simple text fields
        ['title', 'description', 'salary_min', 'salary_max', 'salary_currency',
            'experience_level', 'city', 'province', 'country',
            'application_deadline', 'expires_at', 'application_instructions']
            .forEach(k => {
                const el = document.querySelector(`[name="${k}"]`);
                if (el) el.value = data[k] ?? '';
        });

        // 2. array → pills
        function refreshPills(listId, values) {
            const container = document.getElementById(listId);
            container.innerHTML = '';
            (values || []).forEach(v => addPill(listId, v));
            syncJson(listId);
        }

        refreshPills('required-skills-list', data.required_skills);
        refreshPills('preferred-skills-list', data.preferred_skills);

        // 3. dict → education pills
        const eduEntries = Object.entries(data.education_requirements || {});
        const eduContainer = document.getElementById('education-list');
        eduContainer.innerHTML = '';
        eduEntries.forEach(([k, v]) => addPill('education-list', `${k}:${v}`));
        syncJson('education-list');

        // 4. re-calculate ATS
        document.getElementById('calcAtsBtn').click();
    } else alert('Enhancement failed.');
});

/* Update job status */
async function updateJobStatus(jobId, newStatus) {
    const res = await fetch(`{{ url_for("jobs_workflow.update_status", job_id="__ID__") }}`.replace("__ID__", jobId), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({status: newStatus})
    });
    if (res.ok) location.reload(); else alert("Error updating status");
}

/* Toggle featured flag */
async function toggleFeatured(jobId, featured) {
    const res = await fetch(`{{ url_for("jobs_workflow.toggle_featured", job_id="__ID__") }}`.replace("__ID__", jobId), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({featured})
    });
    if (res.ok) location.reload(); else alert("Error toggling featured");
}




/* ==========  Job Post Insights Card ========== */
(() => {
    // Endpoint URL for fetching insights - resolves on the DOM
    const endpoint = document.getElementById('endpointurl').value;
    /* ---- DOM references ---- */
    const card = document.getElementById('jobPostInsightsCard');
    const btn = document.getElementById('refreshInsightsBtn');
    const spinner = document.getElementById('insightsLoadingSpinner');
    const content = document.getElementById('insightsContent');
    const error = document.getElementById('insightsErrorAlert');
    console.log("endpoint url : ", endpoint);
    /* ---- helpers ---- */
    const setLoading = (on) => {
        spinner.style.display = on ? '' : 'none';
        content.style.display = on ? 'none' : '';
        error.style.display = 'none';

        btn.disabled = on;
        btn.querySelector('i')?.classList.toggle('fa-spin', on);
    };

    /* ---- render ---- */
    const loadInsights = async () => {
setLoading(true);
try {
    const res = await fetch(endpoint, { method: 'POST', credentials: 'same-origin' });
    if (!res.ok) throw new Error('Network response was not ok');
    const data = await res.json();
    console.log('Job) Post Insights:', data);
    /* clarity score */
    const score = Math.round(data.clarity_score * 10);
    const bar = document.getElementById('clarityProgressBar');
    bar.style.width = `${score}%`;
    bar.setAttribute('aria-valuenow', score);
    bar.textContent = `${score} %`;
    bar.classList.toggle('bg-warning', score < 60);
    bar.classList.toggle('bg-success', score >= 60);

    /* salary benchmark */
    document.getElementById('salaryBenchmarkBadge').textContent =
        data.salary_benchmark || '—';

    /* missing information */
    const mList = document.getElementById('missingInfoList');
    mList.innerHTML = '';
    if (data.missing_information?.length) {
        data.missing_information.forEach(item => {
            mList.insertAdjacentHTML('beforeend',
                `<li class="list-group-item">
            <i class="bi bi-dash-circle"></i> ${item}
            </li>`);
        });
    } else {
        mList.insertAdjacentHTML('beforeend',
            '<li class="list-group-item text-muted">None</li>');
    }

    /* suggestions */
    const sList = document.getElementById('suggestionsList');
    sList.innerHTML = '';
    if (data.suggestions?.length) {
        data.suggestions.forEach(item => {
            sList.insertAdjacentHTML('beforeend',
                `<li class="list-group-item">
            <i class="bi bi-check-circle"></i> ${item}
            </li>`);
        });
        renderAiSuggestions(data?.suggestions);
    } else {
        sList.insertAdjacentHTML('beforeend',
            '<li class="list-group-item text-muted">None</li>');
    }

    content.style.display = '';
} catch (err) {
    console.error(err);
    error.style.display = '';
} finally {
    setLoading(false);

}
    };
    /* ---- events ---- */

    btn?.addEventListener('click', loadInsights);
    document.addEventListener('DOMContentLoaded', loadInsights);
})();

/* helper: render AI-enhance suggestions */

// Character counter
document.getElementById('userPrompt').addEventListener('input', function () {
    const count = this.value.length;
    document.getElementById('charCount').textContent = count;
});

// Updated helper function with improved styling
function renderAiSuggestions(suggestions = []) {
    const container = document.getElementById('aiSuggestionsContainer');
    const list = document.getElementById('aiSuggestionsList');
    list.innerHTML = '';

    if (suggestions?.length) {
        suggestions.forEach(text => {
            const badge = document.createElement('span');
            badge.className = 'suggestion-badge';
            badge.textContent = text;
            badge.title = text; // Show full text on hover
            badge.onclick = () => {
                const prompt = document.getElementById('userPrompt');
                if (!prompt.value.includes(text)) {
                    prompt.value += (prompt.value ? ' ' : '') + text;
                    // Trigger character count update
                    prompt.dispatchEvent(new Event('input'));
                }
            };
            list.appendChild(badge);
        });
        container.style.display = 'block';
    } else {
        container.style.display = 'none';
    }
}

// Demo functionality
document.addEventListener('DOMContentLoaded', function () {
    // Show modal for demo
    document.body.addEventListener('click', function (e) {
        if (e.target.textContent === 'Show Demo') {
            const modal = new bootstrap.Modal(document.getElementById('aiPromptModal'));
            modal.show();

            // Demo suggestions
            setTimeout(() => {
                renderAiSuggestions([
                    'Make it more conversational',
                    'Add technical depth',
                    'Include examples',
                    'Simplify language',
                    'Add call-to-action',
                    'Focus on benefits',
                    'Include statistics',
                    'Make it shorter'
                ]);
            }, 500);
        }
    });
});


