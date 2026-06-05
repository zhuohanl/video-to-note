/* editor-review.js — markdown toolbar + transcript toggle + version control */
(function () {
  lucide.createIcons();
  var noteDoc = document.getElementById('noteDoc');
  var popLayer = document.getElementById('popLayer');

  /* ---------- transcript toggle ---------- */
  document.getElementById('txToggle').addEventListener('change', function (e) {
    document.body.classList.toggle('show-tx', e.target.checked);
    flash(e.target.checked ? 'Transcript shown' : 'Transcript hidden');
  });

  /* ---------- markdown toolbar ---------- */
  var toolbar = document.getElementById('mdToolbar');
  var styleSel = document.getElementById('mdStyle');
  var lastEditable = noteDoc;
  noteDoc.addEventListener('focusin', function () { lastEditable = noteDoc; });
  toolbar.addEventListener('mousedown', function (e) { if (e.target.closest('button, select')) e.preventDefault(); });
  function focusBack() {
    noteDoc.focus();
    var sel = window.getSelection();
    if (sel.rangeCount === 0 || !noteDoc.contains(sel.anchorNode)) {
      var r = document.createRange(); r.selectNodeContents(noteDoc); r.collapse(false);
      sel.removeAllRanges(); sel.addRange(r);
    }
  }
  function exec(cmd, val) { focusBack(); try { document.execCommand(cmd, false, val || null); } catch (e) {} updateToolbar(); flash('Edited'); }
  toolbar.querySelectorAll('[data-cmd]').forEach(function (b) {
    b.addEventListener('click', function () {
      var cmd = b.dataset.cmd;
      if (cmd === 'divider') { focusBack(); document.execCommand('insertHTML', false, '<hr class="md-hr"><p><br></p>'); flash('Divider added'); return; }
      if (cmd === 'code') { focusBack(); var t = window.getSelection().toString(); document.execCommand('insertHTML', false, '<code>' + (t || 'code') + '</code>'); flash('Edited'); return; }
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
      if (blk === 'h3' || blk === 'h4') styleSel.value = blk; else if (blk === 'p' || blk === 'div' || blk === '') styleSel.value = 'p';
    } catch (e) {}
  }
  document.addEventListener('selectionchange', function () {
    var a = window.getSelection().anchorNode;
    if (a && noteDoc.contains(a)) updateToolbar();
  });

  /* ---------- version control ---------- */
  var VERSIONS = [], activeVersionId = null;
  var vCountEl = document.getElementById('vCount');
  function relTime(t) { var s = Math.round((Date.now() - t) / 1000); if (s < 45) return 'just now'; var m = Math.round(s / 60); return m < 60 ? m + 'm ago' : Math.round(m / 60) + 'h ago'; }
  function addVersion(label, initial) {
    VERSIONS.unshift({ id: String(Date.now()) + Math.random().toString(36).slice(2), label: label, t: Date.now(), html: noteDoc.innerHTML, initial: !!initial });
    activeVersionId = VERSIONS[0].id; vCountEl.textContent = VERSIONS.length;
  }
  addVersion('Initial note', true);

  /* ---------- Edit ↔ Review sync ---------- */
  // The moment the user edits the assembled note, mark it "polished" so the Edit
  // page knows to warn before clip changes, and to offer a rebuild on return.
  function markPolished() { try { localStorage.setItem('vtn_notePolished', '1'); } catch (e) {} }
  noteDoc.addEventListener('input', markPolished);

  // If clips changed in Edit after the note was polished, offer to rebuild.
  (function maybeRebuildBanner() {
    try { if (localStorage.getItem('vtn_clipsChanged') !== '1') return; } catch (e) { return; }
    var b = document.createElement('div');
    b.className = 'er-rebuild';
    b.innerHTML = '<i data-lucide="refresh-cw"></i>' +
      '<div class="grow"><b>Your clips changed in Edit.</b> Rebuild the note to include them, or keep the version you wrote — we\u2019ll save a copy to History either way.</div>' +
      '<button class="btn ghost sm" data-keep>Keep my note</button>' +
      '<button class="btn primary sm" data-rebuild><i data-lucide="refresh-cw"></i>Rebuild note</button>';
    var doc = document.querySelector('.er-doc');
    doc.insertBefore(b, doc.firstChild);
    lucide.createIcons();
    b.querySelector('[data-keep]').addEventListener('click', function () {
      try { localStorage.removeItem('vtn_clipsChanged'); } catch (e) {}
      b.remove(); flash('Kept your note');
    });
    b.querySelector('[data-rebuild]').addEventListener('click', function () {
      addVersion('Note before rebuild');
      try { localStorage.removeItem('vtn_clipsChanged'); localStorage.removeItem('vtn_notePolished'); } catch (e) {}
      b.remove(); flash('Rebuilt from your latest clips · previous note saved to History');
    });
  })();

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
    p.innerHTML = '<div class="menu-head eyebrow">Versions</div>' + VERSIONS.map(function (v) {
      var cur = v.id === activeVersionId;
      return '<div class="ver-row' + (cur ? ' cur' : '') + '"><span class="ver-ic"><i data-lucide="' + (v.initial ? 'file-text' : 'save') + '"></i></span>' +
        '<div class="grow"><div class="vlabel">' + v.label + '</div><div class="vtime">' + relTime(v.t) + '</div></div>' +
        (cur ? '<span class="ver-tag">current</span>' : '<button class="btn ghost sm" data-restore="' + v.id + '">Restore</button>') + '</div>';
    }).join('');
    place(p, versionsBtn);
    p.querySelectorAll('[data-restore]').forEach(function (b) { b.addEventListener('click', function () { restoreVersion(b.dataset.restore); }); });
  }
  function restoreVersion(id) {
    var v = VERSIONS.filter(function (x) { return x.id === id; })[0];
    if (!v) return;
    noteDoc.innerHTML = v.html; lucide.createIcons(); activeVersionId = id; closePops(); flash('Restored “' + v.label + '”');
  }

  /* ---------- popover plumbing ---------- */
  function place(p, anchor) {
    popLayer.appendChild(p);
    var r = anchor.getBoundingClientRect();
    var pw = p.offsetWidth, ph = p.offsetHeight;
    var left = r.right + window.scrollX - pw; if (left < 12) left = 12;
    var top = r.top + window.scrollY - ph - 8; if (top < window.scrollY + 12) top = r.bottom + window.scrollY + 8;
    p.style.position = 'absolute'; p.style.top = top + 'px'; p.style.left = left + 'px';
    lucide.createIcons();
  }
  function closePops() { popLayer.innerHTML = ''; }
  document.addEventListener('click', function (e) { if (!e.target.closest('#popLayer') && !e.target.closest('#versionsBtn')) closePops(); });

  /* ---------- save ---------- */
  var saveStatus = document.getElementById('saveStatus'), st;
  function flash(msg) {
    clearTimeout(st);
    saveStatus.innerHTML = '<i data-lucide="loader" style="width:14px;height:14px;"></i>' + msg;
    saveStatus.className = 'chip outline mono'; lucide.createIcons();
    st = setTimeout(function () { saveStatus.innerHTML = '<i data-lucide="check"></i>Saved'; saveStatus.className = 'chip ok'; lucide.createIcons(); }, 1200);
  }
  var sd = document.getElementById('saveDraft');
  sd.addEventListener('click', function () {
    markPolished();
    addVersion('Saved ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    var o = sd.innerHTML; sd.innerHTML = '<i data-lucide="check"></i>Version saved'; sd.disabled = true; lucide.createIcons();
    setTimeout(function () { sd.innerHTML = o; sd.disabled = false; lucide.createIcons(); }, 1500);
  });
})();
