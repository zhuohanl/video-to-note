/* editor.js — Video-Note timeline editor (Clipchamp-style) */
(function () {
  lucide.createIcons();

  var TOTAL = 1880; // 31:20
  var uid = 0;
  var pps = 0;            // px per second (set on layout)
  var zoom = 1;
  var playhead = 0;       // seconds

  function fmt(s) { s = Math.max(0, Math.round(s)); var m = Math.floor(s / 60), x = s % 60; return m + ':' + (x < 10 ? '0' : '') + x; }
  function fmt2(s) { s = Math.max(0, s); var m = Math.floor(s / 60), x = s % 60; return m + ':' + (x < 10 ? '0' : '') + x.toFixed(2); }
  function splitSentences(t) { var p = t.match(/[^.!?]+[.!?]+(\s|$)/g); return p ? p.map(function (x) { return x.trim(); }) : [t]; }

  var clips = [
    { id: ++uid, start: 0, end: 252, title: 'Opening & session goals',
      transcript: "Welcome everyone. Today we ship a working AI app to Azure by the end of this session. We will keep it practical and code-first. Expect a live demo rather than slides, and you will leave with a deployable pattern you can reuse.",
      summary: "The speaker frames the session around shipping a working AI app to Azure by the end, and sets expectations for a practical, demo-led talk." },
    { id: ++uid, start: 252, end: 760, title: 'Architecture overview',
      transcript: "The system is a pipeline of small services. Each model sits behind a provider adapter so it stays swappable. Work is queued per stage and streamed to the client as it completes. The orchestration layer never holds vendor specifics, which keeps the whole thing portable.",
      summary: "The system is organized as a pipeline of small services behind provider adapters, so models stay swappable and work streams to the client per stage." },
    { id: ++uid, start: 760, end: 1445, title: 'Live demo: deploy worker',
      transcript: "Let's deploy. I run azd up to provision and deploy in one step. Notice the container app spins up behind a managed identity, so there are no secrets in the repo. Deployment finishes in about three minutes and the worker is reachable immediately, with logs streaming to the console.",
      summary: "A live azd up provisions and deploys in one step behind a managed identity; the worker is reachable in about three minutes with streaming logs." },
    { id: ++uid, start: 1445, end: 1880, title: 'Q&A',
      transcript: "Questions. How do we control cost? Use the soft ceiling and per-job estimate. Can the worker scale horizontally? Yes, it is stateless behind the queue. And can I run the whole stack locally? Yes, with the dev container.",
      summary: "Audience Q&A covers cost controls, horizontal scaling of the stateless worker, and running the full stack locally." }
  ];

  // selection: an ordered list of selected clip ids; anchor for shift-range
  var selectedIds = [clips[0].id];
  var anchorId = clips[0].id;
  var pickerOpen = false;
  // each clip carries a default screenshot timestamp (40% into the clip)
  clips.forEach(function (c) { c.shotAt = Math.round(c.start + (c.end - c.start) * 0.4); });

  // Pipeline loading state — play the "build the editor" sequence when arriving
  // fresh from Submit (?run=1); otherwise open ready.
  var preparing = /[?&]run=1/.test(location.search);
  var pipelineDone = !preparing;
  clips.forEach(function (c) { c.drafted = !preparing; });
  function shotBg(c) { return /demo|Q&A/.test(c.title) ? 'linear-gradient(180deg,#4a5263,#363d4b)' : 'linear-gradient(180deg,#3f6fc4,#2c5099)'; }

  var el = {
    canvas: document.getElementById('tlCanvas'),
    ruler: document.getElementById('tlRuler'),
    laneSeg: document.getElementById('laneSeg'),
    laneShot: document.getElementById('laneShot'),
    laneTx: document.getElementById('laneTx'),
    laneSum: document.getElementById('laneSum'),
    playhead: document.getElementById('tlPlayhead'),
    scroll: document.getElementById('tlScroll'),
    inspector: document.getElementById('inspector'),
    tpTime: document.getElementById('tpTime'),
    nowClip: document.getElementById('nowClip'),
    splitBtn: document.getElementById('splitBtn'),
    mergeBtn: document.getElementById('mergeBtn'),
    hint: document.getElementById('tlHint'),
    hover: document.getElementById('tlHover'),
    save: document.getElementById('saveStatus')
  };

  function byId(id) { return clips.filter(function (c) { return c.id === id; })[0]; }
  function isSel(id) { return selectedIds.indexOf(id) >= 0; }
  function primaryId() { return selectedIds[selectedIds.length - 1]; }
  function idxOf(id) { return clips.findIndex(function (c) { return c.id === id; }); }
  // selected clips in timeline order
  function selectedOrdered() { return clips.filter(function (c) { return isSel(c.id); }); }
  function selectionConsecutive() {
    var idxs = selectedIds.map(idxOf).sort(function (a, b) { return a - b; });
    return idxs.length >= 2 && (idxs[idxs.length - 1] - idxs[0] === idxs.length - 1);
  }

  function layout() {
    var w = el.scroll.clientWidth;
    // a minimum scale so long videos extend past the viewport and scroll horizontally
    var MIN_PPS = 1.0;
    pps = Math.max(w / TOTAL, MIN_PPS) * zoom;
    var cw = Math.max(w, TOTAL * pps);
    el.canvas.style.width = cw + 'px';
    // force every lane + ruler to the full timeline width (some shrink under flex)
    [el.ruler, el.laneShot, el.laneSeg, el.laneTx, el.laneSum].forEach(function (L) {
      if (L) { L.style.width = cw + 'px'; L.style.minWidth = cw + 'px'; L.style.flex = 'none'; }
    });
  }

  function render() {
    layout();
    var ticks = '';
    for (var t = 0; t <= TOTAL; t += 120) ticks += '<div class="tl-tick" style="left:' + (t * pps) + 'px"><span>' + fmt(t) + '</span></div>';
    el.ruler.innerHTML = ticks;

    var darkFilm = '<span class="f" style="background:#1b1b1b"></span>';
    var blueFilm = '<span class="f" style="background:linear-gradient(135deg,#243b66,#2E5AAC)"></span>';
    el.laneShot.innerHTML = clips.map(function (c) {
      var clipW = (c.end - c.start) * pps;
      var thumbW = Math.min(84, Math.max(26, clipW - 4));
      var left = Math.max(c.start * pps, Math.min(c.shotAt * pps - thumbW / 2, c.end * pps - thumbW));
      return '<div class="shot-cell' + (isSel(c.id) ? ' sel' : '') + '" data-seg="' + c.id + '" style="left:' + left + 'px;width:' + thumbW + 'px">' +
        '<div class="shot-fill" style="background:' + shotBg(c) + '"></div>' +
        '<span class="ic"><i data-lucide="image"></i></span><span class="st">' + fmt(c.shotAt) + '</span></div>';
    }).join('');
    el.laneSeg.innerHTML = clips.map(function (c, i) {
      var dark = /demo|Q&A/.test(c.title);
      var n = Math.max(3, Math.round((c.end - c.start) * pps / 46));
      var film = ''; for (var k = 0; k < n; k++) film += dark ? darkFilm : blueFilm;
      return '<div class="seg-block' + (isSel(c.id) ? ' sel' : '') + '" data-seg="' + c.id + '" style="left:' + (c.start * pps) + 'px;width:' + ((c.end - c.start) * pps) + 'px">' +
        '<span class="seg-no">' + String(i + 1).padStart(2, '0') + '</span>' +
        '<span class="handle l"></span><div class="film">' + film + '</div><span class="handle r"></span></div>';
    }).join('');

    el.laneTx.innerHTML = clips.map(function (c) {
      return '<div class="lane-cell' + (isSel(c.id) ? ' sel' : '') + '" data-seg="' + c.id + '" style="left:' + (c.start * pps) + 'px;width:' + ((c.end - c.start) * pps - 4) + 'px">' + esc(c.transcript) + '</div>';
    }).join('');
    el.laneSum.innerHTML = clips.map(function (c) {
      if (!c.drafted) return '<div class="lane-cell sum-skel" data-seg="' + c.id + '" style="left:' + (c.start * pps) + 'px;width:' + ((c.end - c.start) * pps - 4) + 'px"><span class="sk"></span><span class="sk"></span></div>';
      var edited = c.aiSummary !== undefined && c.summary.trim() !== c.aiSummary.trim();
      return '<div class="lane-cell' + (isSel(c.id) ? ' sel' : '') + (edited ? ' edited' : '') + '" data-seg="' + c.id + '" style="left:' + (c.start * pps) + 'px;width:' + ((c.end - c.start) * pps - 4) + 'px">' + esc(c.summary) + '</div>';
    }).join('');

    positionPlayhead();
    renderInspector();
    el.splitBtn.disabled = !pipelineDone || selectedIds.length > 1;
    el.mergeBtn.disabled = !pipelineDone || !selectionConsecutive();
    if (el.setSceneBtn) el.setSceneBtn.disabled = !pipelineDone;
    el.hint.textContent = !pipelineDone
      ? 'Editing unlocks when drafting finishes — you can scrub and read ready clips now.'
      : (selectedIds.length > 1
        ? selectedIds.length + ' clips selected — click Merge to combine them.'
        : 'Click the timeline to move the playhead; Split cuts there. Shift-click clips to select a range to Merge.');
    lucide.createIcons();
  }

  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
  function candidatesHTML(c) {
    var cands = [0.12, 0.35, 0.6, 0.85].map(function (f) { return Math.round(c.start + (c.end - c.start) * f); });
    return '<div class="shot-candidates"><div class="scc-lbl">Pick a different frame from this clip:</div><div class="scc-grid">' +
      cands.map(function (t) {
        return '<div class="scc' + (Math.abs(t - c.shotAt) < 2 ? ' cur' : '') + '" data-shotat="' + t + '" style="background:' + shotBg(c) + '"><span class="st">' + fmt(t) + '</span></div>';
      }).join('') + '</div></div>';
  }

  function positionPlayhead() {
    el.playhead.style.left = (playhead * pps) + 'px';
    el.tpTime.textContent = fmt(playhead) + ' / ' + fmt(TOTAL);
    var c = clips.filter(function (x) { return playhead >= x.start && playhead < x.end; })[0] || clips[0];
    el.nowClip.textContent = String(clips.indexOf(c) + 1).padStart(2, '0') + ' · ' + c.title;
  }

  function renderInspector() {
    // multi-select → merge panel
    if (selectedIds.length > 1) {
      var grp = selectedOrdered();
      var ok = selectionConsecutive();
      el.inspector.innerHTML =
        '<div class="insp-head"><div class="insp-eyebrow"><span class="insp-n">' + grp.length + ' clips</span>' +
          '<span class="insp-range">' + fmt(grp[0].start) + '–' + fmt(grp[grp.length - 1].end) + '</span></div>' +
          '<div class="insp-title" style="pointer-events:none">' + (ok ? 'Merge selected clips' : 'Selection not consecutive') + '</div></div>' +
        '<div class="insp-body">' +
          '<div class="insp-block"><div class="lbl"><i data-lucide="combine"></i>Clips to merge</div>' +
            '<div class="merge-list">' + grp.map(function (c) {
              return '<div class="merge-item"><span class="mi-n">' + String(clips.indexOf(c) + 1).padStart(2, '0') + '</span><span class="mi-t">' + esc(c.title) + '</span><span class="mi-r mono">' + fmt(c.start) + '–' + fmt(c.end) + '</span></div>';
            }).join('') + '</div></div>' +
          '<p class="insp-hint" style="line-height:1.5">' + (ok
            ? 'Transcript and summary tracks will be joined in order into one clip. The merged summary is flagged so you can regenerate it to fit.'
            : 'Select clips that sit next to each other on the timeline — gaps can’t be merged.') + '</p>' +
          '<div class="merge-actions"><button class="btn ghost sm" id="inspClear">Clear selection</button>' +
            '<button class="btn primary sm" id="inspMerge"' + (ok ? '' : ' disabled') + '><i data-lucide="combine"></i>Merge ' + grp.length + ' clips</button></div>' +
        '</div>';
      lucide.createIcons();
      return;
    }
    var c = byId(primaryId()); if (!c) return;
    var i = clips.indexOf(c);
    var edited = c.aiSummary !== undefined && c.summary.trim() !== c.aiSummary.trim();
    el.inspector.innerHTML =
      '<div class="insp-head">' +
        '<div class="insp-eyebrow"><span class="insp-n">' + String(i + 1).padStart(2, '0') + '</span>' +
        '<span class="insp-range">' + fmt(c.start) + '–' + fmt(c.end) + ' · ' + fmt(c.end - c.start) + '</span></div>' +
        '<input class="insp-title" id="inspTitle" value="' + c.title.replace(/"/g, '&quot;') + '" />' +
      '</div>' +
      '<div class="insp-body">' +
        '<div class="insp-flag' + (c.flagged ? ' show' : '') + '"><i data-lucide="triangle-alert"></i>Boundaries changed — regenerate the summary to fit.<button class="regen" id="inspRegen"><i data-lucide="refresh-cw"></i>Regenerate</button></div>' +
        '<div class="insp-block"><div class="lbl"><i data-lucide="image"></i>Screenshot</div>' +
          '<div class="insp-shot-frame" style="background:' + shotBg(c) + '"><span class="st">' + fmt(c.shotAt) + '</span></div>' +
          '<div class="insp-shot-foot"><span class="shot-caption">Move the playhead over this clip and click <b>Set scene</b> on the timeline to change it.</span></div>' +
        '</div>' +
        '<div class="insp-block"><div class="lbl"><i data-lucide="captions"></i>Transcript</div><div class="insp-transcript">' + esc(c.transcript) + '</div></div>' +
        (!c.drafted
          ? '<div class="insp-block"><div class="lbl"><i data-lucide="loader" class="spin"></i>Summary / your notes</div>' +
              '<div class="insp-summary is-drafting"><span class="sk"></span><span class="sk"></span><span class="sk short"></span></div>' +
              '<div class="insp-sumfoot"><span class="insp-hint">Drafting this section\u2026 you can edit it once it appears.</span></div></div>'
          : '<div class="insp-block' + (edited ? ' edited' : '') + '"><div class="lbl"><i data-lucide="pencil-line"></i>Summary / your notes' + (edited ? '<span class="edited-tag">your edit</span>' : '<span class="edit-badge">editable</span>') + '</div>' +
          '<div class="insp-summary" id="inspSummary" contenteditable="true" spellcheck="false" data-ph="Write your own notes, or edit the AI summary…">' + esc(c.summary) + '</div>' +
          '<div class="insp-sumfoot"><button class="insp-restore" id="inspRestore"><i data-lucide="rotate-ccw"></i>Restore AI summary</button>' +
          (edited ? '' : '<span class="insp-hint"><i data-lucide="pencil" style="width:12px;height:12px;vertical-align:-1px"></i> Click to overwrite with your own words — restore anytime.</span>') + '</div>' +
        '</div>') +
      '</div>';
    lucide.createIcons();
  }

  /* ---------- inspector events ---------- */
  el.inspector.addEventListener('input', function (e) {
    var c = byId(primaryId()); if (!c) return;
    if (e.target.id === 'inspTitle') { c.title = e.target.value; positionPlayhead(); renderSumLaneOnly(); flash('Saved'); }
    if (e.target.id === 'inspSummary') {
      if (c.aiSummary === undefined) c.aiSummary = c.summary;
      c.summary = e.target.textContent;
      var edited = c.summary.trim() !== c.aiSummary.trim();
      e.target.closest('.insp-block').classList.toggle('edited', edited);
      renderSumLaneOnly();
      if (notePolished()) markClipsChanged();
      flash('Saved');
    }
  });
  el.inspector.addEventListener('click', function (e) {
    if (e.target.closest('#inspRestore')) { var c = byId(primaryId()); if (c && c.aiSummary !== undefined) { c.summary = c.aiSummary; render(); flash('Restored AI summary'); } }
    if (e.target.closest('#inspRegen')) { var c2 = byId(primaryId()); if (c2) { c2.flagged = false; render(); flash('Summary regenerated'); } }
    if (e.target.closest('#inspMerge')) { mergeSelected(); }
    if (e.target.closest('#inspClear')) { selectedIds = [primaryId()]; anchorId = primaryId(); render(); }
    if (e.target.closest('#shotRescan')) { pickerOpen = !pickerOpen; renderInspector(); }
    var sc = e.target.closest('[data-shotat]');
    if (sc) { var c3 = byId(primaryId()); if (c3) { c3.shotAt = +sc.dataset.shotat; pickerOpen = false; render(); flash('Screenshot updated to ' + fmt(c3.shotAt)); } }
  });
  function renderSumLaneOnly() {
    var c = byId(primaryId()); if (!c) return;
    var cell = el.laneSum.querySelector('[data-seg="' + c.id + '"]');
    if (cell) { cell.textContent = c.summary; cell.classList.toggle('edited', c.aiSummary !== undefined && c.summary.trim() !== c.aiSummary.trim()); }
  }

  /* ---------- timeline click: place playhead + select (shift = range) ---------- */
  el.canvas.addEventListener('click', function (e) {
    pickerOpen = false;
    var seg = e.target.closest('[data-seg]');
    if ((e.shiftKey || e.metaKey || e.ctrlKey) && seg) {
      var clicked = idxOf(+seg.dataset.seg);
      var anchor = idxOf(anchorId); if (anchor < 0) anchor = clicked;
      var lo = Math.min(anchor, clicked), hi = Math.max(anchor, clicked);
      selectedIds = clips.slice(lo, hi + 1).map(function (c) { return c.id; });
      render();
      return;
    }
    var r = el.canvas.getBoundingClientRect();
    playhead = Math.max(0, Math.min(TOTAL, (e.clientX - r.left) / pps));
    var c = clips.filter(function (x) { return playhead >= x.start && playhead < x.end; })[0];
    if (c) { selectedIds = [c.id]; anchorId = c.id; }
    render();
  });

  /* ---------- drag playhead ---------- */  el.playhead.style.pointerEvents = 'auto';
  el.playhead.addEventListener('mousedown', function (ev) {
    ev.preventDefault();
    function move(e) {
      var r = el.canvas.getBoundingClientRect();
      playhead = Math.max(0, Math.min(TOTAL, (e.clientX - r.left) / pps));
      positionPlayhead();
    }
    function up() { document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up); }
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up);
  });

  /* ---------- hover scrubline with precise timestamp ---------- */
  el.scroll.addEventListener('mousemove', function (e) {
    var r = el.canvas.getBoundingClientRect();
    var x = e.clientX - r.left;
    if (x < 0 || x > r.width) { el.hover.style.display = 'none'; return; }
    el.hover.style.display = 'block';
    el.hover.style.left = x + 'px';
    el.hover.firstChild.textContent = fmt2(x / pps);
  });
  el.scroll.addEventListener('mouseleave', function () { el.hover.style.display = 'none'; });

  /* ---------- scissors split (cuts at the playhead) ---------- */
  el.splitBtn.addEventListener('click', function () {
    var c = clips.filter(function (x) { return playhead > x.start && playhead < x.end; })[0];
    if (!c || playhead <= c.start + 1 || playhead >= c.end - 1) { flash('Move the playhead inside a clip first'); return; }
    withRebuildGuard(function () { doSplit(c, playhead); });
  });
  function doSplit(c, at) {
    var frac = (at - c.start) / (c.end - c.start);
    var words = c.transcript.split(/\s+/);
    var wi = Math.max(1, Math.round(words.length * frac));
    var tx1 = words.slice(0, wi).join(' '), tx2 = words.slice(wi).join(' ');
    var sents = splitSentences(c.summary);
    var half = Math.max(1, Math.ceil(sents.length / 2));
    var sum1 = sents.slice(0, half).join(' ');
    var sum2 = sents.slice(half).join(' ') || 'New section — regenerate or write a summary.';
    var c2 = { id: ++uid, start: at, end: c.end, title: c.title + ' (cont.)', transcript: tx2, summary: sum2, flagged: true };
    c2.shotAt = Math.round(at + (c2.end - at) * 0.4);
    c.end = at; c.transcript = tx1; c.summary = sum1; c.flagged = true;
    if (c.shotAt >= at) c.shotAt = Math.round(c.start + (at - c.start) * 0.4);
    clips.splice(clips.indexOf(c) + 1, 0, c2);
    selectedIds = [c2.id]; anchorId = c2.id; playhead = c2.start;
    render(); flash('Clip split at ' + fmt(at));
  }

  /* ---------- merge selected consecutive clips ---------- */
  el.mergeBtn.addEventListener('click', mergeSelected);
  function mergeSelected() {
    if (!selectionConsecutive()) { flash('Select 2+ consecutive clips'); return; }
    withRebuildGuard(doMerge);
  }
  function doMerge() {
    var grp = selectedOrdered();
    var first = grp[0];
    first.end = grp[grp.length - 1].end;
    first.transcript = grp.map(function (g) { return g.transcript; }).join(' ');
    first.summary = grp.map(function (g) { return g.summary; }).join(' ');
    if (grp.some(function (g) { return g.aiSummary !== undefined; })) first.aiSummary = grp.map(function (g) { return g.aiSummary || g.summary; }).join(' ');
    first.title = first.title.replace(/ \(cont\.\)$/, '');
    first.flagged = true;
    var rest = grp.slice(1);
    clips = clips.filter(function (c) { return rest.indexOf(c) < 0; });
    selectedIds = [first.id]; anchorId = first.id; playhead = first.start;
    render(); flash(grp.length + ' clips merged');
  }

  /* ---------- set screenshot to the frame at the playhead ---------- */
  el.setSceneBtn = document.getElementById('setSceneBtn');
  el.setSceneBtn.addEventListener('click', function () {
    var c = clips.filter(function (x) { return playhead >= x.start && playhead < x.end; })[0];
    if (!c) { flash('Move the playhead onto a clip first'); return; }
    withRebuildGuard(function () {
      selectedIds = [c.id]; anchorId = c.id;
      c.shotAt = Math.round(playhead);
      render(); flash('Scene set to ' + fmt(c.shotAt));
    });
  });

  /* ---------- zoom ---------- */
  document.getElementById('zoomIn').addEventListener('click', function () { zoom = Math.min(6, zoom * 1.5); render(); });
  document.getElementById('zoomOut').addEventListener('click', function () { zoom = Math.max(1, zoom / 1.5); render(); });
  document.getElementById('zoomFit').addEventListener('click', function () { zoom = 1; render(); });
  window.addEventListener('resize', render);

  /* ---------- save status ---------- */
  var st;
  function flash(msg) {
    if (!el.save) return;
    clearTimeout(st);
    el.save.innerHTML = '<i data-lucide="loader" style="width:14px;height:14px;"></i>' + msg;
    el.save.className = 'chip outline mono'; lucide.createIcons();
    st = setTimeout(function () { el.save.innerHTML = '<i data-lucide="check"></i>Saved'; el.save.className = 'chip ok'; lucide.createIcons(); }, 1100);
  }

  /* ---------- "polished note will refresh" guard ---------- */
  // If the user has already polished the assembled note (set on the Review page),
  // changing clips here means that note must be rebuilt to match. Warn once,
  // up front, in plain language; then keep a quiet reminder. A saved copy of the
  // note is always kept on the Review page, so nothing is ever lost.
  var changeAcknowledged = false;
  function notePolished() { try { return localStorage.getItem('vtn_notePolished') === '1'; } catch (e) { return false; } }
  function markClipsChanged() { try { localStorage.setItem('vtn_clipsChanged', '1'); } catch (e) {} showChangeChip(); }
  function showChangeChip() {
    var chip = document.getElementById('refreshChip');
    if (chip) chip.style.display = 'inline-flex';
  }
  function withRebuildGuard(proceed) {
    if (!notePolished() || changeAcknowledged) {
      if (notePolished()) markClipsChanged();
      proceed();
      return;
    }
    openHeadsUp(function () {
      changeAcknowledged = true;
      markClipsChanged();
      proceed();
    });
  }
  function openHeadsUp(onConfirm) {
    var ov = document.createElement('div');
    ov.className = 'ed-modal-ov';
    ov.innerHTML =
      '<div class="ed-modal">' +
        '<div class="em-icon"><i data-lucide="info"></i></div>' +
        '<h3>You\u2019ve polished your note</h3>' +
        '<p>Changing clips here will refresh the note to match. We\u2019ll keep a saved copy you can restore anytime.</p>' +
        '<div class="em-actions"><button class="btn ghost" data-cancel>Cancel</button><button class="btn primary" data-go>Keep editing</button></div>' +
      '</div>';
    document.body.appendChild(ov);
    lucide.createIcons();
    function close() { ov.remove(); }
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    ov.querySelector('[data-cancel]').addEventListener('click', close);
    ov.querySelector('[data-go]').addEventListener('click', function () { close(); onConfirm(); });
  }
  (function () {
    try { if (localStorage.getItem('vtn_clipsChanged') === '1' && notePolished()) { changeAcknowledged = true; showChangeChip(); } } catch (e) {}
  })();

  (function pipeline() {
    if (!preparing) { render(); return; }

    // build the stage strip (matches the Processing design) + a veil over the lanes
    var strip = document.createElement('div');
    strip.className = 'ed-progress'; strip.id = 'edProgress';
    strip.innerHTML =
      '<div class="ep-head"><span class="ep-eyebrow">Processing</span>' +
        '<button class="ep-skip" id="epSkip">Skip to editor <i data-lucide="chevron-right"></i></button></div>' +
      '<div class="ep-rail" id="epRail"></div>' +
      '<div class="ep-foot"><div class="ep-bar"><span id="epBarFill"></span></div>' +
        '<span class="ep-count" id="epCount">Starting…</span><span class="ep-eta" id="epEta"></span></div>';
    document.querySelector('.ed-app').insertBefore(strip, document.querySelector('.ed-top'));

    var veil = document.createElement('div');
    veil.className = 'prep-veil'; veil.id = 'prepVeil';
    veil.innerHTML = '<div class="pv-msg"><i data-lucide="loader" class="spin"></i>Preparing your video…</div>';
    el.scroll.appendChild(veil);
    lucide.createIcons();
    render();

    // the video preview isn't ready until the proxy is acquired — show that honestly
    var screenEl = document.querySelector('.ed-screen');
    var screenReady = screenEl.innerHTML;
    screenEl.classList.add('prep');
    screenEl.innerHTML = '<div class="screen-prep"><i data-lucide="loader" class="spin"></i><span>Preparing video preview…</span></div>';
    lucide.createIcons();

    var stages = ['resolving', 'acquiring', 'analyzing', 'segmenting', 'drafting'];
    var status = { resolving: 'todo', acquiring: 'todo', analyzing: 'todo', segmenting: 'todo', drafting: 'todo' };
    var branch = { transcribe: 'todo', index: 'todo', style: 'todo' };

    function bicon(s) { return s === 'done' ? '<i data-lucide="check"></i>' : s === 'active' ? '<i data-lucide="loader" class="spin"></i>' : ''; }
    function paint() {
      document.getElementById('epRail').innerHTML = stages.map(function (s, i) {
        var st = status[s];
        var node = '<div class="ep-step ' + st + '"><div class="ep-node">' + bicon(st) + '</div>' +
          '<div class="ep-lbl">' + s + '</div>' +
          (s === 'analyzing' ? '<div class="ep-branches">' + ['transcribe', 'index', 'style'].map(function (b) {
            return '<span class="ep-branch ' + branch[b] + (b === 'style' ? ' style' : '') + '">' + (branch[b] === 'done' ? '<i data-lucide="check"></i>' : branch[b] === 'active' ? '<i data-lucide="loader" class="spin"></i>' : '') + b + '</span>';
          }).join('') + '</div>' : '') + '</div>';
        var conn = i < stages.length - 1 ? '<div class="ep-conn ' + (st === 'done' ? 'done' : '') + '"></div>' : '';
        return node + conn;
      }).join('');
      lucide.createIcons();
    }
    function setFoot(done, total, eta) {
      document.getElementById('epBarFill').style.width = (total ? (done / total) * 100 : 8) + '%';
      document.getElementById('epCount').textContent = total ? ('Section ' + done + ' of ' + total) : 'Reading the talk…';
      document.getElementById('epEta').textContent = eta || '';
    }

    var t = 400;
    function at(fn) { setTimeout(fn, t); }
    paint(); setFoot(0, 0, '');
    at(function () { status.resolving = 'active'; paint(); }); t += 650;
    at(function () { status.resolving = 'done'; status.acquiring = 'active'; paint(); setFoot(0, 0, '~25s left'); }); t += 850;
    at(function () { status.acquiring = 'done'; status.analyzing = 'active'; branch.transcribe = 'active'; paint(); screenEl.classList.remove('prep'); screenEl.innerHTML = screenReady; }); t += 600;
    at(function () { branch.transcribe = 'done'; branch.index = 'active'; paint(); }); t += 600;
    at(function () { branch.index = 'done'; branch.style = 'active'; paint(); }); t += 600;
    at(function () { branch.style = 'done'; status.analyzing = 'done'; status.segmenting = 'active'; paint(); setFoot(0, 0, '~12s left'); }); t += 850;
    at(function () {
      status.segmenting = 'done'; status.drafting = 'active'; paint();
      var v = document.getElementById('prepVeil'); if (v) { v.classList.add('lift'); setTimeout(function () { v.remove(); }, 350); }
    }); t += 500;
    var n = clips.length;
    for (var k = 0; k < n; k++) (function (k) {
      at(function () { clips[k].drafted = true; setFoot(k + 1, n, '~' + Math.max(0, (n - k - 1) * 5) + 's left'); render(); }); t += 800;
    })(k);
    at(function () { status.drafting = 'done'; paint(); finish(); }); t += 300;

    function finish() {
      pipelineDone = true; clips.forEach(function (c) { c.drafted = true; });
      var strip = document.getElementById('edProgress');
      if (strip) { strip.classList.add('done'); strip.querySelector('.ep-foot').innerHTML = '<span class="ep-ready"><i data-lucide="check"></i>Ready — your notes are drafted. Edit anything below.</span>'; lucide.createIcons(); }
      render();
      setTimeout(function () { if (strip) strip.classList.add('collapse'); }, 1600);
      setTimeout(function () { if (strip) strip.remove(); }, 2100);
      try { history.replaceState(null, '', location.pathname); } catch (e) {}
    }

    document.getElementById('epSkip').addEventListener('click', function () {
      // jump straight to the finished editor
      t = 0; var v = document.getElementById('prepVeil'); if (v) v.remove();
      status = { resolving: 'done', acquiring: 'done', analyzing: 'done', segmenting: 'done', drafting: 'done' };
      branch = { transcribe: 'done', index: 'done', style: 'done' }; paint();
      screenEl.classList.remove('prep'); screenEl.innerHTML = screenReady;
      finish();
    });
  })();
})();
