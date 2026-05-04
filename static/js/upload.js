// Tab switching
document.querySelectorAll('.tab-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
    btn.classList.add('active');
    var tab = document.getElementById('tab-' + btn.dataset.tab);
    if (tab) tab.classList.add('active');
  });
});

// Drag & Drop setup
function setupDropZone(zoneId, inputId, previewId, nameId) {
  var zone = document.getElementById(zoneId);
  var input = document.getElementById(inputId);
  if (!zone || !input) return;

  ['dragenter', 'dragover'].forEach(function(e) {
    zone.addEventListener(e, function(ev) { ev.preventDefault(); zone.classList.add('drag-over'); });
  });
  ['dragleave', 'drop'].forEach(function(e) {
    zone.addEventListener(e, function(ev) { ev.preventDefault(); zone.classList.remove('drag-over'); });
  });
  zone.addEventListener('drop', function(ev) {
    if (ev.dataTransfer.files.length) {
      input.files = ev.dataTransfer.files;
      showFilePreview(previewId, nameId, ev.dataTransfer.files[0].name);
    }
  });
  input.addEventListener('change', function() {
    if (input.files.length) showFilePreview(previewId, nameId, input.files[0].name);
  });
}

function showFilePreview(previewId, nameId, filename) {
  var preview = document.getElementById(previewId);
  var nameEl  = document.getElementById(nameId);
  if (preview) preview.classList.remove('hidden');
  if (nameEl)  nameEl.textContent = filename;
}

setupDropZone('resumeDropZone', 'resumeFile', 'resumePreview', 'resumeFileName');
setupDropZone('jdDropZone',     'jdFile',     'jdPreview',     'jdFileName');

// Character counter
var jdTextarea = document.getElementById('jdText');
var charCount  = document.getElementById('charCount');
if (jdTextarea && charCount) {
  jdTextarea.addEventListener('input', function() { charCount.textContent = jdTextarea.value.length; });
}

// Clear file
function clearFile(type) {
  if (type === 'resume') {
    document.getElementById('resumeFile').value = '';
    document.getElementById('resumePreview').classList.add('hidden');
  } else {
    document.getElementById('jdFile').value = '';
    document.getElementById('jdPreview').classList.add('hidden');
  }
}

// Progress steps
var STEPS = [
  'Extracting text from documents...',
  'Loading BERT model...',
  'Computing semantic embeddings...',
  'Running FAISS similarity search...',
  'Analyzing skill gaps...',
  'Generating SHAP explanations...',
  'Building recommendations...',
  'Finalizing results...',
];

function setStep(text, pct) {
  var stepEl = document.getElementById('progressStep');
  var pctEl  = document.getElementById('progressPct');
  var barEl  = document.getElementById('progressBar');
  if (stepEl) stepEl.textContent = text;
  if (pctEl)  pctEl.textContent  = pct + '%';
  if (barEl)  barEl.style.width  = pct + '%';
}

function showOverlay() {
  var overlay = document.getElementById('progressOverlay');
  if (overlay) overlay.classList.add('active');
}

function hideOverlay() {
  var overlay = document.getElementById('progressOverlay');
  if (overlay) overlay.classList.remove('active');
}

function showError(msg) {
  var el = document.getElementById('errorAlert');
  if (!el) { alert(msg); return; }
  el.textContent = msg;
  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  var el = document.getElementById('errorAlert');
  if (el) el.classList.add('hidden');
}

function getCsrf() {
  var name = 'csrftoken';
  var cookies = document.cookie.split(';');
  for (var i = 0; i < cookies.length; i++) {
    var c = cookies[i].trim();
    if (c.startsWith(name + '=')) return c.substring(name.length + 1);
  }
  return '';
}

// Main function — global so onclick="startAnalysis()" works
function startAnalysis() {
  hideError();

  var resumeInput = document.getElementById('resumeFile');
  var jdInput     = document.getElementById('jdText');
  var jdFileInput = document.getElementById('jdFile');
  var btn         = document.getElementById('analyzeBtn');
  var btnText     = document.getElementById('btnText');
  var btnIcon     = document.getElementById('btnIcon');

  // Validate resume
  if (!resumeInput || !resumeInput.files || resumeInput.files.length === 0) {
    showError('Please upload your resume file (PDF or DOCX).');
    return;
  }

  // Which JD tab is active?
  var activeTabBtn = document.querySelector('.tab-btn.active');
  var activeTab    = activeTabBtn ? activeTabBtn.dataset.tab : 'paste';

  if (activeTab === 'paste') {
    var jdVal = jdInput ? jdInput.value.trim() : '';
    if (jdVal.length < 50) {
      showError('Please paste a job description (at least 50 characters).');
      return;
    }
  } else {
    if (!jdFileInput || !jdFileInput.files || jdFileInput.files.length === 0) {
      showError('Please upload a job description file.');
      return;
    }
  }

  // Show loading state
  showOverlay();
  if (btn)     btn.disabled     = true;
  if (btnText) btnText.textContent = 'Analyzing...';
  if (btnIcon) btnIcon.textContent = '⏳';
  setStep(STEPS[0], 0);

  // Animate steps
  var stepIndex = 0;
  var stepTimer = setInterval(function() {
    stepIndex++;
    if (stepIndex < STEPS.length) {
      var pct = Math.round((stepIndex / STEPS.length) * 90);
      setStep(STEPS[stepIndex], pct);
    } else {
      clearInterval(stepTimer);
    }
  }, 2500);

  // Build form data
  var fd = new FormData();
  fd.append('file', resumeInput.files[0]);

  var titleEl = document.getElementById('jdTitle');
  fd.append('title', titleEl ? titleEl.value : '');

  if (activeTab === 'paste') {
    fd.append('text', jdInput.value);
  } else {
    fd.append('text', ' ');
    fd.append('jd_file', jdFileInput.files[0]);
  }

  // Send request
  fetch('/analyzer/analyze/', {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrf() },
    body: fd,
  })
  .then(function(response) {
    return response.json().then(function(data) {
      return { ok: response.ok, data: data };
    });
  })
  .then(function(result) {
    clearInterval(stepTimer);
    if (!result.ok) {
      throw new Error(result.data.error || 'Server error. Check your inputs and try again.');
    }
    setStep('Done! Redirecting...', 100);
    setTimeout(function() { window.location.href = result.data.redirect; }, 600);
  })
  .catch(function(err) {
    clearInterval(stepTimer);
    hideOverlay();
    if (btn)     btn.disabled     = false;
    if (btnText) btnText.textContent = 'Analyze Match';
    if (btnIcon) btnIcon.textContent = '🔍';
    showError(err.message || 'Something went wrong. Please try again.');
  });
}
