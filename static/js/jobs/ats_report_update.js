document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('calcAtsBtn');
    const panel = document.getElementById('atsPanel');   // the card wrapper

    if (!btn || !panel) return;

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.innerHTML = '<i class="spinner-border spinner-border-sm me-1"></i>Loading…';

        try {
            const ats_endpoint_url = document.getElementById('ats_endpoint_url').value;
            const res = await fetch(ats_endpoint_url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            const json = await res.json();

            // Render the card with the new report
            const html = await renderAtsCard(json);
            panel.innerHTML = html;

        } catch (err) {
            panel.innerHTML = `<div class="alert alert-danger">
                           <i class="bi bi-exclamation-triangle-fill"></i> ${err.message || 'Error loading report.'}
                         </div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="ti-stats-up me-1"></i>Calculate ATS';
        }
    });

    /* ---- helper ---- */
    async function renderAtsCard(report) {
        // Simple Jinja-like template in JS
        if (!report) return '<div class="alert alert-warning">No report returned.</div>';

        let scoreRows = '';
        for (const [key, val] of Object.entries(report.score_breakdown || {})) {
            if (key === 'total') continue;
            scoreRows += `
        <div class="col">
          <div class="fw-bold">${val}</div>
          <small class="text-muted">${key.replaceAll('_', ' ').toTitleCase()}</small>
        </div>`;
        }

        let missingBadges = '';
        (report.top_5_missing || []).forEach(kw => {
            missingBadges += `<span class="badge bg-danger me-1">${kw}</span>`;
        });

        let suggestions = '';
        (report.suggestions || []).forEach(s => {
            suggestions += `
        <div class="border-start border-primary ps-3 mb-3">
          <strong>${(s.field || '').toTitleCase()}</strong><br>
          <small class="text-muted">Impact: +${s.impact.estimated_score_increase} pts</small>
          ${s.current ? `<div class="text-danger text-decoration-line-through">${s.current}</div>` : ''}
          <div class="text-success fw-bold">${s.recommended}</div>
          <em>${s.impact.reasoning}</em>
        </div>`;
        });

        return `
<div class="card shadow-sm mb-4">
  <div class="card-header bg-primary text-white">
    <h5 class="mb-0">
      <i class="bi bi-cpu-fill me-2"></i>AI-Enhanced ATS Report
      <small class="float-end">Score ${report.ai_enhanced_score || '?'}/100</small>
    </h5>
  </div>
  <div class="card-body">
    <h6>Score Breakdown</h6>
    <div class="row mb-3 text-center">${scoreRows}</div>

    <h6>Top Missing Keywords</h6>
    <div class="mb-3">${missingBadges}</div>

    <h6>
      <button class="btn btn-sm btn-outline-primary" type="button"
              data-bs-toggle="collapse" data-bs-target="#suggestions-${report.id}">
        ✨ AI Suggestions
      </button>
    </h6>
    <div class="collapse mt-2" id="suggestions-${report.id}">
      ${suggestions}
    </div>
  </div>
  <div class="card-footer text-muted small">
    Built from ${(report.keyword_corpora || []).join(', ')}
  </div>
</div>`;
    }
});
