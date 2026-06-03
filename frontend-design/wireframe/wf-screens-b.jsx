/* wf-screens-b.jsx — Progress, Review (3 variants), Export */

const SECTIONS = [
  { i: 1, t: "Opening & session goals", c: "text_led",   r: "0:00 – 4:12",  st: "ready" },
  { i: 2, t: "Architecture overview",   c: "mixed",       r: "4:12 – 12:40", st: "ready" },
  { i: 3, t: "Live demo: deploy worker",c: "visual_led",  r: "12:40 – 24:05",st: "ready" },
  { i: 4, t: "Q&A",                     c: "text_led",    r: "24:05 – 31:20",st: "ready" },
];

/* ---------- shared review pieces ---------- */
function Scrubber({ compact }) {
  return (
    <div className="scrubber box flat wob">
      <ImgPh tag="video proxy · 720p" height={compact ? 120 : 150} style={{ border: "none", borderRadius: 0 }} />
      <div className="scrub-controls">
        <button className="btn icon sm wob"><Icon name="play" size={14} /></button>
        <span className="mono" style={{ fontSize: 12 }}>12:40 / 31:20</span>
        <div className="scrub-track">
          <span className="scrub-fill" style={{ width: "41%" }}></span>
          {[8, 22, 41, 77].map(p => <span key={p} className="scrub-mark" style={{ left: p + "%" }}></span>)}
          <span className="scrub-head" style={{ left: "41%" }}></span>
        </div>
      </div>
      <button className="btn sm wob" style={{ margin: "10px", marginTop: 0 }}>
        <Icon name="camera" size={14} /> Capture frame here
      </button>
    </div>
  );
}

function Outline({ active = 3 }) {
  return (
    <div className="outline box flat wob">
      <div className="row between center" style={{ marginBottom: 10 }}>
        <span className="eyebrow">Outline</span>
        <span className="mono" style={{ fontSize: 11 }}>4 sections</span>
      </div>
      <div className="col" style={{ gap: 2 }}>
        {SECTIONS.map(s => (
          <div key={s.i} className={"outline-item" + (s.i === active ? " on" : "")}>
            <span className="mono outline-num">{String(s.i).padStart(2, "0")}</span>
            <span className="grow outline-t">{s.t}</span>
            <Cls kind={s.c} />
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionActions({ size = "", structuralDisabled, menu }) {
  const dis = structuralDisabled ? " is-disabled" : "";
  return (
    <div className="sec-actions">
      <div className="row wrap" style={{ gap: 8 }}>
        <button className={"btn ghost " + size}><Icon name="refresh" size={14} /> Regenerate</button>
        <button className={"btn ghost " + size + dis} title={structuralDisabled ? "available once drafting finishes" : ""}><Icon name="scissors" size={14} /> Split</button>
        <button className={"btn ghost " + size + dis} title={structuralDisabled ? "available once drafting finishes" : ""}><Icon name="merge" size={14} /> Merge up</button>
        <button className={"btn ghost " + size + (menu === "revisions" ? " on" : "")}><Icon name="history" size={14} /> Revisions</button>
        {structuralDisabled && <span className="anno" style={{ alignSelf: "center" }}>Split / Merge disabled until <span className="mono">done</span></span>}
      </div>
      {menu === "revisions" && <RevisionsMenu />}
      {menu === "regen" && <RegenWarning />}
    </div>
  );
}

function RevisionsMenu() {
  const revs = [
    { v: "v3", t: "Current (edited)", meta: "your edits · just now", cur: true },
    { v: "v2", t: "Regenerated", meta: "depth: thorough · 2m ago" },
    { v: "v1", t: "Original draft", meta: "first pass · 4m ago" },
  ];
  return (
    <div className="popover rev-menu wob">
      <div className="pop-head"><span className="eyebrow">Revisions</span><Icon name="x" size={14} className="muted" /></div>
      <div className="col" style={{ gap: 2 }}>
        {revs.map(r => (
          <div key={r.v} className={"rev-row" + (r.cur ? " cur" : "")}>
            <span className="mono rev-v">{r.v}</span>
            <div className="grow">
              <div className="label" style={{ fontSize: 13 }}>{r.t}</div>
              <div className="sublabel" style={{ fontSize: 12 }}>{r.meta}</div>
            </div>
            {r.cur ? <span className="chip mono">current</span> : <button className="btn sm wob">Restore</button>}
          </div>
        ))}
      </div>
    </div>
  );
}

function RegenWarning() {
  return (
    <div className="popover regen-warn wob">
      <div className="row center" style={{ gap: 8, marginBottom: 6 }}>
        <Icon name="warn" size={16} style={{ color: "var(--cls-visual)" }} />
        <span className="label" style={{ fontSize: 14 }}>Regenerate section?</span>
      </div>
      <div className="sublabel" style={{ fontSize: 13, marginBottom: 12, lineHeight: 1.45 }}>
        This replaces your manual edits with a fresh draft. A snapshot is saved to <b>Revisions</b> first — you can always restore it.
      </div>
      <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
        <button className="btn ghost sm wob">Keep my edits</button>
        <button className="btn primary sm wob"><Icon name="refresh" size={13} /> Regenerate anyway</button>
      </div>
    </div>
  );
}

function ShotTray({ degraded }) {
  return (
    <div className="shot-tray">
      <div className="row between center" style={{ marginBottom: 8 }}>
        <span className="eyebrow">Screenshots</span>
        <span className="anno">toggle · caption · reorder · delete</span>
      </div>
      <div className="row wrap" style={{ gap: 10 }}>
        {[1, 2, 3].map(n => (
          <div key={n} className="shot">
            <ImgPh cap={"0:1" + n + ":40"} height={74} style={{ width: 124 }} />
            <span className={"shot-pick" + (n < 3 ? " on" : "")}>
              {n < 3 ? <Icon name="check" size={12} /> : null}
            </span>
          </div>
        ))}
        {degraded ? (
          <div className="shot-add wob is-disabled" title="re-download the proxy to capture">
            <Icon name="camera" size={16} /><span className="sublabel" style={{ fontSize: 11 }}>capture off</span>
          </div>
        ) : (
          <button className="shot-add wob"><Icon name="plus" size={18} /><span className="sublabel" style={{ fontSize: 12 }}>Capture</span></button>
        )}
      </div>
    </div>
  );
}

function MediaUnavailable() {
  return (
    <div className="box flat wob media-gone">
      <div className="media-gone-art">
        <Icon name="youtube" size={26} className="muted" />
        <span className="media-gone-x"><Icon name="x" size={14} /></span>
      </div>
      <div className="media-gone-body">
        <div className="row center" style={{ gap: 7 }}>
          <Icon name="warn" size={15} style={{ color: "var(--cls-visual)" }} />
          <span className="label" style={{ fontSize: 14, whiteSpace: "nowrap" }}>Proxy expired</span>
        </div>
        <div className="sublabel" style={{ fontSize: 12.5, lineHeight: 1.45 }}>
          The scrub proxy was cleaned up (7-day TTL). Existing screenshots are kept; re-download to scrub or capture new frames.
        </div>
        <button className="btn sm wob" style={{ alignSelf: "flex-start" }}>
          <Icon name="download" size={14} /> Re-download proxy
        </button>
      </div>
    </div>
  );
}

function ExportBar() {
  return (
    <div className="export-bar">
      <span className="row center" style={{ gap: 9 }}>
        <span className="export-badge sm"><Icon name="check" size={14} /></span>
        <span className="sublabel" style={{ fontSize: 13 }}>4 sections · 9 screenshots · reviewed</span>
      </span>
      <span className="row center" style={{ gap: 8 }}>
        <button className="btn ghost sm wob"><Icon name="eye" size={13} /> Preview note.md</button>
        <button className="btn primary sm wob"><Icon name="download" size={14} /> Export ZIP</button>
      </span>
    </div>
  );
}

function SectionCard({ s, mode = "preview", active, banner, menu, structuralDisabled, degraded }) {
  return (
    <div className={"sec-card box wob" + (active ? " active" : "")} data-screen-label={"section-" + s.i}>
      <div className="row between center wrap" style={{ gap: 10 }}>
        <div className="row center" style={{ gap: 10 }}>
          <span className="mono sec-num">{String(s.i).padStart(2, "0")}</span>
          <span className="label sec-title">{s.t}</span>
          <Icon name="edit" size={14} className="muted" />
        </div>
        <div className="row center" style={{ gap: 8 }}>
          <Cls kind={s.c} />
          <span className="chip mono"><Icon name="clock" size={12} /> {s.r}</span>
        </div>
      </div>

      {banner === "boundaries" && (
        <div className="banner warn wob">
          <Icon name="warn" size={15} className="b-ic" />
          <span><b>Boundaries changed</b> — regenerate this section to fit its new span.</span>
        </div>
      )}

      <div className="md-editor box sunken wob">
        <div className="md-toolbar">
          <button className={"md-tab" + (mode === "edit" ? " on" : "")}><Icon name="edit" size={13} /> Edit</button>
          <button className={"md-tab" + (mode === "preview" ? " on" : "")}><Icon name="eye" size={13} /> Preview</button>
          <span className="grow"></span>
          <span className="anno">debounced PATCH → markdown_edited</span>
        </div>
        {mode === "edit" ? (
          <div className="md-body mono md-src">
            <div>## {s.t}</div>
            <div className="ln w90"></div>
            <div className="ln w80"></div>
            <div>![demo](images/0003-demo.png)</div>
            <div className="ln w70"></div>
          </div>
        ) : (
          <div className="md-body md-prose">
            <Lines rows={["w90", "w80", "w90"]} />
            <ImgPh cap="0:13:40" height={120} style={{ margin: "12px 0" }} />
            <Lines rows={["w70", "w50"]} />
          </div>
        )}
      </div>

      <ShotTray degraded={degraded} />
      <hr className="divider" style={{ margin: "4px 0" }} />
      <SectionActions size="sm" menu={menu} structuralDisabled={structuralDisabled} />
    </div>
  );
}

/* ============================ PROGRESS ============================ */
function Progress() {
  return (
    <div>
      <div className="screen-head">
        <h2><Icon name="loader" size={20} /> Progress → review</h2>
        <span className="route">/jobs/[jobId]</span>
        <p>Subscribed to the SSE stream. The stage rail advances; each section pops in the moment it's drafted, so reading can start before the run finishes.</p>
      </div>
      <Frame route="video-to-note.app/jobs/3f9c…">
        <div className="row between center wrap" style={{ gap: 12, marginBottom: 16 }}>
          <StageRail phase={4} withStyle={true} />
          <span className="chip mono"><Icon name="youtube" size={12} /> 58 min · captions</span>
        </div>

        <div className="col" style={{ gap: 10, marginBottom: 14 }}>
          <div className="banner info wob">
            <Icon name="warn" size={16} className="b-ic" />
            <span><b>Est. ~$1.42</b> — informational, never blocks. Actual cost recorded after the run.</span>
          </div>
          <div className="banner ok wob">
            <Icon name="sparkle" size={16} className="b-ic" />
            <span><b>Following your examples:</b> fine-grained sections, detailed notes. <span className="muted">Depth “Thorough” overridden — <u>switch back?</u></span></span>
          </div>
          <div className="banner warn wob">
            <Icon name="warn" size={16} className="b-ic" />
            <span><b>Transcript from speech, not official captions</b> — proper nouns &amp; code may need a closer check.</span>
          </div>
        </div>

        <div className="col" style={{ gap: 12 }}>
          <div className="row center" style={{ gap: 8 }}>
            <span className="eyebrow">Drafting sections</span>
            <span className="anno" style={{ whiteSpace: "nowrap" }}><span className="anno-pin">→</span> streamed by order_index</span>
          </div>

          {SECTIONS.slice(0, 2).map((s, idx) => (
            <div key={s.i} className="prog-sec box wob ready">
              <div className="row center" style={{ gap: 10 }}>
                <span className="mono sec-num">{String(s.i).padStart(2, "0")}</span>
                <span className="label">{s.t}</span>
                <Cls kind={s.c} />
                <span className="grow"></span>
                <span className="chip ok-chip"><Icon name="check" size={12} /> ready</span>
              </div>
              <Lines rows={["w90", "w70"]} gap={7} />
              {idx === 0 && (
                <>
                  <hr className="divider" style={{ margin: "2px 0" }} />
                  <SectionActions size="sm" structuralDisabled />
                </>
              )}
            </div>
          ))}

          <div className="prog-sec box wob drafting">
            <div className="row center" style={{ gap: 10 }}>
              <span className="mono sec-num">03</span>
              <span className="label">Live demo: deploy worker</span>
              <Cls kind="visual_led" />
              <span className="grow"></span>
              <span className="chip mono"><Icon name="loader" size={12} /> drafting…</span>
            </div>
            <div className="skel"><span></span><span></span><span></span></div>
          </div>

          <div className="prog-empty box sunken wob">
            <Icon name="file" size={18} className="muted" />
            <span className="sublabel">Sections will appear here as they're drafted.</span>
          </div>
        </div>
      </Frame>
      <Anno n="i" style={{ marginTop: 14, maxWidth: 620 }}>
        Same route as Review. When the last section is ready a <span className="mono">done</span> event fires and the view is fully in edit mode — no navigation.
      </Anno>
    </div>
  );
}

/* ====================== REVIEW — two-pane ====================== */
function ReviewA({ state = "ready" }) {
  const degraded = state === "media";
  const banner = state === "boundaries" ? "boundaries" : null;
  const menu = state === "revisions" ? "revisions" : state === "regen" ? "regen" : null;
  return (
    <Frame route="video-to-note.app/jobs/3f9c…">
      <div className="rev-a">
        <aside className="rev-a-rail">
          {degraded ? <MediaUnavailable /> : <Scrubber />}
          <Outline active={3} />
        </aside>
        <main className="rev-a-list">
          <SectionCard s={SECTIONS[1]} mode="preview" degraded={degraded} />
          <SectionCard s={SECTIONS[2]} mode="edit" active degraded={degraded} banner={banner} menu={menu} />
        </main>
      </div>
      <ExportBar />
    </Frame>
  );
}

function Review() {
  const [st, setSt] = React.useState("ready");
  const STATES = [
    ["ready", "Default"],
    ["revisions", "Revisions menu"],
    ["regen", "Regenerate warning"],
    ["boundaries", "Boundaries changed"],
    ["media", "Media unavailable"],
  ];
  const caps = {
    ready: "review_ready — full editing. Sticky video + outline rail; each section card has the markdown editor, classification badge, timestamp, screenshot tray, and Regenerate / Split / Merge / Revisions. ExportBar pinned at the bottom.",
    revisions: "Revisions menu — prior versions of a section (original draft, regenerated, current edits) with one-click Restore. Opened from the Revisions action.",
    regen: "Regenerate warning — regenerating a section that has manual edits asks first; a snapshot is saved to Revisions so the edits are recoverable.",
    boundaries: "Boundaries changed — after a Split or Merge, the affected section shows a non-blocking “regenerate to fit” banner.",
    media: "Degraded (media_unavailable) — the scrub proxy expired (7-day TTL). The scrubber and capture affordances are hidden and replaced by a “re-download to scrub / capture” action; existing screenshots remain.",
  };
  return (
    <div>
      <div className="screen-head">
        <h2><Icon name="edit" size={20} /> Review editor</h2>
        <span className="route">/jobs/[jobId]</span>
        <p>The workhorse. Edit markdown, adjust section boundaries, regenerate a single section, swap revisions, and capture missing frames — all before export.</p>
      </div>
      <div className="variants wob">
        {STATES.map(([k, l]) => (
          <button key={k} className={st === k ? "on" : ""} onClick={() => setSt(k)}>{l}</button>
        ))}
      </div>
      <div className="variant-cap">{caps[st]}</div>
      <ReviewA state={st} />
    </div>
  );
}

/* ============================= EXPORT ============================= */
function Export() {
  return (
    <div>
      <div className="screen-head">
        <h2><Icon name="download" size={20} /> Export</h2>
        <span className="route">/jobs/[jobId]/export</span>
        <p>Assembles a ZIP from current DB state + Blob assets: a markdown file with relative image paths, an images folder, and a metadata file for audit / re-import.</p>
      </div>
      <Frame route="video-to-note.app/jobs/3f9c…/export">
        <div className="export-wrap">
          <div className="export-card box flat wob">
            <div className="row center" style={{ gap: 12, marginBottom: 6 }}>
              <span className="export-badge"><Icon name="check" size={20} /></span>
              <div>
                <div className="label" style={{ fontSize: 18 }}>Notes ready to export</div>
                <div className="sublabel">4 sections · 9 screenshots</div>
              </div>
            </div>
            <hr className="divider" style={{ margin: "14px 0" }} />
            <div className="eyebrow" style={{ marginBottom: 10 }}>ZIP contents</div>
            <div className="file-tree mono">
              <div className="row center" style={{ gap: 8 }}><Icon name="file" size={14} /> note.md</div>
              <div className="row center" style={{ gap: 8, paddingLeft: 18 }}><Icon name="image" size={14} /> images/ <span className="muted">0001-intro.png · 0002-demo.png · …</span></div>
              <div className="row center" style={{ gap: 8 }}><Icon name="file" size={14} /> metadata.json</div>
            </div>
            <button className="btn primary wob" style={{ width: "100%", justifyContent: "center", marginTop: 18 }}>
              <Icon name="download" size={16} /> Export & download ZIP
            </button>
          </div>
          <div className="col" style={{ gap: 14, maxWidth: 300 }}>
            <Anno n="i">metadata.json stores source URL, depth, transcript source + per-section / per-shot timestamps.</Anno>
            <div className="banner ok wob">
              <Icon name="check" size={15} className="b-ic" />
              <span>Reproducible — re-assembled any time from current state.</span>
            </div>
          </div>
        </div>
      </Frame>
    </div>
  );
}

Object.assign(window, { Progress, Review, Export });
