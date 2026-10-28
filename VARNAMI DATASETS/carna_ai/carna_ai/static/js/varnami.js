/**
 * VARNAMI (CARNA-AI) · Core Frontend Application Logic
 * Modern, responsive Carnatic music analysis and composition platform
 */

// Global State
const STATE = {
  activePage: 'home',
  ragas: [],
  ragasMap: {},
  swaras: [],
  glossary: [],
  samples: [],
  activeAnalysis: null,
  activeCineAnalysis: null,
  activeComposition: null,
  activeHumming: null,
  selectedRagaForModal: null,
  user: null,
  audioCtx: null,
  mediaRecorder: null,
  recordedAudioChunks: [],
  recordingTimer: null,
  recordingStartTime: null,
  library: []
};

// Utilities
const $ = (id) => document.getElementById(id);
const $$ = (selector) => document.querySelectorAll(selector);

function showToast(message, type = 'ok') {
  const container = $('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icon = type === 'ok' ? '✓' : type === 'warn' ? '⚠' : '✕';
  toast.innerHTML = `<span style="font-weight:700; color:var(--${type})">${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// User Profile Management
function initUser() {
  const saved = localStorage.getItem('varnami_user');
  if (saved) {
    try { STATE.user = JSON.parse(saved); } catch (e) { STATE.user = null; }
  }
  if (!STATE.user) {
    STATE.user = {
      name: 'Vidya Narayanan',
      role: 'Carnatic Student',
      email: 'vidya@carnatic.edu',
      tonicHz: 146.83,
      kattai: '2 Kattai (D)',
      avatar: 'VN'
    };
    localStorage.setItem('varnami_user', JSON.stringify(STATE.user));
  }
  updateUserUI();
}

function updateUserUI() {
  const badge = $('user-badge');
  if (!badge) return;
  $('user-name-display').textContent = STATE.user.name;
  $('user-role-display').textContent = STATE.user.role;
  $('user-avatar-display').textContent = STATE.user.avatar || STATE.user.name.slice(0, 2).toUpperCase();
}

function openAuthModal(tab = 'signin') {
  $('auth-modal').classList.add('active');
  switchAuthTab(tab);
}

function closeAuthModal() {
  $('auth-modal').classList.remove('active');
}

function switchAuthTab(tab) {
  $$('.auth-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  $('auth-signin-form').style.display = tab === 'signin' ? 'block' : 'none';
  $('auth-register-form').style.display = tab === 'register' ? 'block' : 'none';
  $('auth-profile-form').style.display = tab === 'profile' ? 'block' : 'none';
  if (tab === 'profile') {
    $('prof-name').value = STATE.user.name;
    $('prof-role').value = STATE.user.role;
    $('prof-email').value = STATE.user.email;
    $('prof-tonic').value = STATE.user.tonicHz;
  }
}

function demoLogin(type) {
  if (type === 'student') {
    STATE.user = { name: 'Vidya Narayanan', role: 'Carnatic Student', email: 'vidya@carnatic.edu', tonicHz: 146.83, kattai: '2 Kattai (D)', avatar: 'VN' };
  } else if (type === 'musician') {
    STATE.user = { name: 'Sundararajan Vidwan', role: 'Vocalist & Vainika', email: 'sundar@vidwan.org', tonicHz: 138.59, kattai: '1 Kattai (C)', avatar: 'SV' };
  } else if (type === 'composer') {
    STATE.user = { name: 'Arvind Swaminathan', role: 'Cine & Fusion Composer', email: 'arvind@carna-ai.music', tonicHz: 146.83, kattai: '2 Kattai (D)', avatar: 'AS' };
  }
  localStorage.setItem('varnami_user', JSON.stringify(STATE.user));
  updateUserUI();
  closeAuthModal();
  showToast(`Logged in as ${STATE.user.name} (${STATE.user.role})`);
}

// Page Navigation
function showPage(pageId) {
  STATE.activePage = pageId;
  $$('.page-view').forEach(p => p.classList.remove('active'));
  $$('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.page === pageId));
  
  const target = $(`page-${pageId}`);
  if (target) {
    target.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Mobile menu close
  const navLinks = $('nav-links');
  if (navLinks) navLinks.classList.remove('mobile-open');

  // Trigger page-specific re-renders
  if (pageId === 'explorer') renderRagaGrid();
  if (pageId === 'library') renderLibrary();
  if (pageId === 'glossary') renderGlossary();
}

// Library Management (Local Storage)
function initLibrary() {
  const saved = localStorage.getItem('varnami_library');
  if (saved) {
    try { STATE.library = JSON.parse(saved); } catch (e) { STATE.library = []; }
  } else {
    // Seed sample items if library is brand new
    STATE.library = [
      {
        id: 'seed-1',
        title: 'Ninnukori Varnam Analysis',
        type: 'carnatic',
        raga: 'Mohanam',
        confidence: 0.96,
        date: new Date(Date.now() - 3600000 * 24).toLocaleString(),
        notation: "S R2 G3 P D2 S' | S' D2 P G3 R2 S",
        tonicHz: 146.83
      },
      {
        id: 'seed-2',
        title: 'Mohanam & Hamsadhwani Blend',
        type: 'composition',
        raga: 'Mohanam + Hamsadhwani',
        confidence: 1.0,
        date: new Date(Date.now() - 3600000 * 5).toLocaleString(),
        notation: "S R2 G3 P D2 | P G3 R2 S , S R2 G3 P N3 S'",
        tonicHz: 146.83
      }
    ];
    localStorage.setItem('varnami_library', JSON.stringify(STATE.library));
  }
}

function saveToLibrary(item) {
  item.id = 'lib-' + Date.now();
  item.date = new Date().toLocaleString();
  STATE.library.unshift(item);
  localStorage.setItem('varnami_library', JSON.stringify(STATE.library));
  showToast(`"${item.title}" saved to your personal library!`);
}

function deleteLibraryItem(id) {
  STATE.library = STATE.library.filter(i => i.id !== id);
  localStorage.setItem('varnami_library', JSON.stringify(STATE.library));
  renderLibrary();
  showToast('Item deleted from library');
}

function renderLibrary(filter = 'all') {
  const container = $('library-grid');
  if (!container) return;
  const search = ($('library-search')?.value || '').toLowerCase().trim();
  
  let list = STATE.library;
  if (filter !== 'all') list = list.filter(i => i.type === filter);
  if (search) list = list.filter(i => (i.title + i.raga + (i.notation || '')).toLowerCase().includes(search));

  if (!list.length) {
    container.innerHTML = `
      <div class="col-12" style="text-align:center; padding:3rem; color:var(--text-muted)">
        <p style="font-size:1.1rem; margin-bottom:0.5rem">No saved records found.</p>
        <small>Run a song analysis or compose a raga phrase and click "Save to Library".</small>
      </div>`;
    return;
  }

  container.innerHTML = list.map(item => `
    <div class="card col-4" style="display:flex; flex-direction:column; justify-content:space-between">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.8rem">
          <span class="card-badge" style="${item.type === 'composition' ? 'background:rgba(138,56,245,0.15); border-color:var(--purple-vibrant); color:#e9d5ff' : ''}">
            ${item.type.toUpperCase()}
          </span>
          <small style="color:var(--text-muted); font-size:0.75rem">${item.date}</small>
        </div>
        <h4 style="margin-bottom:0.4rem">${item.title}</h4>
        <div style="font-size:0.85rem; color:var(--gold-light); margin-bottom:0.6rem">
          <b>Raga:</b> ${item.raga} ${item.confidence ? `· ${(item.confidence * 100).toFixed(0)}% fit` : ''}
        </div>
        ${item.notation ? `<pre style="font-family:var(--font-mono); font-size:0.78rem; background:var(--bg-input); padding:0.6rem; border-radius:var(--radius-sm); border:1px solid var(--line-light); max-height:80px; overflow-y:auto; margin-bottom:0.8rem">${item.notation}</pre>` : ''}
      </div>
      <div style="display:flex; gap:0.5rem; justify-content:flex-end; border-top:1px solid var(--line-light); padding-top:0.6rem">
        <button class="btn btn-secondary btn-sm" onclick="exportLibraryItem('${item.id}')">Export</button>
        <button class="btn btn-secondary btn-sm" style="color:var(--err)" onclick="deleteLibraryItem('${item.id}')">Delete</button>
      </div>
    </div>
  `).join('');
}

function exportLibraryItem(id) {
  const item = STATE.library.find(i => i.id === id);
  if (!item) return;
  const blob = new Blob([JSON.stringify(item, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${item.title.replace(/\s+/g, '_')}_varnami.json`;
  a.click();
}

// Fetch Initial Data from API
async function loadInitialData() {
  try {
    const [ragasRes, swarasRes, glossaryRes, samplesRes] = await Promise.all([
      fetch('/api/ragas'),
      fetch('/api/swaras'),
      fetch('/api/glossary'),
      fetch('/api/samples')
    ]);

    if (ragasRes.ok) {
      STATE.ragas = await ragasRes.json();
      STATE.ragas.forEach(r => STATE.ragasMap[r.name] = r);
      populateRagaSelectors();
    }
    if (swarasRes.ok) STATE.swaras = await swarasRes.json();
    if (glossaryRes.ok) STATE.glossary = await glossaryRes.json();
    if (samplesRes.ok) {
      STATE.samples = await samplesRes.json();
      populateSampleSelectors();
    }
  } catch (err) {
    console.error('Error loading initial data:', err);
  }
}

function populateRagaSelectors() {
  const names = STATE.ragas.map(r => r.name);
  ['composer-raga-a', 'composer-raga-b', 'carnatic-demo-raga', 'cine-demo-raga'].forEach(id => {
    const el = $(id);
    if (!el) return;
    const current = el.value;
    el.innerHTML = names.map(n => `<option value="${n}">${n}</option>`).join('');
    if (current && names.includes(current)) el.value = current;
  });

  ['carnatic-demo-mix', 'cine-demo-mix'].forEach(id => {
    const el = $(id);
    if (!el) return;
    const current = el.value;
    el.innerHTML = `<option value="">Single Raga (No Mix)</option>` + names.map(n => `<option value="${n}">Mix: ${n}</option>`).join('');
    if (current) el.value = current;
  });

  if ($('composer-raga-a')) $('composer-raga-a').value = 'Mohanam';
  if ($('composer-raga-b')) $('composer-raga-b').value = 'Hamsadhwani';
  if ($('carnatic-demo-raga')) $('carnatic-demo-raga').value = 'Mohanam';
  if ($('cine-demo-raga')) $('cine-demo-raga').value = 'Mechakalyani';
  if ($('cine-demo-mix')) $('cine-demo-mix').value = 'Ahiri';

  updateComposerCompatibility();
}

function runCinePreset(title, ragaA, ragaB) {
  if ($('cine-demo-raga')) $('cine-demo-raga').value = ragaA;
  if ($('cine-demo-mix')) $('cine-demo-mix').value = ragaB;
  showToast(`Loaded ${title}! Running multi-raga decomposition...`);
  runSyntheticDemo('cine');
}

function populateSampleSelectors() {
  const carnaticSelect = $('carnatic-sample-select');
  if (carnaticSelect && STATE.samples.length) {
    carnaticSelect.innerHTML = `<option value="">-- Choose a preloaded classical recording --</option>` +
      STATE.samples.map(s => `<option value="${s.filename}">${s.title} (${s.raga} - ${s.singer})</option>`).join('');
  }
}

// -------------------------------------------------------------
// CARNATIC SONG ANALYSIS LOGIC
// -------------------------------------------------------------
async function runCarnaticAnalysis(useSample = null) {
  const statusEl = $('carnatic-status');
  const errEl = $('carnatic-err');
  const resultsContainer = $('carnatic-results');
  errEl.textContent = '';
  statusEl.innerHTML = '<span style="color:var(--gold-bright); font-weight:700">⏳ Analysing audio (spectral pitch tracking &amp; swara extraction, takes ~3-5s)...</span>';
  resultsContainer.style.display = 'none';

  try {
    let data;
    if (useSample) {
      const tonic = $('carnatic-tonic').value;
      const secs = $('carnatic-secs').value;
      const url = `/api/analyze-sample?sample=${encodeURIComponent(useSample)}&max_seconds=${secs}${tonic ? `&tonic_hz=${tonic}` : ''}`;
      const res = await fetch(url);
      data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Sample analysis failed');
    } else {
      const fileInput = $('carnatic-file');
      if (!fileInput.files.length) throw new Error('Please select an audio file (WAV or MP3) or click a sample button.');
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      fd.append('max_seconds', $('carnatic-secs').value);
      if ($('carnatic-tonic').value) fd.append('tonic_hz', $('carnatic-tonic').value);
      
      const res = await fetch('/api/analyze', { method: 'POST', body: fd });
      data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Audio analysis failed');
    }

    STATE.activeAnalysis = data;
    renderCarnaticDashboard(data);
    statusEl.innerHTML = '<span style="color:var(--ok); font-weight:700">✓ Analysis Complete</span>';
    setTimeout(() => { if (statusEl.textContent.includes('Complete')) statusEl.innerHTML = ''; }, 3000);
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
    showToast(`Analysis complete: Detected ${data.classification?.predicted || 'Raga'}!`);
  } catch (e) {
    statusEl.innerHTML = '';
    errEl.textContent = e.message;
    showToast(e.message, 'err');
  }
}

async function runSyntheticDemo(target = 'carnatic') {
  const statusEl = $(`${target}-status`);
  const errEl = $(`${target}-err`);
  const resultsContainer = $(`${target}-results`);
  errEl.textContent = '';
  statusEl.innerHTML = '<span style="color:var(--gold-bright); font-weight:700">⏳ Synthesizing grammar-based clip &amp; running full pipeline (~3-5s)...</span>';

  try {
    const raga = $(`${target}-demo-raga`)?.value || 'Mohanam';
    const mix = $(`${target}-demo-mix`)?.value || '';
    const secs = 30;
    const seed = Math.floor(Math.random() * 1000);
    const url = `/api/demo?raga=${encodeURIComponent(raga)}&mix=${encodeURIComponent(mix)}&seconds=${secs}&seed=${seed}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Demo generation failed');

    if (target === 'carnatic') {
      STATE.activeAnalysis = data;
      renderCarnaticDashboard(data);
    } else {
      STATE.activeCineAnalysis = data;
      renderCineDashboard(data);
    }

    statusEl.innerHTML = '<span style="color:var(--ok); font-weight:700">✓ Demo Ready</span>';
    setTimeout(() => { if (statusEl.textContent.includes('Ready')) statusEl.innerHTML = ''; }, 3000);
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
    showToast(`Synthetic test complete for ${raga}!`);
  } catch (e) {
    statusEl.innerHTML = '';
    errEl.textContent = e.message;
    showToast(e.message, 'err');
  }
}

function renderCarnaticDashboard(d) {
  const pc = d.classification;
  const ragaName = pc.predicted;
  const meta = STATE.ragasMap[ragaName] || {};

  $('res-predicted-raga').textContent = ragaName;
  $('res-raga-type').textContent = meta.type || 'Carnatic Raga';
  $('res-raga-margin').textContent = `Margin over runner-up: ${(pc.margin * 100).toFixed(0)} pts`;
  $('res-raga-confidence').textContent = `${(pc.confidence * 100).toFixed(0)}% fit`;

  // Tonic & Duration
  $('res-tonic-val').textContent = `${d.tonic_hz.toFixed(1)} Hz (${d.tonic_source || 'estimated'})`;
  $('res-duration-val').textContent = `${d.duration_s.toFixed(1)} s · ${d.n_notes} segmented notes`;
  
  if (d.tonic_warning) {
    $('res-tonic-warning').style.display = 'block';
    $('res-tonic-warning-text').textContent = d.tonic_warning;
  } else {
    $('res-tonic-warning').style.display = 'none';
  }

  // Arohanam & Avarohanam
  $('res-arohanam').innerHTML = (meta.arohanam || 'S R G M P D N S\'').split(' ')
    .map(s => `<span class="swara-pill">${s}</span>`).join('');
  $('res-avarohanam').innerHTML = (meta.avarohanam || 'S\' N D P M G R S').split(' ')
    .map(s => `<span class="swara-pill">${s}</span>`).join('');

  // Confidence Bars
  $('res-confidence-bars').innerHTML = pc.top.map((t, idx) => `
    <div class="confidence-bar">
      <span class="confidence-bar-name">${idx + 1}. ${t.raga}</span>
      <div class="confidence-bar-track">
        <div class="confidence-bar-fill" style="width: ${Math.max(4, t.confidence * 100)}%"></div>
      </div>
      <span class="confidence-bar-pct">${(t.confidence * 100).toFixed(0)}%</span>
    </div>
  `).join('');

  // Evidence List
  const ev = d.explanation;
  if (ev && ev.evidence) {
    $('res-evidence-list').innerHTML = ev.evidence.map(item => `
      <li style="margin-bottom:0.4rem; color:${item.kind === 'warning' ? 'var(--warn)' : 'var(--text-soft)'}">
        ${item.kind === 'warning' ? '⚠ ' : '✓ '} ${item.text}
      </li>
    `).join('');
  }

  // Notation Box
  $('res-notation').textContent = d.notation || '—';

  // Canvases
  drawPitchContour($('carnatic-pitch-canvas'), d);
  drawSwaraTimeline($('carnatic-timeline-canvas'), d);
}

// -------------------------------------------------------------
// CINE SONG ANALYSIS LOGIC
// -------------------------------------------------------------
async function runCineAnalysis(useSample = null) {
  const statusEl = $('cine-status');
  const errEl = $('cine-err');
  const resultsContainer = $('cine-results');
  errEl.textContent = '';
  statusEl.innerHTML = '<span style="color:var(--gold-bright); font-weight:700">⏳ Analyzing Cine Song multi-raga blend &amp; progression (~3-5s)...</span>';
  resultsContainer.style.display = 'none';

  try {
    let data;
    if (useSample) {
      const url = `/api/analyze-sample?sample=${encodeURIComponent(useSample)}&max_seconds=35`;
      const res = await fetch(url);
      data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Sample analysis failed');
    } else {
      const fileInput = $('cine-file');
      if (!fileInput.files.length) throw new Error('Please select a film song audio file or click a reference button.');
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      fd.append('max_seconds', $('cine-secs').value);
      const res = await fetch('/api/analyze', { method: 'POST', body: fd });
      data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Audio analysis failed');
    }

    STATE.activeCineAnalysis = data;
    renderCineDashboard(data);
    statusEl.innerHTML = '<span style="color:var(--ok); font-weight:700">✓ Cine Analysis Complete</span>';
    setTimeout(() => { if (statusEl.textContent.includes('Complete')) statusEl.innerHTML = ''; }, 3000);
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
    showToast('Cine analysis complete!');
  } catch (e) {
    statusEl.innerHTML = '';
    errEl.textContent = e.message;
    showToast(e.message, 'err');
  }
}

function renderCineDashboard(d) {
  const f = d.film;
  if (!f) return;

  $('cine-verdict').textContent = f.verdict;
  $('cine-primary-raga').textContent = `${f.primary.raga} (${f.primary.pct}%)`;
  $('cine-secondary-raga').textContent = f.secondary.raga ? `${f.secondary.raga} (${f.secondary.pct}%)` : 'None identified';
  $('cine-other-pct').textContent = `${f.other_pct}%`;

  // Stacked Bar
  const stack = $('cine-film-stack');
  stack.innerHTML = f.weights.map(w => `
    <div class="film-stack-segment" title="${w.raga}: ${w.pct}%" style="width:${w.pct}%; background:${getHue(w.raga)}"></div>
  `).join('') + `<div style="flex:1; background:var(--line-light)"></div>`;

  // Weights Bars
  $('cine-weights-bars').innerHTML = f.weights.slice(0, 5).map(w => `
    <div class="confidence-bar">
      <span class="confidence-bar-name">${w.raga}</span>
      <div class="confidence-bar-track">
        <div class="confidence-bar-fill" style="width:${w.pct}%; background:${getHue(w.raga)}"></div>
      </div>
      <span class="confidence-bar-pct">${w.pct}%</span>
    </div>
  `).join('');

  // 20s Window Timeline
  const tlContainer = $('cine-window-timeline');
  if (f.window_timeline && f.window_timeline.length) {
    tlContainer.innerHTML = f.window_timeline.map(w => `
      <div style="background:var(--bg-input); border:1px solid var(--line); border-radius:var(--radius-md); padding:0.6rem 0.9rem; text-align:center">
        <div style="font-size:0.75rem; color:var(--text-muted)">${w.t0.toFixed(0)}s – ${w.t1.toFixed(0)}s</div>
        <div style="font-weight:700; color:var(--gold-bright); font-size:0.95rem">${w.raga}</div>
        <div style="font-size:0.8rem; color:var(--text-soft)">${(w.p * 100).toFixed(0)}% fit</div>
      </div>
    `).join('');
  } else {
    tlContainer.innerHTML = `<span style="color:var(--text-muted)">Audio too short for multi-window progression.</span>`;
  }

  // Draw Canvases
  drawPitchContour($('cine-pitch-canvas'), d);
  drawSwaraTimeline($('cine-timeline-canvas'), d);
  $('cine-notation').textContent = d.notation || '—';
}

function getHue(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
  return `hsl(${h}, 65%, 50%)`;
}

// -------------------------------------------------------------
// PITCH & TIMELINE CANVASES
// -------------------------------------------------------------
function drawPitchContour(canvas, d) {
  if (!canvas || !d || !d.pitch) return;
  const r = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 800;
  const h = 340;
  canvas.width = w * r;
  canvas.height = h * r;
  const ctx = canvas.getContext('2d');
  ctx.scale(r, r);

  const t = d.pitch.t;
  const cents = d.pitch.cents;
  const T_max = t[t.length - 1] || 1;

  const valid = cents.filter(c => c !== null).sort((a, b) => a - b);
  let lo = -200, hi = 1400;
  if (valid.length > 10) {
    lo = Math.floor((valid[Math.floor(valid.length * 0.02)] - 60) / 100) * 100;
    hi = Math.ceil((valid[Math.floor(valid.length * 0.98)] + 60) / 100) * 100;
  }

  const padLeft = 48, padBottom = 24, padTop = 12, padRight = 12;
  const X = (sec) => padLeft + (sec / T_max) * (w - padLeft - padRight);
  const Y = (cn) => padTop + (1 - (cn - lo) / (hi - lo)) * (h - padTop - padBottom);

  // Background
  ctx.fillStyle = '#0c081a';
  ctx.fillRect(0, 0, w, h);

  // Semitone lines
  const swaraNames = { 0: 'S', 1: 'R1', 2: 'R2', 3: 'G2', 4: 'G3', 5: 'M1', 6: 'M2', 7: 'P', 8: 'D1', 9: 'D2', 10: 'N2', 11: 'N3', 12: "S'" };
  for (let s = lo / 100; s <= hi / 100; s++) {
    const yVal = Y(s * 100);
    const m = ((s % 12) + 12) % 12;
    const isSa = m === 0;

    ctx.strokeStyle = isSa ? 'rgba(229,176,66,0.35)' : 'rgba(255,255,255,0.06)';
    ctx.lineWidth = isSa ? 1.5 : 1;
    ctx.beginPath();
    ctx.moveTo(padLeft, yVal);
    ctx.lineTo(w - padRight, yVal);
    ctx.stroke();

    ctx.fillStyle = isSa ? 'var(--gold-bright)' : 'var(--text-muted)';
    ctx.font = isSa ? 'bold 11px system-ui' : '10px system-ui';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(swaraNames[m] || '', padLeft - 6, yVal);
  }

  // Note bounding blocks
  if (d.notes) {
    d.notes.forEach(n => {
      const x1 = X(n.start);
      const x2 = X(n.end);
      const yMid = Y(n.semitone * 100);
      ctx.fillStyle = `hsla(${n.pc * 30}, 65%, 55%, 0.18)`;
      ctx.fillRect(x1, yMid - 10, Math.max(2, x2 - x1), 20);
    });
  }

  // Pitch Curve
  ctx.strokeStyle = '#e5b042';
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  let inLine = false;
  for (let i = 0; i < t.length; i++) {
    if (cents[i] === null) {
      inLine = false;
      continue;
    }
    const px = X(t[i]);
    const py = Y(cents[i]);
    if (!inLine) {
      ctx.moveTo(px, py);
      inLine = true;
    } else {
      ctx.lineTo(px, py);
    }
  }
  ctx.stroke();

  // Time Axis
  ctx.fillStyle = 'var(--text-muted)';
  ctx.textAlign = 'center';
  ctx.font = '10px system-ui';
  for (let sec = 0; sec <= T_max; sec += Math.max(5, Math.round(T_max / 10 / 5) * 5)) {
    ctx.fillText(`${sec}s`, X(sec), h - 6);
  }
}

function drawSwaraTimeline(canvas, d) {
  if (!canvas || !d || !d.notes) return;
  const pps = 60; // pixels per second
  const totalW = Math.max(canvas.parentElement.clientWidth, d.duration_s * pps);
  canvas.style.width = totalW + 'px';

  const r = window.devicePixelRatio || 1;
  canvas.width = totalW * r;
  canvas.height = 64 * r;
  const ctx = canvas.getContext('2d');
  ctx.scale(r, r);

  ctx.fillStyle = '#0c081a';
  ctx.fillRect(0, 0, totalW, 64);

  const glyphs = { oscillation: '~', glide_up: '/', glide_down: '\\', steady: '' };
  d.notes.forEach(n => {
    const x = n.start * pps;
    const w = Math.max(2, n.dur * pps - 1);
    ctx.fillStyle = `hsla(${n.pc * 30}, 65%, 45%, 0.85)`;
    ctx.fillRect(x, 8, w, 36);

    if (w > 18) {
      ctx.fillStyle = '#ffffff';
      ctx.font = '600 11px system-ui';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(n.label + (glyphs[n.movement] || ''), x + w / 2, 26);
    }
  });

  // Time markers
  ctx.fillStyle = 'var(--text-muted)';
  ctx.font = '10px system-ui';
  ctx.textAlign = 'left';
  for (let s = 0; s < d.duration_s; s += 5) {
    ctx.fillText(`${s}s`, s * pps + 2, 56);
  }
}

// -------------------------------------------------------------
// ALAPANA & HUMMING (MICROPHONE RECORDING)
// -------------------------------------------------------------
async function toggleHummingRecording() {
  const btn = $('mic-record-btn');
  const timerEl = $('mic-timer');
  const statusEl = $('humming-status');

  if (STATE.mediaRecorder && STATE.mediaRecorder.state === 'recording') {
    // Stop recording
    STATE.mediaRecorder.stop();
    clearInterval(STATE.recordingTimer);
    btn.classList.remove('recording');
    btn.innerHTML = `<span>🎙️</span> Start Alapana Recording`;
    statusEl.textContent = 'Audio recorded. Ready to analyze.';
    return;
  }

  // Start recording
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    STATE.mediaRecorder = new MediaRecorder(stream);
    STATE.recordedAudioChunks = [];

    // Audio Visualizer Setup
    if (!STATE.audioCtx) STATE.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = STATE.audioCtx.createMediaStreamSource(stream);
    const analyser = STATE.audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    visualizeMicInput(analyser);

    STATE.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) STATE.recordedAudioChunks.push(e.data);
    };

    STATE.mediaRecorder.onstop = () => {
      const blob = new Blob(STATE.recordedAudioChunks, { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(blob);
      const player = $('humming-player');
      player.src = audioUrl;
      player.style.display = 'block';
      $('humming-analyze-btn').disabled = false;
      STATE.hummingBlob = blob;
      stream.getTracks().forEach(t => t.stop());
    };

    STATE.mediaRecorder.start();
    STATE.recordingStartTime = Date.now();
    btn.classList.add('recording');
    btn.innerHTML = `<span style="color:var(--err)">⏹</span> Stop Recording`;
    statusEl.textContent = 'Recording vocal alapana... Sing or hum clearly.';

    STATE.recordingTimer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - STATE.recordingStartTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const secs = String(elapsed % 60).padStart(2, '0');
      timerEl.textContent = `${mins}:${secs}`;
      if (elapsed >= 120) toggleHummingRecording(); // Cap at 2 min
    }, 500);

  } catch (err) {
    statusEl.textContent = '';
    showToast('Microphone access denied: ' + err.message, 'err');
  }
}

function visualizeMicInput(analyser) {
  const canvas = $('mic-visualizer-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    if (!STATE.mediaRecorder || STATE.mediaRecorder.state !== 'recording') return;
    requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);

    ctx.fillStyle = '#080612';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const barWidth = (canvas.width / bufferLength) * 2.5;
    let x = 0;
    for (let i = 0; i < bufferLength; i++) {
      const barHeight = (dataArray[i] / 255) * canvas.height;
      ctx.fillStyle = `hsla(${260 + (i / bufferLength) * 60}, 80%, 60%, 0.8)`;
      ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
      x += barWidth + 1;
    }
  }
  draw();
}

async function analyzeHummingAudio() {
  const statusEl = $('humming-status');
  const errEl = $('humming-err');
  const resultsContainer = $('humming-results');
  errEl.textContent = '';
  statusEl.textContent = 'Tracking vocal pitch & identifying candidate ragas...';

  try {
    let blob = STATE.hummingBlob;
    const fileInput = $('humming-file');
    if (!blob && fileInput.files.length) blob = fileInput.files[0];
    if (!blob) throw new Error('Please record humming or choose an audio file first.');

    const fd = new FormData();
    fd.append('file', blob, 'humming.wav');
    if ($('humming-tonic').value) fd.append('tonic_hz', $('humming-tonic').value);

    const res = await fetch('/api/humming', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Humming analysis failed');

    STATE.activeHumming = data;
    renderHummingResults(data);
    statusEl.textContent = '';
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
    showToast(`Humming match: ${data.classification?.predicted || 'Raga'}!`);
  } catch (e) {
    statusEl.textContent = '';
    errEl.textContent = e.message;
    showToast(e.message, 'err');
  }
}

function renderHummingResults(d) {
  const pc = d.classification;
  $('hum-top-raga').textContent = pc.predicted;
  $('hum-top-confidence').textContent = `${(pc.confidence * 100).toFixed(0)}% estimated fit`;
  $('hum-tonic-val').textContent = `Tonic Sa = ${d.tonic_hz.toFixed(1)} Hz (${d.tonic_source || 'detected'})`;

  $('hum-candidates').innerHTML = pc.top.map((t, i) => `
    <div class="confidence-bar">
      <span class="confidence-bar-name">${i + 1}. ${t.raga}</span>
      <div class="confidence-bar-track">
        <div class="confidence-bar-fill" style="width:${t.confidence * 100}%"></div>
      </div>
      <span class="confidence-bar-pct">${(t.confidence * 100).toFixed(0)}%</span>
    </div>
  `).join('');

  drawPitchContour($('humming-pitch-canvas'), d);
  drawSwaraTimeline($('humming-timeline-canvas'), d);
  $('hum-notation').textContent = d.notation || '—';
}

function sendHummingToComposer() {
  if (!STATE.activeHumming) return;
  const pred = STATE.activeHumming.classification?.predicted;
  if (pred && $('composer-raga-a')) {
    $('composer-raga-a').value = pred;
    updateComposerCompatibility();
    showPage('composer');
    showToast(`Loaded ${pred} into AI Composer!`);
  }
}

// -------------------------------------------------------------
// RAGA EXPLORER LOGIC
// -------------------------------------------------------------
let activeRagaFilter = 'all';

function setRagaFilter(filter) {
  activeRagaFilter = filter;
  $$('.raga-filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === filter));
  renderRagaGrid();
}

function renderRagaGrid() {
  const container = $('raga-grid');
  if (!container) return;
  const search = ($('raga-search')?.value || '').toLowerCase().trim();

  let list = STATE.ragas;
  if (activeRagaFilter === 'melakarta') list = list.filter(r => r.type === 'Melakarta');
  if (activeRagaFilter === 'janya') list = list.filter(r => r.type !== 'Melakarta');
  if (activeRagaFilter === 'audava') list = list.filter(r => r.arohanam_swaras === 5 || (r.arohanam_class || '').includes('Audava'));
  if (activeRagaFilter === 'shadava') list = list.filter(r => r.arohanam_swaras === 6 || (r.arohanam_class || '').includes('Shadava'));
  if (activeRagaFilter === 'sampoorna') list = list.filter(r => r.arohanam_swaras === 7 || (r.arohanam_class || '').includes('Sampoorna'));
  if (activeRagaFilter === 'vakra') list = list.filter(r => (r.vakra || '').toLowerCase() === 'yes');

  if (search) {
    list = list.filter(r => (r.name + r.arohanam + r.avarohanam + (r.parent_melakarta || '')).toLowerCase().includes(search));
  }

  $('raga-count-badge').textContent = `${list.length} Ragas`;

  container.innerHTML = list.map(r => `
    <div class="raga-card col-4" onclick="openRagaModal('${r.name}')">
      <div class="raga-card-header">
        <div>
          <div class="raga-card-title">${r.name}</div>
          <small style="color:var(--text-muted); font-size:0.75rem">
            ${r.type === 'Melakarta' ? `Melakarta #${r.melakarta_no || ''}` : `Janya of ${r.parent_melakarta || 'Melakarta'}`}
          </small>
        </div>
        <span class="card-badge" style="background:rgba(229,176,66,0.08)">
          ${r.arohanam_swaras || 7} Notes
        </span>
      </div>
      <div class="raga-card-scale">
        <span style="color:var(--text-muted)">Aro:</span> ${r.arohanam}
      </div>
      <div class="raga-card-scale">
        <span style="color:var(--text-muted)">Avaro:</span> ${r.avarohanam}
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.4rem; padding-top:0.6rem; border-top:1px solid var(--line-light)">
        <span class="swara-pill" style="font-size:0.7rem">${r.usage_band || 'Classical'}</span>
        <span style="font-size:0.8rem; color:var(--gold); font-weight:600">View Profile & Scale →</span>
      </div>
    </div>
  `).join('');
}

function openRagaModal(name) {
  const r = STATE.ragasMap[name];
  if (!r) return;
  STATE.selectedRagaForModal = r;

  $('modal-raga-title').textContent = r.name;
  $('modal-raga-type').textContent = r.type === 'Melakarta' ? `72-Melakarta System Root #${r.melakarta_no || ''}` : `Janya Raga (Parent: ${r.parent_melakarta || '—'})`;
  $('modal-arohanam').textContent = r.arohanam;
  $('modal-avarohanam').textContent = r.avarohanam;
  $('modal-vakra').textContent = r.vakra || 'No';

  // Swara breakdown with audio keyboard
  const swarasEl = $('modal-swaras-list');
  swarasEl.innerHTML = (r.swaras || []).map((s, idx) => {
    const semi = (r.pitch_classes && r.pitch_classes[idx] !== undefined) ? r.pitch_classes[idx] : idx;
    return `<button class="swara-pill" style="font-size:0.88rem; cursor:pointer; padding:0.35rem 0.8rem; background:rgba(229,176,66,0.15); border-color:var(--gold)" onclick="playSwaraTone(${semi})" title="Click to hear ${s}">🔊 ${s}</button>`;
  }).join(' ');

  $('raga-modal').classList.add('active');
}

function closeRagaModal() {
  $('raga-modal').classList.remove('active');
}

async function playRagaScale() {
  if (!STATE.selectedRagaForModal) return;
  const name = STATE.selectedRagaForModal.name;
  const tonic = $('modal-tonic-select')?.value || 146.83;
  showToast(`Generating scale audio for ${name} at ${tonic} Hz...`);

  try {
    const res = await fetch(`/api/raga/${encodeURIComponent(name)}/scale?tonic_hz=${tonic}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to generate scale audio');

    const player = $('modal-scale-player');
    player.src = 'data:audio/wav;base64,' + data.wav_base64;
    player.play();
  } catch (e) {
    showToast(e.message, 'err');
  }
}

// -------------------------------------------------------------
// AI COMPOSER LOGIC
// -------------------------------------------------------------
function setComposerMood(mood) {
  $$('.mood-preset-btn').forEach(b => b.classList.toggle('active', b.dataset.mood === mood));
  if (mood === 'joyous') {
    $('composer-raga-a').value = 'Mohanam';
    $('composer-raga-b').value = 'Hamsadhwani';
    $('composer-bpm').value = 92;
  } else if (mood === 'pathos') {
    $('composer-raga-a').value = 'Ahiri';
    $('composer-raga-b').value = 'Hanumatodi';
    $('composer-bpm').value = 68;
  } else if (mood === 'peaceful') {
    $('composer-raga-a').value = 'Mechakalyani';
    $('composer-raga-b').value = 'Sahana';
    $('composer-bpm').value = 75;
  } else if (mood === 'majestic') {
    $('composer-raga-a').value = 'Kharaharapriya';
    $('composer-raga-b').value = 'Sriragam';
    $('composer-bpm').value = 88;
  }
  updateComposerCompatibility();
  showToast(`Applied ${mood} mood parameters!`);
}

async function updateComposerCompatibility() {
  const a = $('composer-raga-a')?.value;
  const b = $('composer-raga-b')?.value;
  if (!a || !b) return;

  try {
    const res = await fetch(`/api/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
    const data = await res.json();
    if (!res.ok) return;

    $('comp-jaccard').textContent = `${(data.jaccard * 100).toFixed(0)}%`;
    $('comp-shared-swaras').innerHTML = (data.shared || []).map(s => `<span class="swara-pill shared">${s}</span>`).join(' ') || 'None';
    $('comp-unique-a').innerHTML = (data.only_a || []).map(s => `<span class="swara-pill unique-a">${s}</span>`).join(' ') || 'None';
    $('comp-unique-b').innerHTML = (data.only_b || []).map(s => `<span class="swara-pill unique-b">${s}</span>`).join(' ') || 'None';
  } catch (e) {}
}

async function generateComposition() {
  const statusEl = $('composer-status');
  const errEl = $('composer-err');
  const resultsContainer = $('composer-results');
  errEl.textContent = '';
  statusEl.textContent = 'Generating constrained melody & aligning sahitya syllables...';

  try {
    const payload = {
      a: $('composer-raga-a').value,
      b: $('composer-raga-b').value,
      length: parseInt($('composer-length').value, 10),
      blend: parseFloat($('composer-blend').value) / 100,
      seed: parseInt($('composer-seed').value, 10),
      tonic_hz: parseFloat($('composer-tonic').value),
      bpm: parseFloat($('composer-bpm').value),
      lyrics: $('composer-lyrics').value.trim() || null
    };

    const res = await fetch('/api/compose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Composition failed');

    STATE.activeComposition = data;
    renderCompositionResults(data);
    statusEl.textContent = '';
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
    showToast('Phrase generated successfully!');
  } catch (e) {
    statusEl.textContent = '';
    errEl.textContent = e.message;
    showToast(e.message, 'err');
  }
}

function renderCompositionResults(c) {
  $('comp-notation').textContent = c.notation;
  $('comp-legend').textContent = c.legend;

  // Dual Lyrics Notation
  if (c.lyrics && c.lyrics.dual_notation) {
    $('comp-dual-notation-container').style.display = 'block';
    $('comp-dual-notation').textContent = c.lyrics.dual_notation;
  } else {
    $('comp-dual-notation-container').style.display = 'none';
  }

  // Audio Player
  const p = $('composer-player');
  if (c.wav_base64) {
    p.src = 'data:audio/wav;base64,' + c.wav_base64;
    p.play().catch(() => {});
  }

  // Check badges
  const chkEl = $('comp-checks');
  chkEl.innerHTML = Object.entries(c.checks || {}).map(([k, v]) => `
    <span class="card-badge" style="color:var(${v ? '--ok' : '--warn'}); border-color:var(${v ? '--ok' : '--warn'})">
      ${v ? '✓' : '✗'} ${k.replace(/_/g, ' ')}
    </span>
  `).join(' ');
}

function downloadCompositionAudio() {
  if (!STATE.activeComposition || !STATE.activeComposition.wav_base64) return;
  const a = document.createElement('a');
  a.href = 'data:audio/wav;base64,' + STATE.activeComposition.wav_base64;
  a.download = `varnami_${STATE.activeComposition.a}_${STATE.activeComposition.b}_phrase.wav`;
  a.click();
}

function downloadCompositionMIDI() {
  if (!STATE.activeComposition || !STATE.activeComposition.midi_base64) return;
  const a = document.createElement('a');
  a.href = 'data:audio/midi;base64,' + STATE.activeComposition.midi_base64;
  a.download = `varnami_${STATE.activeComposition.a}_${STATE.activeComposition.b}.mid`;
  a.click();
}

function downloadCompositionSheet() {
  if (!STATE.activeComposition) return;
  const c = STATE.activeComposition;
  let text = `========================================================\n`;
  text += `VARNAMI (CARNA-AI) · Generated Composition Sheet\n`;
  text += `========================================================\n`;
  text += `Raga A: ${c.a}\nRaga B: ${c.b}\nTempo: ${c.bpm} BPM\nTonic Sa: ${c.tonic_hz} Hz\n\n`;
  text += `SWARA NOTATION:\n${c.notation}\n\n`;
  if (c.lyrics && c.lyrics.dual_notation) {
    text += `DUAL SWARA & SAHITYA ALIGNMENT:\n${c.lyrics.dual_notation}\n\n`;
  }
  text += `LEGEND:\n${c.legend}\n`;
  
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `varnami_${c.a}_${c.b}_sheet.txt`;
  a.click();
}

function saveCurrentComposition() {
  if (!STATE.activeComposition) return;
  const c = STATE.activeComposition;
  saveToLibrary({
    title: `${c.a} & ${c.b} AI Composition`,
    type: 'composition',
    raga: `${c.a} + ${c.b}`,
    notation: c.notation,
    dualNotation: c.lyrics ? c.lyrics.dual_notation : '',
    tonicHz: c.tonic_hz,
    bpm: c.bpm
  });
}

// -------------------------------------------------------------
// GLOSSARY & REFERENCE
// -------------------------------------------------------------
function renderGlossary() {
  const container = $('glossary-table-body');
  if (!container) return;
  const search = ($('glossary-search')?.value || '').toLowerCase().trim();

  let list = STATE.glossary;
  if (search) {
    list = list.filter(g => (g.term + g.definition + (g.category || '')).toLowerCase().includes(search));
  }

  container.innerHTML = list.map(g => `
    <tr>
      <td style="font-weight:700; color:var(--gold-bright)">${g.term}</td>
      <td><span class="card-badge">${g.category || 'Concept'}</span></td>
      <td style="color:var(--text-soft)">${g.definition}</td>
    </tr>
  `).join('');

  // Render Swara reference
  const swarasBody = $('swaras-table-body');
  if (swarasBody && STATE.swaras.length) {
    swarasBody.innerHTML = STATE.swaras.map(s => `
      <tr>
        <td style="font-family:var(--font-mono); font-weight:700; color:var(--gold)">${s.swara}</td>
        <td>${s.name}</td>
        <td style="font-family:var(--font-mono)">${s.cents_12tet}</td>
        <td style="font-family:var(--font-mono)">${s.ratio_5limit || '—'}</td>
        <td style="color:var(--text-muted)">${s.western_interval || ''}</td>
      </tr>
    `).join('');
  }
}

// -------------------------------------------------------------
// CONTACT & FEEDBACK
// -------------------------------------------------------------
async function handleContactSubmit(e) {
  e.preventDefault();
  const name = $('contact-name').value.trim();
  const email = $('contact-email').value.trim();
  const role = $('contact-role').value;
  const message = $('contact-msg').value.trim();

  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, role, message })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.error || 'Submission failed');
    showToast(d.message);
    e.target.reset();
  } catch (err) {
    showToast(err.message, 'err');
  }
}

async function handleFeedbackSubmit(rating) {
  const feedback = $('feedback-text').value.trim();
  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating, feedback })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.error || 'Feedback submission failed');
    showToast(d.message);
    $('feedback-text').value = '';
  } catch (err) {
    showToast(err.message, 'err');
  }
}

function exportAnalysisJSON() {
  if (!STATE.activeAnalysis) {
    showToast('No active analysis to export', 'warn');
    return;
  }
  const blob = new Blob([JSON.stringify(STATE.activeAnalysis, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const raga = STATE.activeAnalysis.classification?.predicted || 'raga';
  a.download = `varnami_${raga.toLowerCase()}_analysis.json`;
  a.click();
  showToast('Analysis exported as JSON!');
}

function exportLibraryBackup() {
  const blob = new Blob([JSON.stringify(STATE.library, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `varnami_library_backup_${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  showToast('Library backup downloaded!');
}

function playSwaraTone(semitone) {
  try {
    if (!STATE.audioCtx) STATE.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (STATE.audioCtx.state === 'suspended') STATE.audioCtx.resume();
    const tonic = parseFloat($('modal-tonic-select')?.value || 146.83);
    const freq = tonic * Math.pow(2, semitone / 12);
    const osc = STATE.audioCtx.createOscillator();
    const gain = STATE.audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, STATE.audioCtx.currentTime);
    gain.gain.setValueAtTime(0.25, STATE.audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, STATE.audioCtx.currentTime + 0.6);
    osc.connect(gain);
    gain.connect(STATE.audioCtx.destination);
    osc.start();
    osc.stop(STATE.audioCtx.currentTime + 0.6);
  } catch(e) {
    console.error('Audio play error:', e);
  }
}

// -------------------------------------------------------------
// EVENT LISTENERS & INITIALIZATION
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  initUser();
  initLibrary();
  loadInitialData();

  // Navigation clicks
  $$('.nav-btn, [data-page]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const page = el.dataset.page;
      if (page) showPage(page);
    });
  });

  // Mobile menu toggle
  $('mobile-menu-btn')?.addEventListener('click', () => {
    $('nav-links').classList.toggle('mobile-open');
  });

  // Blend slider label update
  $('composer-blend')?.addEventListener('input', (e) => {
    $('composer-blend-val').textContent = `${e.target.value}%`;
  });

  // Composer Raga selects
  $('composer-raga-a')?.addEventListener('change', updateComposerCompatibility);
  $('composer-raga-b')?.addEventListener('change', updateComposerCompatibility);

  // Contact form
  $('contact-form')?.addEventListener('submit', handleContactSubmit);

  // Drag and drop setup for file dropzones
  ['carnatic-dropzone', 'cine-dropzone'].forEach(id => {
    const dz = $(id);
    if (!dz) return;
    dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
    dz.addEventListener('drop', (e) => {
      e.preventDefault();
      dz.classList.remove('dragover');
      const input = dz.querySelector('input[type="file"]');
      if (e.dataTransfer.files.length && input) {
        input.files = e.dataTransfer.files;
        showToast(`Selected file: ${e.dataTransfer.files[0].name}`);
      }
    });
  });

  // Check URL hash for initial page
  const hash = window.location.hash.replace('#', '');
  if (hash) showPage(hash);
});
