// ═══════════════════════════════════════════════════════════════════
//  AI Governance MCP Server — Web UI Application Logic
//  Full 9-phase audit workflow for the Data Protection Officer
//  ═══════════════════════════════════════════════════════════════════

const API_BASE = localStorage.getItem('ai_gov_api_base') || 'http://localhost:8000';

// ─── State ──────────────────────────────────────────────────────────
const state = {
  currentView: 'dashboard',
  modelId: '',
  apiBase: API_BASE,
  connectionOk: false,
  phases: {
    1: { name: 'Risk Classification', icon: '⚡', status: 'pending', data: null, error: null },
    2: { name: 'Supply Chain Audit', icon: '🔗', status: 'pending', data: null, error: null },
    3: { name: 'Human Oversight', icon: '👁️', status: 'pending', data: null, error: null },
    4: { name: 'Bias Assessment', icon: '⚖️', status: 'pending', data: null, error: null },
    5: { name: 'DPIA Generation', icon: '🛡️', status: 'pending', data: null, error: null },
    6: { name: 'Adversarial Tests', icon: '🧪', status: 'pending', data: null, error: null },
    7: { name: 'Weighted Scoring', icon: '📊', status: 'pending', data: null, error: null },
    8: { name: 'Audit Certificate', icon: '📜', status: 'pending', data: null, error: null },
    9: { name: 'Drift Monitoring', icon: '📈', status: 'pending', data: null, error: null },
  },
};

const PHASE_CONFIG = {
  1: { endpoint: '/api/risk/classify', title: 'Risk Classification', icon: '⚡',
       reg: 'EU AI Act Art. 6, Annex I-III | NIST AI RMF MAP 1.1 | ISO 42001 Clause 6.1',
       desc: 'Classify the AI system into a risk tier (Prohibited, High, Limited, Minimal) based on its intended purpose, sector, and capabilities.' },
  2: { endpoint: '/api/supply-chain/audit', title: 'Supply Chain Audit', icon: '🔗',
       reg: 'EU AI Act Art. 10, 12 | NIST AI RMF GOVERN 1.2 | ISO 42001 Clause 7.4.3',
       desc: 'Audit data lineage, IP clearance, and third-party dependencies through the provenance graph.' },
  3: { endpoint: '/api/human-oversight/verify', title: 'Human Oversight', icon: '👁️',
       reg: 'EU AI Act Art. 14 | NIST AI RMF GOVERN 3.2 | ISO 42001 Clause 8.2 | GDPR Art. 22',
       desc: 'Verify human-in-the-loop (HITL) and kill-switch controls. A BLOCKER FAIL halts certification.' },
  4: { endpoint: '/api/bias/assess', title: 'Bias Assessment', icon: '⚖️',
       reg: 'EU AI Act Art. 10 | NIST AI RMF MEASURE 2.2 | ISO 42001 Clause 8.1.2 | GDPR Art. 9, 35',
       desc: 'Multidimensional fairness scan across protected attributes using Fairlearn & AIF360.' },
  5: { endpoint: '/api/dpia/generate', title: 'DPIA Generation', icon: '🛡️',
       reg: 'GDPR Art. 5, 9, 22, 35, 44-49 | ISO 42001 Clause 6.2',
       desc: 'Generate a Data Protection Impact Assessment with cross-border transfer analysis.' },
  6: { endpoint: '/api/adversarial/run', title: 'Adversarial Tests', icon: '🧪',
       reg: 'EU AI Act Art. 15 | NIST AI RMF MEASURE 1.3 | ISO 42001 Clause 8.1.3',
       desc: 'Test robustness against prompt injection, jailbreak, OOD, and model inversion attacks.' },
  7: { endpoint: '/api/scoring/weighted', title: 'Weighted Scoring', icon: '📊',
       reg: 'NIST AI RMF MEASURE 4.1 | ISO 42001 Clause 9.1',
       desc: 'Aggregate all phases into a weighted score (0-100). Halts on BLOCKER FAIL.' },
  8: { endpoint: '/api/certificate/generate', title: 'Audit Certificate', icon: '📜',
       reg: 'W3C VC Data Model 1.1 | ISO 42001 Clause 7.5',
       desc: 'Issue a cryptographically signed W3C Verifiable Credential for the completed audit.' },
  9: { endpoint: '/api/drift/monitor', title: 'Drift Monitoring', icon: '📈',
       reg: 'EU AI Act Art. 15 | NIST AI RMF MEASURE 3.3 | ISO 42001 Clause 9.1',
       desc: 'Continuous post-deployment drift monitoring with Evidently AI.' },
};

// ─── API Client ─────────────────────────────────────────────────────

async function apiCall(endpoint, body, method = 'POST') {
  const url = `${state.apiBase}${endpoint}`;
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try { const j = JSON.parse(text); detail = j.detail || j.message || text; } catch {}
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return res.json();
}

async function checkHealth() {
  try {
    const data = await apiCall('/health', null, 'GET');
    state.connectionOk = data.status === 'ok';
    return data;
  } catch {
    state.connectionOk = false;
    return null;
  }
}

function setModelId(id) {
  state.modelId = id;
  localStorage.setItem('ai_gov_model_id', id);
}

// ─── Toast System ────────────────────────────────────────────────────

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 4000);
}

// ─── Navigation ──────────────────────────────────────────────────────

function navigate(view, data) {
  state.currentView = view;
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => item.classList.remove('active'));
  const target = document.querySelector(`.nav-item[data-view="${view}"]`);
  if (target) target.classList.add('active');

  document.getElementById('viewDashboard').classList.add('hidden');
  document.getElementById('viewPhase').classList.add('hidden');
  document.getElementById('viewReport').classList.add('hidden');

  if (view === 'dashboard') {
    document.getElementById('viewDashboard').classList.remove('hidden');
    document.getElementById('pageTitle').textContent = 'Dashboard';
    renderDashboard();
  } else if (view.startsWith('phase-')) {
    const phaseNum = parseInt(view.split('-')[1]);
    document.getElementById('viewPhase').classList.remove('hidden');
    renderPhaseForm(phaseNum, data);
  } else if (view === 'report') {
    document.getElementById('viewReport').classList.remove('hidden');
    document.getElementById('pageTitle').textContent = 'Audit Report';
    renderReport();
  }
}

// ─── Render Dashboard ────────────────────────────────────────────────

function renderDashboard() {
  const statusCounts = { pending: 0, running: 0, passed: 0, failed: 0, blocker: 0 };
  Object.values(state.phases).forEach(p => {
    statusCounts[p.status] = (statusCounts[p.status] || 0) + 1;
  });
  const completed = statusCounts.passed + statusCounts.failed + statusCounts.blocker;
  const total = 9;
  const pct = Math.round((completed / total) * 100);

  document.getElementById('statCompleted').textContent = `${completed}/${total}`;
  document.getElementById('statPassed').textContent = statusCounts.passed;
  document.getElementById('statFailed').textContent = statusCounts.failed + statusCounts.blocker;
  document.getElementById('statProgress').textContent = `${pct}%`;

  const progressFill = document.getElementById('dashboardProgressFill');
  progressFill.style.width = `${pct}%`;
  progressFill.className = 'progress-bar-fill' + (pct === 100 ? ' complete' : statusCounts.blocker > 0 ? ' failed' : '');

  const phaseGrid = document.getElementById('phaseGrid');
  phaseGrid.innerHTML = '';
  for (let i = 1; i <= 9; i++) {
    const p = state.phases[i];
    const cfg = PHASE_CONFIG[i];
    const card = document.createElement('div');
    card.className = 'phase-card';
    const statusLabel = p.status === 'blocker' ? 'blocker' : p.status;
    card.innerHTML = `
      <div class="phase-top">
        <div class="phase-badge">${i}</div>
        <div class="phase-name">
          ${cfg.title}
          <div class="phase-reg">${cfg.reg}</div>
        </div>
      </div>
      <div class="phase-desc">${cfg.desc}</div>
      <div class="phase-footer">
        <span class="phase-status-label ${statusLabel}">${p.status.toUpperCase()}</span>
        <button class="btn btn-sm btn-outline" onclick="navigate('phase-${i}')">${p.status === 'pending' ? 'Start' : 'Review'}</button>
      </div>
    `;
    phaseGrid.appendChild(card);
  }

  const allPassed = Object.values(state.phases).every(p => p.status === 'passed');
  const anyFailed = Object.values(state.phases).some(p => p.status === 'failed' || p.status === 'blocker');
  document.getElementById('reportBtnWrap').innerHTML = completed > 0
    ? `<button class="btn ${allPassed ? 'btn-success' : anyFailed ? 'btn-danger' : 'btn-primary'} btn-lg" onclick="navigate('report')">
        ${allPassed ? '✅' : anyFailed ? '⚠️' : '📋'} View Consolidated Report
       </button>`
    : '';
}

// ─── Render Phase Form ───────────────────────────────────────────────

const forms = {
  1: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[1].desc}</p>
    <div class="form-row">
      <div class="form-group">
        <label>Model ID <span class="required">*</span></label>
        <input class="form-control" id="f1_modelId" value="${state.modelId || 'model-llm-v1'}" placeholder="e.g. model-llm-v2">
      </div>
      <div class="form-group">
        <label>Model Type <span class="required">*</span></label>
        <select class="form-control" id="f1_modelType">
          <option value="general_purpose_ai">General Purpose AI</option>
          <option value="biometric">Biometric</option>
          <option value="critical_infrastructure">Critical Infrastructure</option>
          <option value="educational">Educational</option>
          <option value="employment" selected>Employment</option>
          <option value="credit">Credit</option>
          <option value="law_enforcement">Law Enforcement</option>
          <option value="other">Other</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Sector <span class="required">*</span></label>
        <select class="form-control" id="f1_sector">
          <option value="healthcare">Healthcare</option>
          <option value="finance">Finance</option>
          <option value="criminal_justice">Criminal Justice</option>
          <option value="employment" selected>Employment</option>
          <option value="education">Education</option>
          <option value="critical_infrastructure">Critical Infrastructure</option>
          <option value="other">Other</option>
        </select>
      </div>
      <div class="form-group">
        <label>Uses Profiling?</label>
        <select class="form-control" id="f1_usesProfiling">
          <option value="true">Yes</option>
          <option value="false" selected>No</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>Deployer (optional)</label>
      <input class="form-control" id="f1_deployer" placeholder="e.g. Acme Corp">
    </div>
  `,
  2: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[2].desc}</p>
    <div class="form-group">
      <label>Model ID <span class="required">*</span></label>
      <input class="form-control" id="f2_modelId" value="${state.modelId || 'model-llm-v1'}">
    </div>
    <div class="form-group">
      <label class="flex items-center gap-2">
        <input type="checkbox" id="f2_deepScan"> Deep Scan (recursive transitive dependencies)
      </label>
    </div>
  `,
  3: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[3].desc}</p>
    <div class="form-group">
      <label>Model ID <span class="required">*</span></label>
      <input class="form-control" id="f3_modelId" value="${state.modelId || 'model-llm-v1'}">
    </div>
    <div class="form-row-3">
      <div class="form-group">
        <label>Human-in-the-Loop? <span class="required">*</span></label>
        <select class="form-control" id="f3_hasHumanInTheLoop">
          <option value="true" selected>Yes</option>
          <option value="false">No</option>
        </select>
      </div>
      <div class="form-group">
        <label>Kill-Switch Present? <span class="required">*</span></label>
        <select class="form-control" id="f3_hasKillSwitch">
          <option value="true">Yes</option>
          <option value="false" selected>No</option>
        </select>
      </div>
      <div class="form-group">
        <label>Deployment Context <span class="required">*</span></label>
        <select class="form-control" id="f3_deploymentContext">
          <option value="real_time" selected>Real-time</option>
          <option value="batch">Batch</option>
          <option value="assistive">Assistive</option>
          <option value="autonomous">Autonomous</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>Oversight Process Description</label>
      <textarea class="form-control" id="f3_oversightProcess" placeholder="Describe the human oversight process...">Manual review by qualified operator before final decision execution.</textarea>
    </div>
  `,
  4: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[4].desc}</p>
    <div class="form-group">
      <label>Model ID <span class="required">*</span></label>
      <input class="form-control" id="f4_modelId" value="${state.modelId || 'model-llm-v1'}">
    </div>
    <div class="form-group">
      <label>Sensitive Features (comma-separated) <span class="required">*</span></label>
      <input class="form-control" id="f4_sensitiveFeatures" value="race,gender,age" placeholder="e.g. race,gender,age,disability">
      <div class="form-hint">Protected attributes to test for bias</div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Fairness Threshold</label>
        <input class="form-control" id="f4_fairnessThreshold" value="0.8" type="number" step="0.05" min="0" max="1">
        <div class="form-hint">80% rule (0.8) per US EEOC guidelines</div>
      </div>
      <div class="form-group">
        <label>Sample Dataset Size</label>
        <input class="form-control" id="f4_sampleSize" value="100" type="number" min="1">
      </div>
    </div>
  `,
  5: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[5].desc}</p>
    <div class="form-group">
      <label>Model ID <span class="required">*</span></label>
      <input class="form-control" id="f5_modelId" value="${state.modelId || 'model-llm-v1'}">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Data Controller <span class="required">*</span></label>
        <input class="form-control" id="f5_dataController" value="Acme Corp">
      </div>
      <div class="form-group">
        <label>DPO Name <span class="required">*</span></label>
        <input class="form-control" id="f5_dpoName" value="Jane Doe">
      </div>
    </div>
    <div class="form-group">
      <label>Processing Purpose <span class="required">*</span></label>
      <input class="form-control" id="f5_processingPurpose" value="Automated candidate screening and ranking for employment">
    </div>
    <div class="form-group">
      <label>Data Categories (comma-separated) <span class="required">*</span></label>
      <input class="form-control" id="f5_dataCategories" value="biometric,employment_history,education">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Cross-Border Transfer?</label>
        <select class="form-control" id="f5_crossBorderTransfer">
          <option value="false" selected>No</option>
          <option value="true">Yes</option>
        </select>
      </div>
      <div class="form-group" id="f5_thirdCountriesWrap" style="display:none">
        <label>Third Countries</label>
        <input class="form-control" id="f5_thirdCountries" placeholder="e.g. United States, Japan">
      </div>
    </div>
  `,
  6: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[6].desc}</p>
    <div class="form-group">
      <label>Model ID <span class="required">*</span></label>
      <input class="form-control" id="f6_modelId" value="${state.modelId || 'model-llm-v1'}">
    </div>
    <div class="form-group">
      <label>Test Suites <span class="required">*</span></label>
      <div class="flex flex-wrap gap-2">
        <label class="flex items-center gap-1"><input type="checkbox" class="test-suite" value="prompt_injection" checked> Prompt Injection</label>
        <label class="flex items-center gap-1"><input type="checkbox" class="test-suite" value="jailbreak" checked> Jailbreak</label>
        <label class="flex items-center gap-1"><input type="checkbox" class="test-suite" value="ood_detection" checked> OOD Detection</label>
        <label class="flex items-center gap-1"><input type="checkbox" class="test-suite" value="model_inversion"> Model Inversion</label>
        <label class="flex items-center gap-1"><input type="checkbox" class="test-suite" value="membership_inference"> Membership Inference</label>
      </div>
    </div>
    <div class="form-group">
      <label>Severity Threshold</label>
      <select class="form-control" id="f6_severityThreshold">
        <option value="low">Low</option>
        <option value="medium" selected>Medium</option>
        <option value="high">High</option>
      </select>
    </div>
  `,
  7: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[7].desc}</p>
    <p class="mb-4" style="color:var(--text-secondary);font-size:13px;">
      This phase aggregates results from Phases 1-6. Complete those phases first, then click "Score Audit" to compute the weighted score.
    </p>
    <div class="form-group">
      <label>Model ID</label>
      <input class="form-control" id="f7_modelId" value="${state.modelId || 'model-llm-v1'}" readonly>
    </div>
  `,
  8: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[8].desc}</p>
    <p class="mb-4" style="color:var(--text-secondary);font-size:13px;">
      Issue a W3C Verifiable Credential for the completed audit. Requires Phases 1-7 to be completed.
    </p>
    <div class="form-group">
      <label>Model ID</label>
      <input class="form-control" id="f8_modelId" value="${state.modelId || 'model-llm-v1'}" readonly>
    </div>
    <div class="form-group">
      <label>Issuer Name <span class="required">*</span></label>
      <input class="form-control" id="f8_issuerName" value="AI Governance Auditor">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Tier</label>
        <input class="form-control" id="f8_tier" readonly>
      </div>
      <div class="form-group">
        <label>Validity (days)</label>
        <input class="form-control" id="f8_validDays" value="365" type="number">
      </div>
    </div>
  `,
  9: (pNum, data) => `
    <p class="card-subtitle mb-6">${PHASE_CONFIG[9].desc}</p>
    <div class="form-group">
      <label>Model ID <span class="required">*</span></label>
      <input class="form-control" id="f9_modelId" value="${state.modelId || 'model-llm-v1'}">
    </div>
    <div class="form-group">
      <label>Features to Monitor (comma-separated) <span class="required">*</span></label>
      <input class="form-control" id="f9_features" value="accuracy,f1_score,latency,confidence">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Drift Threshold</label>
        <input class="form-control" id="f9_driftThreshold" value="0.1" type="number" step="0.05" min="0" max="1">
      </div>
      <div class="form-group">
        <label>Sample Size</label>
        <input class="form-control" id="f9_sampleSize" value="50" type="number" min="1">
      </div>
    </div>
  `,
};

function renderPhaseForm(phaseNum, data) {
  const p = state.phases[phaseNum];
  const cfg = PHASE_CONFIG[phaseNum];
  document.getElementById('pageTitle').textContent = `Phase ${phaseNum}: ${cfg.title}`;

  const card = document.getElementById('phaseFormCard');
  card.innerHTML = `
    <div class="card-header">
      <div>
        <div class="card-title">${cfg.icon} ${cfg.title}</div>
        <div class="card-subtitle">${cfg.reg}</div>
      </div>
      <div class="card-actions">
        <button class="btn btn-outline btn-sm" onclick="navigate('dashboard')">← Dashboard</button>
      </div>
    </div>
    <div id="phaseFormBody">
      ${forms[phaseNum](phaseNum, data)}
      <div class="flex justify-between items-center mt-6">
        <span style="font-size:13px;color:var(--text-muted)">Status: <strong>${p.status.toUpperCase()}</strong></span>
        <button class="btn btn-primary btn-lg" onclick="executePhase(${phaseNum})" id="executeBtn">
          ${p.status === 'running' ? '<span class="loading-spinner"></span> Running...' : p.status === 'passed' ? '🔄 Re-run Phase' : '▶ Execute Phase'}
        </button>
      </div>
    </div>
    <div id="phaseResultArea" class="result-container ${p.data ? '' : 'hidden'}">
      ${p.data ? renderPhaseResult(phaseNum, p.data) : ''}
    </div>
  `;

  // Wire up cross-border transfer toggle for DPIA
  const cbTransfer = document.getElementById('f5_crossBorderTransfer');
  if (cbTransfer) {
    cbTransfer.addEventListener('change', () => {
      document.getElementById('f5_thirdCountriesWrap').style.display = cbTransfer.value === 'true' ? 'block' : 'none';
    });
  }
}

function renderPhaseResult(phaseNum, data) {
  const passed = data.compliant || data.certificationEligible || data.overallDriftStatus === 'stable' || false;
  const isBlocker = data.blocker === true || (data.blockerFailures && data.blockerFailures.length > 0);
  const statusClass = isBlocker ? 'failed' : passed ? 'passed' : 'warning';
  const icon = isBlocker ? '❌' : passed ? '✅' : '⚠️';
  const statusText = isBlocker ? 'BLOCKER FAIL' : passed ? 'PASSED' : 'WARNING';

  let metricsHtml = '';
  if (data.metrics) {
    metricsHtml = '<div class="result-metrics">' +
      data.metrics.map(m => `
        <div class="metric-card">
          <div class="metric-value ${m.passed || !m.drifted ? 'text-success' : 'text-danger'}">${typeof m.score === 'number' ? m.score.toFixed(3) : m.score}</div>
          <div class="metric-label">${m.feature || m.protectedAttribute || m.metric || m.testName}</div>
          <div class="metric-status ${m.passed || !m.drifted ? 'text-success' : 'text-danger'}">${m.passed || !m.drifted ? '✓ PASS' : '✗ FAIL'}</div>
        </div>
      `).join('') + '</div>';
  } else if (data.categoryScores) {
    metricsHtml = '<div class="result-metrics">' +
      Object.entries(data.categoryScores).map(([k, v]) => `
        <div class="metric-card">
          <div class="metric-value">${v}</div>
          <div class="metric-label">${k.replace(/_/g, ' ')}</div>
        </div>
      `).join('') + '</div>';
  } else if (data.sections) {
    metricsHtml = '<div class="result-metrics">' +
      data.sections.slice(0, 4).map(s => `
        <div class="metric-card">
          <div class="metric-value ${s.risk === 'high' || s.risk === 'critical' ? 'text-danger' : s.risk === 'medium' ? 'text-warning' : 'text-success'}">${s.risk.toUpperCase()}</div>
          <div class="metric-label" style="font-size:10px">${s.section.substring(0, 30)}</div>
        </div>
      `).join('') + '</div>';
  } else if (data.overallScore !== undefined) {
    metricsHtml = `<div class="result-metrics">
      <div class="metric-card"><div class="metric-value">${data.overallScore}</div><div class="metric-label">OVERALL SCORE</div></div>
      <div class="metric-card"><div class="metric-value ${data.certificationEligible ? 'text-success' : 'text-danger'}">${data.certificationEligible ? 'YES' : 'NO'}</div><div class="metric-label">CERTIFICATION ELIGIBLE</div></div>
    </div>`;
  } else if (data.overallDriftStatus) {
    const st = data.overallDriftStatus;
    metricsHtml = `<div class="result-metrics">
      <div class="metric-card"><div class="metric-value ${st === 'stable' ? 'text-success' : st === 'warning' ? 'text-warning' : 'text-danger'}">${st.toUpperCase()}</div><div class="metric-label">DRIFT STATUS</div></div>
    </div>`;
  }

  let summaryHtml = '';
  if (data.summary) summaryHtml = `<p style="margin-bottom:12px;font-size:13px">${data.summary}</p>`;
  if (data.rationale) summaryHtml = `<p style="margin-bottom:12px;font-size:13px">${data.rationale}</p>`;
  if (data.remediation) summaryHtml += `<p style="color:var(--warning);font-size:13px">🛠 Remediation: ${data.remediation}</p>`;

  return `
    <div class="result-header ${statusClass}">
      <span class="result-icon">${icon}</span>
      <div class="result-text">
        <h3>${statusText}</h3>
        <p>Phase ${phaseNum}: ${PHASE_CONFIG[phaseNum].title}</p>
      </div>
    </div>
    ${metricsHtml}
    ${summaryHtml}
    <div class="result-json">${JSON.stringify(data, null, 2)}</div>
  `;
}

// ─── Execute Phase ───────────────────────────────────────────────────

async function executePhase(phaseNum) {
  const p = state.phases[phaseNum];
  const btn = document.getElementById('executeBtn');
  if (!btn) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="loading-spinner"></span> Running...';
  p.status = 'running';
  updateNavStates();

  try {
    let body;
    let endpoint;
    let result;

    switch (phaseNum) {
      case 1: {
        const modelId = document.getElementById('f1_modelId').value.trim();
        body = {
          modelId,
          modelType: document.getElementById('f1_modelType').value,
          sector: document.getElementById('f1_sector').value,
          usesProfiling: document.getElementById('f1_usesProfiling').value === 'true',
          deployer: document.getElementById('f1_deployer').value.trim() || undefined,
        };
        setModelId(modelId);
        result = await apiCall('/api/risk/classify', body);
        break;
      }
      case 2: {
        const modelId = document.getElementById('f2_modelId').value.trim();
        body = { modelId, deepScan: document.getElementById('f2_deepScan').checked };
        setModelId(modelId);
        result = await apiCall('/api/supply-chain/audit', body);
        break;
      }
      case 3: {
        const modelId = document.getElementById('f3_modelId').value.trim();
        body = {
          modelId,
          hasHumanInTheLoop: document.getElementById('f3_hasHumanInTheLoop').value === 'true',
          hasKillSwitch: document.getElementById('f3_hasKillSwitch').value === 'true',
          deploymentContext: document.getElementById('f3_deploymentContext').value,
          oversightProcess: document.getElementById('f3_oversightProcess').value.trim() || undefined,
        };
        setModelId(modelId);
        result = await apiCall('/api/human-oversight/verify', body);
        break;
      }
      case 4: {
        const modelId = document.getElementById('f4_modelId').value.trim();
        const sensitiveFeatures = document.getElementById('f4_sensitiveFeatures').value.split(',').map(s => s.trim()).filter(Boolean);
        const sampleSize = parseInt(document.getElementById('f4_sampleSize').value) || 100;
        const datasetSample = Array.from({ length: sampleSize }, (_, i) => ({
          feature_1: Math.random(),
          feature_2: Math.random(),
          label: Math.random() > 0.5 ? 1 : 0,
          race: ['white', 'black', 'asian', 'hispanic'][Math.floor(Math.random() * 4)],
          gender: Math.random() > 0.5 ? 'male' : 'female',
          age: 20 + Math.floor(Math.random() * 50),
        }));
        body = {
          modelId,
          datasetSample,
          sensitiveFeatures,
          fairnessThreshold: parseFloat(document.getElementById('f4_fairnessThreshold').value) || 0.8,
        };
        setModelId(modelId);
        result = await apiCall('/api/bias/assess', body);
        break;
      }
      case 5: {
        const modelId = document.getElementById('f5_modelId').value.trim();
        body = {
          modelId,
          dataController: document.getElementById('f5_dataController').value.trim(),
          dpoName: document.getElementById('f5_dpoName').value.trim(),
          processingPurpose: document.getElementById('f5_processingPurpose').value.trim(),
          dataCategories: document.getElementById('f5_dataCategories').value.split(',').map(s => s.trim()).filter(Boolean),
          crossBorderTransfer: document.getElementById('f5_crossBorderTransfer').value === 'true',
          thirdCountries: document.getElementById('f5_thirdCountries')?.value.split(',').map(s => s.trim()).filter(Boolean) || [],
        };
        setModelId(modelId);
        result = await apiCall('/api/dpia/generate', body);
        break;
      }
      case 6: {
        const modelId = document.getElementById('f6_modelId').value.trim();
        const suites = [...document.querySelectorAll('.test-suite:checked')].map(el => el.value);
        if (suites.length === 0) throw new Error('Select at least one test suite');
        body = {
          modelId,
          testSuites: suites,
          severityThreshold: document.getElementById('f6_severityThreshold').value,
        };
        setModelId(modelId);
        result = await apiCall('/api/adversarial/run', body);
        break;
      }
      case 7: {
        const modelId = state.modelId || 'model-llm-v1';
        const p1 = state.phases[1].data || { tier: 'limited', compliant: true };
        const p2 = state.phases[2].data || { ipClearance: true, compliant: true };
        const p3 = state.phases[3].data || { blocker: false, compliant: true };
        const p4 = state.phases[4].data || { overallBiasRisk: 'low', compliant: true };
        const p5 = state.phases[5].data || { compliant: true };
        const p6 = state.phases[6].data || { overallRisk: 'low', compliant: true };
        body = {
          modelId,
          riskTier: { tier: p1.tier, compliant: p1.compliant },
          supplyChain: { ipClearance: p2.ipClearance, supplyChainRisk: p2.supplyChainRisk, compliant: p2.compliant },
          oversight: { blocker: p3.blocker, compliant: p3.compliant },
          bias: { overallBiasRisk: p4.overallBiasRisk, compliant: p4.compliant },
          dpia: { compliant: p5.compliant, crossBorderTransfer: p5.crossBorderTransfer },
          adversarial: { overallRisk: p6.overallRisk, compliant: p6.compliant },
        };
        result = await apiCall('/api/scoring/weighted', body);
        break;
      }
      case 8: {
        const scoreData = state.phases[7].data;
        if (!scoreData) throw new Error('Complete Phase 7 (Weighted Scoring) first');
        const tier = state.phases[1].data?.tier || 'limited';
        body = {
          modelId: state.modelId || 'model-llm-v1',
          weightedScore: scoreData.overallScore,
          tier,
          compliant: scoreData.certificationEligible,
          issuerName: document.getElementById('f8_issuerName').value.trim(),
          validDays: parseInt(document.getElementById('f8_validDays').value) || 365,
        };
        const certData = await apiCall('/api/certificate/generate', body);
        result = { ...certData, issuerName: body.issuerName, tier: body.tier, weightedScore: body.weightedScore };
        break;
      }
      case 9: {
        const modelId = document.getElementById('f9_modelId').value.trim();
        const features = document.getElementById('f9_features').value.split(',').map(s => s.trim()).filter(Boolean);
        const sampleSize = parseInt(document.getElementById('f9_sampleSize').value) || 50;
        const refData = Array.from({ length: sampleSize }, (_, i) => ({
          accuracy: 0.85 + Math.random() * 0.1,
          f1_score: 0.82 + Math.random() * 0.12,
          latency: 100 + Math.random() * 50,
          confidence: 0.75 + Math.random() * 0.2,
        }));
        const prodData = Array.from({ length: sampleSize }, (_, i) => ({
          accuracy: 0.70 + Math.random() * 0.25,
          f1_score: 0.65 + Math.random() * 0.3,
          latency: 150 + Math.random() * 100,
          confidence: 0.60 + Math.random() * 0.35,
        }));
        body = {
          modelId,
          referenceData: refData,
          productionData: prodData,
          driftThreshold: parseFloat(document.getElementById('f9_driftThreshold').value) || 0.1,
          features,
        };
        setModelId(modelId);
        result = await apiCall('/api/drift/monitor', body);
        break;
      }
      default:
        throw new Error(`Unknown phase: ${phaseNum}`);
    }

    p.data = result;
    const isBlocker = result.blocker === true || (result.blockerFailures && result.blockerFailures.length > 0);
    const isCompliant = result.compliant || result.certificationEligible || result.overallDriftStatus === 'stable' || false;
    p.status = isBlocker ? 'blocker' : isCompliant ? 'passed' : 'failed';
    p.error = null;

    showToast(`Phase ${phaseNum}: ${PHASE_CONFIG[phaseNum].title} ${p.status === 'passed' ? 'passed' : p.status === 'blocker' ? 'BLOCKED' : 'completed with warnings'}`, p.status === 'passed' ? 'success' : 'warning');
  } catch (err) {
    p.status = 'failed';
    p.error = err.message;
    showToast(`Phase ${phaseNum} failed: ${err.message}`, 'error');
  }

  updateNavStates();
  navigate(`phase-${phaseNum}`);
}

// ─── Update Navigation States ────────────────────────────────────────

function updateNavStates() {
  for (let i = 1; i <= 9; i++) {
    const p = state.phases[i];
    const el = document.querySelector(`.nav-item[data-view="phase-${i}"]`);
    if (!el) continue;
    el.classList.remove('completed', 'active');
    if (p.status === 'passed') el.classList.add('completed');
    const dot = el.querySelector('.nav-status');
    if (dot) {
      dot.className = 'nav-status';
      dot.classList.add(p.status === 'blocker' ? 'failed' : p.status);
    }
  }
}

// ─── Report ──────────────────────────────────────────────────────────

function renderReport() {
  const phases = state.phases;
  const allData = {};
  let anyData = false;
  for (let i = 1; i <= 9; i++) {
    if (phases[i].data) { allData[i] = phases[i].data; anyData = true; }
  }

  if (!anyData) {
    document.getElementById('reportContent').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <h3>No Audit Data Yet</h3>
        <p>Complete at least one audit phase to generate a report.</p>
        <button class="btn btn-primary mt-4" onclick="navigate('dashboard')">← Go to Dashboard</button>
      </div>
    `;
    return;
  }

  // Compute aggregate stats
  const scoreData = phases[7].data;
  const riskData = phases[1].data;
  const certData = phases[8].data;
  const driftData = phases[9].data;

  const allCompliant = Object.values(phases).every(p => p.data ? (p.data.compliant || p.data.certificationEligible || p.data.overallDriftStatus === 'stable' || false) : true);
  const anyBlocker = Object.values(phases).some(p => p.data?.blocker === true || (p.data?.blockerFailures && p.data.blockerFailures.length > 0));
  const overallScore = scoreData?.overallScore ?? null;
  const overallTier = riskData?.tier ?? 'N/A';

  const blockerFailures = [];
  if (scoreData?.blockerFailures) blockerFailures.push(...scoreData.blockerFailures);
  Object.values(phases).forEach(p => {
    if (p.data?.blocker === true) blockerFailures.push('Human oversight BLOCKER FAIL - insufficient controls');
    if (p.data?.remediation && p.data?.blocker) blockerFailures.push(p.data.remediation);
  });
  const uniqueBlockers = [...new Set(blockerFailures)];

  // EU AI Act non-compliance consequences
  const nonComplianceSeverity = !allCompliant || anyBlocker || (overallScore !== null && overallScore < 60);

  let html = `<div class="report-section">
    <div class="report-section-title">📊 Executive Summary</div>
    <div class="report-summary">
      <div class="report-summary-item">
        <div class="value ${overallScore !== null && overallScore >= 60 ? 'text-success' : 'text-danger'}">${overallScore !== null ? overallScore : 'N/A'}</div>
        <div class="label">Overall Audit Score</div>
      </div>
      <div class="report-summary-item">
        <div class="value ${overallTier === 'prohibited' ? 'text-danger' : overallTier === 'high' ? 'text-warning' : 'text-success'}">${overallTier.toUpperCase()}</div>
        <div class="label">Risk Tier</div>
      </div>
      <div class="report-summary-item">
        <div class="value ${allCompliant && !anyBlocker ? 'text-success' : 'text-danger'}">${allCompliant && !anyBlocker ? 'COMPLIANT' : 'NON-COMPLIANT'}</div>
        <div class="label">Overall Status</div>
      </div>
      <div class="report-summary-item">
        <div class="value">${Object.keys(allData).length}/9</div>
        <div class="label">Phases Completed</div>
      </div>
    </div>
  </div>`;

  // Phase-by-phase results table
  html += `<div class="report-section">
    <div class="report-section-title">📋 Phase-by-Phase Results</div>
    <table class="report-table">
      <thead><tr><th>Phase</th><th>Name</th><th>Status</th><th>Compliant</th><th>Key Details</th></tr></thead>
      <tbody>
        ${[1,2,3,4,5,6,7,8,9].map(i => {
          const d = phases[i].data;
          const cfg = PHASE_CONFIG[i];
          const status = phases[i].status;
          const compliant = d ? (d.compliant ? 'compliant' : 'non-compliant') : 'N/A';
          let detail = d ? (d.summary || d.rationale || d.overallDriftStatus || d.oversightLevel || '') : 'Not executed';
          if (d?.tests) detail = `${d.tests.filter(t => !t.passed).length}/${d.tests.length} tests failed`;
          if (d?.metrics && d.metrics[0]?.drifted !== undefined) {
            const drifted = d.metrics.filter(m => m.drifted).length;
            detail = `${drifted}/${d.metrics.length} features drifted`;
          }
          if (d?.categoryScores) {
            const scores = Object.entries(d.categoryScores).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(' | ');
            detail = scores;
          }
          return `<tr>
            <td><strong>${i}</strong></td>
            <td>${cfg.icon} ${cfg.title}</td>
            <td><span class="status-badge ${status === 'passed' ? 'compliant' : 'non-compliant'}">${status.toUpperCase()}</span></td>
            <td><span class="status-badge ${compliant === 'compliant' ? 'compliant' : 'non-compliant'}">${compliant}</span></td>
            <td style="font-size:12px;color:var(--text-secondary)">${detail.substring(0, 120)}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  </div>`;

  // Certificate section
  if (certData) {
    html += `<div class="report-section">
      <div class="report-section-title">📜 Audit Certificate</div>
      <div class="certificate-display">
        <div class="cert-icon">🏆</div>
        <div class="cert-title">W3C Verifiable Credential</div>
        <div class="cert-details">
          <p>Issuer: ${certData.issuerName || certData.vc?.issuer?.name || 'AI Governance Auditor'}</p>
          <p>Model: ${certData.modelId || certData.vc?.credentialSubject?.modelId || state.modelId}</p>
          <p>Score: ${certData.weightedScore || certData.vc?.credentialSubject?.auditScore || 'N/A'}/100</p>
          <p>Tier: ${certData.tier || certData.vc?.credentialSubject?.tier || 'N/A'}</p>
          <p>Evidence ID: ${certData.evidenceId || 'N/A'}</p>
        </div>
        <div class="result-json">${JSON.stringify(certData.vc || certData, null, 2)}</div>
      </div>
    </div>`;
  }

  // Drift section
  if (driftData) {
    html += `<div class="report-section">
      <div class="report-section-title">📈 Post-Deployment Monitoring</div>
      <div class="result-metrics">
        ${driftData.metrics.map(m => `
          <div class="metric-card">
            <div class="metric-value ${m.drifted ? 'text-danger' : 'text-success'}">${m.driftScore.toFixed(3)}</div>
            <div class="metric-label">${m.feature}</div>
            <div class="metric-status ${m.drifted ? 'text-danger' : 'text-success'}">${m.drifted ? '⚠ DRIFTED' : '✓ STABLE'}</div>
          </div>
        `).join('')}
      </div>
      <p style="font-size:13px;color:var(--text-secondary)">Overall Status: <strong style="color:${driftData.overallDriftStatus === 'stable' ? 'var(--success)' : 'var(--danger)'}">${driftData.overallDriftStatus.toUpperCase()}</strong></p>
    </div>`;
  }

  // BLOCKER FAILURES
  if (uniqueBlockers.length > 0) {
    html += `<div class="report-section">
      <div class="report-section-title">🚫 Blocker Failures (Certification Halted)</div>
      <div style="background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.2);border-radius:8px;padding:16px;">
        ${uniqueBlockers.map(b => `<p style="color:var(--danger);margin-bottom:8px;font-size:13px">❌ ${b}</p>`).join('')}
      </div>
    </div>`;
  }

  // EU AI Act Non-Compliance Consequences
  html += `<div class="report-section">
    <div class="report-section-title">⚖️ EU AI Act Compliance Assessment</div>
    <div class="consequences-section">
      <h3>${nonComplianceSeverity ? '⚠️ Non-Compliance Findings & Consequences' : '✅ Compliant with EU AI Act'}</h3>
      ${nonComplianceSeverity ? `
        <div class="consequence-item">
          <span class="consequence-icon">💰</span>
          <div class="consequence-content">
            <h4>Financial Penalties (Art. 71)</h4>
            <p>Non-compliance with prohibited practices: up to €35 million or 7% of worldwide annual turnover. Non-compliance with other obligations: up to €15 million or 3% of turnover. Providing incorrect information: up to €7.5 million or 1% of turnover.</p>
          </div>
        </div>
        <div class="consequence-item">
          <span class="consequence-icon">⛔</span>
          <div class="consequence-content">
            <h4>Market Restrictions & Withdrawal (Art. 47-51)</h4>
            <p>Market surveillance authorities may restrict, prohibit, or withdraw non-compliant AI systems from the market. Prohibited AI practices (Art. 5) are banned entirely within the EU.</p>
          </div>
        </div>
        <div class="consequence-item">
          <span class="consequence-icon">🛑</span>
          <div class="consequence-content">
            <h4>Certification Revocation (Art. 44)</h4>
            <p>Notified bodies may suspend or withdraw CE marking certification if ongoing monitoring reveals non-compliance. The system cannot be placed on the market without valid certification.</p>
          </div>
        </div>
        <div class="consequence-item">
          <span class="consequence-icon">📋</span>
          <div class="consequence-content">
            <h4>Corrective Action Orders (Art. 47)</h4>
            <p>Authorities can order immediate corrective actions, including system recalls, data deletion, and mandatory algorithm retraining within specified deadlines.</p>
          </div>
        </div>
        <div class="consequence-item">
          <span class="consequence-icon">⚖️</span>
          <div class="consequence-content">
            <h4>Liability & Legal Exposure</h4>
            <p>Victims of AI-caused harm may seek damages under the AI Liability Directive. Non-compliance with bias/fairness requirements creates exposure to discrimination lawsuits and class actions.</p>
          </div>
        </div>
        <div class="consequence-item">
          <span class="consequence-icon">🌍</span>
          <div class="consequence-content">
            <h4>Reputational Damage & Market Exclusion</h4>
            <p>Public disclosure of enforcement actions (Art. 78). Loss of customer trust, partner agreements, and exclusion from public procurement contracts requiring AI Act compliance.</p>
          </div>
        </div>
      ` : `
        <p style="color:var(--success);font-size:14px;">
          The AI system meets the compliance requirements of the EU AI Act. 
          No enforcement actions or penalties are warranted based on this audit.
        </p>
      `}
    </div>
  </div>`;

  document.getElementById('reportContent').innerHTML = html;
}

// ─── Initialization ──────────────────────────────────────────────────

async function init() {
  // Check backend health
  const health = await checkHealth();
  const dot = document.getElementById('connectionDot');
  const label = document.getElementById('connectionLabel');
  if (health) {
    dot.classList.add('connected');
    label.textContent = 'Connected to AI Governance Backend';
  } else {
    dot.classList.remove('connected');
    label.textContent = 'Backend Unavailable — using demo mode';
  }

  // Navigation click handlers
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const view = item.dataset.view;
      if (view) navigate(view);
    });
  });

  // Mobile menu toggle
  const menuToggle = document.getElementById('menuToggle');
  if (menuToggle) {
    menuToggle.addEventListener('click', () => {
      document.querySelector('.sidebar').classList.toggle('open');
    });
  }

  // Load initial model ID from localStorage for display
  const initModelId = localStorage.getItem('ai_gov_model_id');
  if (initModelId) state.modelId = initModelId;

  // Render dashboard
  navigate('dashboard');
}

document.addEventListener('DOMContentLoaded', init);
