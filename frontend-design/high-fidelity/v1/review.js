/* review.js — document-first review interactions */
(function () {
  lucide.createIcons();

  var doc = document.getElementById('doc');
  var noteDoc = document.getElementById('noteDoc');
  var headings = Array.prototype.slice.call(noteDoc.querySelectorAll('h2.note-h'));
  var popLayer = document.getElementById('popLayer');

  /* ---------- active section tracking (for "Adding to →") ---------- */
  var targetEl = document.getElementById('targetSec');
  function activeHeading() {
    var best = headings[0];
    headings.forEach(function (h) {
      var top = h.getBoundingClientRect().top;
      if (top - 160 <= 0) best = h;
    });
    return best;
  }
  function refreshTarget() {
    var h = activeHeading();
    targetEl.innerHTML = String(h.dataset.sec).padStart(2, '0') + ' · ' + h.dataset.title;
  }
  window.addEventListener('scroll', refreshTarget, { passive: true });
  refreshTarget();

  /* ---------- markdown toolbar ---------- */
  var toolbar = document.getElementById('mdToolbar');
  var styleSel = document.getElementById('mdStyle');
  var lastEditable = null;
  doc.addEventListener('focusin', function (e) {
    var ed = e.target.closest('.rv3-prose[contenteditable="true"]');
    if (ed) lastEditable = ed;
  });
  // keep selection when pressing toolbar controls
  toolbar.addEventListener('mousedown', function (e) { if (e.target.closest('button, select')) e.preventDefault(); });
  function focusBack() {
    if (!lastEditable) { lastEditable = doc.querySelector('.rv3-prose[contenteditable="true"]'); }
    if (lastEditable) {
      lastEditable.focus();
      var sel = window.getSelection();
      if (sel.rangeCount === 0 || !lastEditable.contains(sel.anchorNode)) {
        var r = document.createRange(); r.selectNodeContents(lastEditable); r.collapse(false);
        sel.removeAllRanges(); sel.addRange(r);
      }
    }
  }
  function exec(cmd, val) { focusBack(); try { document.execCommand(cmd, false, val || null); } catch (e) {} updateToolbar(); flashSaved('Edited'); }
  function wrapCode() {
    focusBack();
    var sel = window.getSelection();
    var txt = sel.toString();
    document.execCommand('insertHTML', false, '<code>' + (txt || 'code') + '</code>');
    flashSaved('Edited');
  }
  toolbar.querySelectorAll('[data-cmd]').forEach(function (b) {
    b.addEventListener('click', function () {
      var cmd = b.dataset.cmd;
      if (cmd === 'divider') { focusBack(); document.execCommand('insertHTML', false, '<hr class="md-hr"><p><br></p>'); flashSaved('Divider added'); return; }
      if (cmd === 'code') { wrapCode(); return; }
      if (cmd === 'quote') { exec('formatBlock', 'blockquote'); return; }
      if (cmd === 'createLink') { var u = prompt('Link URL'); if (u) exec('createLink', u); return; }
      exec(cmd);
    });
  });
  styleSel.addEventListener('change', function () { exec('formatBlock', styleSel.value); });
  function updateToolbar() {
    try {
      toolbar.querySelector('[data-cmd="bold"]').classList.toggle('on', document.queryCommandState('bold'));
      toolbar.querySelector('[data-cmd="italic"]').classList.toggle('on', document.queryCommandState('italic'));
      toolbar.querySelector('[data-cmd="insertUnorderedList"]').classList.toggle('on', document.queryCommandState('insertUnorderedList'));
      toolbar.querySelector('[data-cmd="insertOrderedList"]').classList.toggle('on', document.queryCommandState('insertOrderedList'));
      var blk = (document.queryCommandValue('formatBlock') || '').toLowerCase();
      if (blk === 'blockquote') { /* leave style select as-is */ }
      else if (blk === 'h3' || blk === 'h4' || blk === 'p' || blk === 'div' || blk === '') {
        styleSel.value = (blk === 'h3' || blk === 'h4') ? blk : 'p';
      }
    } catch (e) {}
  }
  document.addEventListener('selectionchange', function () {
    if (lastEditable && window.getSelection().anchorNode && lastEditable.contains(window.getSelection().anchorNode)) updateToolbar();
  });

  /* ---------- detail-level: change depth & regenerate in place ---------- */
  var DEPTHS = [
    { k: 'brief', name: 'Brief', desc: 'High-level takeaways.' },
    { k: 'balanced', name: 'Balanced', desc: 'The useful middle.' },
    { k: 'thorough', name: 'Thorough', desc: "Capture detail, like you're learning it." },
    { k: 'custom', name: "I'll prompt it", desc: 'Describe exactly what you want.' }
  ];
  var currentDepth = 'balanced';
  var detailBtn = document.getElementById('detailBtn');
  var detailCur = document.getElementById('detailCur');

  detailBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    if (popLayer.querySelector('.rv3-pop.depth')) { closePops(); detailBtn.setAttribute('aria-expanded', 'false'); return; }
    openDepthPanel();
  });

  function openDepthPanel() {
    closePops();
    detailBtn.setAttribute('aria-expanded', 'true');
    var picked = currentDepth;
    var p = document.createElement('div');
    p.className = 'rv3-pop depth';
    var rows = DEPTHS.map(function (d) {
      return '<button class="dp-opt' + (d.k === picked ? ' sel' : '') + '" data-d="' + d.k + '">' +
        '<span class="dp-radio"></span>' +
        '<span><span class="dp-name">' + d.name + (d.k === currentDepth ? ' <span class="badge-cur">current</span>' : '') + '</span>' +
        '<span class="dp-desc">' + d.desc + '</span></span></button>';
    }).join('');
    p.innerHTML =
      '<div class="dp-head">Change detail level</div>' +
      '<div class="dp-sub">Re-drafts the notes at a new depth. The downloaded video &amp; transcript are reused — only the writing changes.</div>' +
      '<div class="dp-opts">' + rows + '</div>' +
      '<div class="dp-custom" hidden><textarea placeholder="Focus on the live demo and any CLI commands shown; keep prose tight…" spellcheck="false"></textarea></div>' +
      '<div class="dp-note"><i data-lucide="info"></i><span>Re-drafts all 4 sections. Your manual edits are saved to <strong>Version history</strong> first, so nothing is lost.</span></div>' +
      '<div class="dp-foot"><button class="btn ghost sm" data-cancel>Cancel</button><button class="btn primary sm" data-go disabled><i data-lucide="refresh-cw"></i>Regenerate all</button></div>';
    place(p, detailBtn);

    var custom = p.querySelector('.dp-custom');
    var note = p.querySelector('.dp-note');
    var goBtn = p.querySelector('[data-go]');
    function sync() {
      var changed = picked !== currentDepth || picked === 'custom';
      note.classList.toggle('show', changed);
      goBtn.disabled = !changed;
      custom.hidden = picked !== 'custom';
      lucide.createIcons();
    }
    p.querySelectorAll('.dp-opt').forEach(function (opt) {
      opt.addEventListener('click', function () {
        picked = opt.dataset.d;
        p.querySelectorAll('.dp-opt').forEach(function (o) { o.classList.remove('sel'); });
        opt.classList.add('sel');
        sync();
      });
    });
    p.querySelector('[data-cancel]').addEventListener('click', function () { closePops(); detailBtn.setAttribute('aria-expanded', 'false'); });
    goBtn.addEventListener('click', function () {
      currentDepth = picked;
      var label = DEPTHS.filter(function (d) { return d.k === picked; })[0].name;
      detailCur.textContent = label;
      closePops();
      detailBtn.setAttribute('aria-expanded', 'false');
      flashSaved('Regenerating all sections at ' + label + '…');
    });
    sync();
  }

  /* ---------- add screenshot from video ---------- */
  var addBtn = document.getElementById('addShot');
  addBtn.addEventListener('click', function () {
    var h = activeHeading();
    var time = document.querySelector('.scrub-row .mono').textContent.split('/')[0].trim();
    // walk this section's range [heading … next heading); drop any existing nudge
    var node = h.nextSibling, lastInSec = h, nextHeading = null;
    while (node) {
      if (node.nodeType === 1 && node.matches('h2.note-h')) { nextHeading = node; break; }
      if (node.nodeType === 1 && node.classList.contains('regen-nudge')) { var d = node; node = node.nextSibling; d.remove(); continue; }
      lastInSec = node; node = node.nextSibling;
    }
    var fig = document.createElement('figure');
    fig.className = 'rv3-fig just-added';
    fig.contentEditable = 'false';
    fig.innerHTML =
      '<div class="shot" style="background:#1b1b1b;color:#8fb98f;">new capture</div>' +
      '<div class="fig-tools"><button title="Recapture"><i data-lucide="refresh-cw"></i></button><button data-fig-remove title="Remove from note"><i data-lucide="trash-2"></i></button></div>' +
      '<figcaption><span class="mono faint">' + time + '</span><span class="cap" contenteditable="true" spellcheck="false">New screenshot — add a caption</span></figcaption>';
    if (nextHeading) noteDoc.insertBefore(fig, nextHeading); else noteDoc.appendChild(fig);
    // single regenerate nudge, paired directly to this capture
    var nudge = document.createElement('div');
    nudge.className = 'regen-nudge show';
    nudge.contentEditable = 'false';
    nudge.innerHTML =
      '<i data-lucide="image" style="width:16px;height:16px;color:var(--accent);"></i>' +
      '<span class="grow">Screenshot added. Want the text to describe it?</span>' +
      '<button class="btn ghost sm" data-nudge-dismiss>Keep text</button>' +
      '<button class="btn primary sm" data-regen><i data-lucide="refresh-cw"></i>Regenerate</button>';
    fig.after(nudge);
    lucide.createIcons();
    wireFig(fig);
    var y = fig.getBoundingClientRect().top + window.scrollY - 150;
    window.scrollTo({ top: y, behavior: 'smooth' });
    flashSaved('Screenshot added');
    setTimeout(function () { fig.classList.remove('just-added'); }, 950);
  });

  function wireFig(fig) {
    var rm = fig.querySelector('[data-fig-remove]');
    if (rm) rm.addEventListener('click', function () {
      // remove the paired "describe it?" nudge along with the screenshot
      var next = fig.nextElementSibling;
      if (next && next.classList.contains('regen-nudge')) next.remove();
      fig.remove();
      flashSaved('Screenshot removed');
    });
  }
  noteDoc.querySelectorAll('.rv3-fig').forEach(wireFig);

  /* ---------- regenerate confirm (overwrite warning) ---------- */
  function openRegenConfirm(anchor, nudge) {
    closePops();
    var p = document.createElement('div');
    p.className = 'rv3-pop confirm';
    p.innerHTML =
      '<div class="pop-title"><i data-lucide="triangle-alert" style="width:17px;height:17px;color:var(--warn-fg);"></i><strong>Regenerate this section?</strong></div>' +
      '<p>The text is rewritten from the transcript and the screenshots now in this section. Manual edits are saved to <strong>Version history</strong> first.</p>' +
      '<div class="pop-foot"><button class="btn ghost sm" data-cancel>Keep my edits</button><button class="btn primary sm" data-go><i data-lucide="refresh-cw"></i>Regenerate</button></div>';
    place(p, anchor);
    p.querySelector('[data-cancel]').addEventListener('click', closePops);
    p.querySelector('[data-go]').addEventListener('click', function () {
      closePops();
      if (nudge && nudge.parentNode) nudge.remove();
      flashSaved('Regenerating…');
    });
  }

  /* ---------- version history ---------- */
  function openHistory(anchor) {
    closePops();
    var p = document.createElement('div');
    p.className = 'rv3-pop menu';
    p.innerHTML =
      '<div class="menu-head eyebrow">Version history</div>' +
      '<button class="menu-item cur"><i data-lucide="dot"></i>Your edits<span class="meta">now</span></button>' +
      '<button class="menu-item"><i data-lucide="sparkles"></i>Regenerated<span class="meta">3m</span></button>' +
      '<button class="menu-item"><i data-lucide="file-text"></i>Original draft<span class="meta">6m</span></button>';
    place(p, anchor);
    p.querySelectorAll('.menu-item:not(.cur)').forEach(function (mi) {
      mi.addEventListener('click', function () { closePops(); flashSaved('Restored a version'); });
    });
  }

  /* ---------- split / merge affordances ---------- */
  noteDoc.querySelectorAll('.split-gap').forEach(function (g) {
    g.addEventListener('click', function () { flashSaved('Section split here'); });
  });

  /* ---------- wire section tools + nudges ---------- */
  doc.addEventListener('click', function (e) {
    var rb = e.target.closest('[data-regen]');
    if (rb) { e.stopPropagation(); openRegenConfirm(rb, rb.closest('.regen-nudge')); return; }
    var hb = e.target.closest('[data-history]');
    if (hb) { e.stopPropagation(); openHistory(hb); return; }
    var nd = e.target.closest('[data-nudge-dismiss]');
    if (nd) { var n = nd.closest('.regen-nudge'); if (n) n.remove(); return; }
  });

  /* ---------- popover plumbing ---------- */
  function place(p, anchor) {
    popLayer.appendChild(p);
    var r = anchor.getBoundingClientRect();
    var pw = p.offsetWidth, ph = p.offsetHeight;
    var top = r.bottom + window.scrollY + 8;
    var left = r.right + window.scrollX - pw; // right-align to the anchor
    if (left < 12) left = 12;
    if (left + pw > window.innerWidth - 12) left = window.innerWidth - pw - 12;
    // flip above if it would run off the bottom of the viewport
    if (r.bottom + ph + 16 > window.innerHeight) top = r.top + window.scrollY - ph - 8;
    p.style.top = Math.max(12, top) + 'px';
    p.style.left = left + 'px';
  }
  function closePops() { popLayer.innerHTML = ''; }
  document.addEventListener('click', function (e) {
    if (!e.target.closest('#popLayer') && !e.target.closest('[data-regen]') && !e.target.closest('[data-history]') && !e.target.closest('#detailBtn') && !e.target.closest('#versionsBtn')) {
      closePops();
      detailBtn.setAttribute('aria-expanded', 'false');
    }
  });

  /* ---------- document version control ---------- */
  var VERSIONS = [];
  var activeVersionId = null;
  var vCountEl = document.getElementById('vCount');
  function relTime(t) {
    var s = Math.round((Date.now() - t) / 1000);
    if (s < 45) return 'just now';
    var m = Math.round(s / 60); if (m < 60) return m + 'm ago';
    var hr = Math.round(m / 60); return hr + 'h ago';
  }
  function updateVCount() { if (vCountEl) vCountEl.textContent = VERSIONS.length; }
  function addVersion(label, initial) {
    VERSIONS.unshift({ id: String(Date.now()) + Math.random().toString(36).slice(2), label: label, t: Date.now(), html: noteDoc.innerHTML, initial: !!initial });
    activeVersionId = VERSIONS[0].id;
    updateVCount();
  }
  addVersion('Initial draft', true); // seed v1 from the drafted note

  var versionsBtn = document.getElementById('versionsBtn');
  versionsBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    if (popLayer.querySelector('.rv3-pop.versions')) { closePops(); return; }
    openVersions();
  });
  function openVersions() {
    closePops();
    var p = document.createElement('div');
    p.className = 'rv3-pop versions';
    var rows = VERSIONS.map(function (v) {
      var cur = v.id === activeVersionId;
      return '<div class="ver-row' + (cur ? ' cur' : '') + '">' +
        '<span class="ver-ic"><i data-lucide="' + (v.initial ? 'file-text' : 'save') + '"></i></span>' +
        '<div class="grow"><div class="vlabel">' + v.label + '</div><div class="vtime">' + relTime(v.t) + '</div></div>' +
        (cur ? '<span class="ver-tag">current</span>' : '<button class="btn ghost sm" data-restore="' + v.id + '">Restore</button>') +
        '</div>';
    }).join('');
    p.innerHTML = '<div class="menu-head eyebrow">Versions</div>' + rows;
    place(p, versionsBtn);
    p.querySelectorAll('[data-restore]').forEach(function (b) {
      b.addEventListener('click', function () { restoreVersion(b.dataset.restore); });
    });
  }
  function restoreVersion(id) {
    var v = VERSIONS.filter(function (x) { return x.id === id; })[0];
    if (!v) return;
    noteDoc.innerHTML = v.html;
    headings = Array.prototype.slice.call(noteDoc.querySelectorAll('h2.note-h'));
    noteDoc.querySelectorAll('.rv3-fig').forEach(wireFig);
    lucide.createIcons();
    activeVersionId = id;
    closePops();
    refreshTarget();
    flashSaved('Restored “' + v.label + '”');
  }

  /* ---------- save status ---------- */
  var saveStatus = document.getElementById('saveStatus');
  var saveTimer;
  function flashSaved(msg) {
    clearTimeout(saveTimer);
    saveStatus.innerHTML = '<i data-lucide="loader" style="width:14px;height:14px;"></i>' + msg;
    saveStatus.className = 'chip outline mono';
    lucide.createIcons();
    saveTimer = setTimeout(function () {
      saveStatus.innerHTML = '<i data-lucide="check"></i>Saved';
      saveStatus.className = 'chip ok';
      lucide.createIcons();
    }, 1400);
  }
  var sd = document.getElementById('saveDraft');
  if (sd) sd.addEventListener('click', function () {
    addVersion('Saved ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    var o = sd.innerHTML; sd.innerHTML = '<i data-lucide="check"></i>Version saved'; sd.disabled = true; lucide.createIcons();
    setTimeout(function () { sd.innerHTML = o; sd.disabled = false; lucide.createIcons(); }, 1600);
  });
})();
