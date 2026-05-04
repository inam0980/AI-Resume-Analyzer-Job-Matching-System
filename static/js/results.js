(function () {
  // ── Score circle animation ──
  var scoreCircle = document.getElementById('scoreCircle');
  var scoreEl     = document.getElementById('scoreNumber');
  var scoreFill   = document.getElementById('scoreFill');
  if (!scoreCircle) return;

  var score = parseFloat(scoreCircle.dataset.score) || 0;
  var circumference = 2 * Math.PI * 80;

  // Inject SVG gradient
  var svg = document.querySelector('.score-svg');
  if (svg) {
    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML =
      '<linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">' +
        '<stop offset="0%"   style="stop-color:#6366f1"/>' +
        '<stop offset="100%" style="stop-color:#8b5cf6"/>' +
      '</linearGradient>';
    svg.prepend(defs);
    if (scoreFill) scoreFill.setAttribute('stroke', 'url(#scoreGradient)');
  }

  var duration = 1600;
  var startTime = null;
  function animateScore(ts) {
    if (!startTime) startTime = ts;
    var p = Math.min((ts - startTime) / duration, 1);
    var eased = 1 - Math.pow(1 - p, 3);
    if (scoreEl) scoreEl.textContent = (Math.round(eased * score * 10) / 10);
    if (scoreFill) scoreFill.style.strokeDashoffset = circumference - (eased * score / 100) * circumference;
    if (p < 1) { requestAnimationFrame(animateScore); }
    else if (scoreEl) { scoreEl.textContent = score; }
  }
  setTimeout(function() { requestAnimationFrame(animateScore); }, 200);

  // ── Breakdown bars ──
  function animateBars(selector, attr, delay) {
    delay = delay || 400;
    document.querySelectorAll(selector).forEach(function(bar) {
      var pct = parseFloat(bar.dataset[attr] || bar.getAttribute('data-pct')) || 0;
      bar.style.width = '0%';
      setTimeout(function() { bar.style.width = Math.min(100, pct) + '%'; }, delay);
    });
  }
  animateBars('.breakdown-bar', 'pct', 400);
  animateBars('.section-bar',   'pct', 600);

  // ── SHAP bars ──
  document.querySelectorAll('.shap-bar').forEach(function(bar, i) {
    var impact   = Math.abs(parseFloat(bar.dataset.impact) || 0);
    var maxPx    = (bar.closest('.shap-bar-wrap') || {}).clientWidth || 160;
    var targetPx = Math.max(4, Math.min(maxPx, impact * 500));
    bar.style.width = '0px';
    setTimeout(function() { bar.style.width = targetPx + 'px'; }, 700 + i * 40);
  });

  // ── Skill tag entrance ──
  document.querySelectorAll('.skill-tag').forEach(function(tag, i) {
    tag.style.opacity   = '0';
    tag.style.transform = 'translateY(6px)';
    tag.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    setTimeout(function() {
      tag.style.opacity   = '1';
      tag.style.transform = 'translateY(0)';
    }, 150 + i * 30);
  });

  // ── Recommendation entrance ──
  document.querySelectorAll('.rec-item').forEach(function(item, i) {
    item.style.opacity   = '0';
    item.style.transform = 'translateX(-10px)';
    item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    setTimeout(function() {
      item.style.opacity   = '1';
      item.style.transform = 'translateX(0)';
    }, 600 + i * 80);
  });
})();
