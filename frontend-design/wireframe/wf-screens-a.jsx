/* wf-screens-a.jsx — Flow map, Login, Submit (3 variants) */

const DEPTHS = [
  { k: "thorough", t: "Thorough", s: "Capture detail, like you're learning it." },
  { k: "balanced", t: "Balanced", s: "The useful middle." },
  { k: "brief",    t: "Brief",    s: "High-level takeaways." },
  { k: "custom",   t: "I'll prompt it", s: "Describe exactly what you want." },
];
const SUBMIT_PH = "https://www.youtube.com/watch?v=…   ·   or a Build / Ignite session URL";

/* ============================ FLOW MAP ============================ */
function FlowMap() {
  const nodes = [
    { n: "1", t: "Login", r: "/login", d: "Single shared credential", ic: "lock" },
    { n: "2", t: "Submit", r: "/", d: "URL · depth · style examples", ic: "link" },
    { n: "3", t: "Progress", r: "/jobs/[id]", d: "Stages stream over SSE", ic: "loader" },
    { n: "4", t: "Review", r: "/jobs/[id]", d: "Edit notes, sections, shots", ic: "edit" },
    { n: "5", t: "Export", r: "…/export", d: "Download note.md + images", ic: "download" },
  ];
  return (
    <div>
      <div className="screen-head">
        <h2><Icon name="arrowRight" size={22} /> Navigation flow</h2>
        <p>Five surfaces, one linear path. Progress and Review live on the same route — the progress view morphs into the editor as sections stream in.</p>
      </div>
      <div className="frame">
        <div className="frame-body" style={{ padding: "calc(34px * var(--d))" }}>
          <div className="flow-row">
            {nodes.map((nd, i) => (
              <React.Fragment key={nd.n}>
                <div className={"flow-node wob" + (i % 2 ? " tilt" : "")}>
                  <div className="flow-top">
                    <span className="flow-num mono">{nd.n}</span>
                    <Icon name={nd.ic} size={18} />
                  </div>
                  <div className="flow-title label">{nd.t}</div>
                  <div className="mono flow-route">{nd.r}</div>
                  <div className="sublabel flow-desc">{nd.d}</div>
                </div>
                {i < nodes.length - 1 && (
                  <div className="flow-arrow"><Icon name="arrowRight" size={26} /></div>
                )}
              </React.Fragment>
            ))}
          </div>

          <div className="flow-loops">
            <div className="flow-loop anno">
              <span className="anno-pin">↻</span>
              <span><b>Review loops:</b> regenerate a section, split / merge boundaries, restore a prior revision, capture a frame — all synchronous, no re-queue.</span>
            </div>
            <div className="flow-loop anno">
              <span className="anno-pin">!</span>
              <span><b>Same route, two modes:</b> <span className="mono">/jobs/[id]</span> starts as Progress and becomes Review without a navigation.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================== LOGIN ============================== */
function Login() {
  return (
    <div>
      <div className="screen-head">
        <h2><Icon name="lock" size={20} /> Login</h2>
        <span className="route">/login</span>
        <p>A single shared username + password gates the whole app. Success sets a signed httpOnly session cookie — the SSE stream rides the same cookie.</p>
      </div>
      <Frame route="video-to-note.app/login">
        <div className="login-wrap">
          <div className="login-card box flat wob">
            <div className="brand" style={{ fontSize: 22, marginBottom: 4 }}>
              <span className="mark"><Icon name="file" size={15} /></span> Video-to-Note
            </div>
            <div className="sublabel" style={{ marginBottom: 20 }}>A reading room for talks.</div>

            <div className="eyebrow" style={{ marginBottom: 6 }}>Username</div>
            <div className="input" style={{ marginBottom: 14 }}>shared-user</div>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Password</div>
            <div className="input" style={{ marginBottom: 20 }}>••••••••••••</div>

            <button className="btn primary wob" style={{ width: "100%", justifyContent: "center" }}>
              Sign in <Icon name="arrowRight" size={16} />
            </button>
          </div>
          <Anno n="i" style={{ marginTop: 20, maxWidth: 380 }}>
            Shared login = no per-person attribution. Swaps cleanly to Entra ID later behind the same cookie boundary.
          </Anno>
        </div>
      </Frame>
    </div>
  );
}

/* ============================= SUBMIT ============================= */
function DepthCard({ d, sel, big }) {
  return (
    <div className={"depth-card box wob" + (sel ? " sel" : "") + (big ? " big" : "")}>
      <div className="row between center">
        <span className="label" style={{ fontSize: big ? 17 : 15 }}>{d.t}</span>
        <Icon name="help" size={16} className="muted" />
      </div>
      <div className="sublabel" style={{ marginTop: 4 }}>{d.s}</div>
      {sel && <span className="depth-tick"><Icon name="check" size={13} /></span>}
    </div>
  );
}

function StylePanel() {
  const [open, setOpen] = React.useState(true);
  return (
    <div className="style-panel box wob" style={{ marginTop: 14 }}>
      <button className="style-head" onClick={() => setOpen(o => !o)}>
        <span className="row center" style={{ gap: 9 }}>
          <Icon name="sparkle" size={16} className="muted" />
          <span className="label">Match my style</span>
          <span className="sublabel" style={{ fontSize: 13 }}>optional</span>
        </span>
        <Icon name="chevron" size={16} className="muted" style={{ transform: open ? "rotate(180deg)" : "none" }} />
      </button>

      {open && (
        <div className="style-body">
          <div className="style-saved row center between wob">
            <span className="row center" style={{ gap: 9 }}>
              <span className="depth-radio" style={{ borderRadius: 5 }}><span className="depth-radio-dot" style={{ borderRadius: 2 }} /></span>
              <span className="label" style={{ fontSize: 14 }}>Use my saved style</span>
              <span className="chip mono">2 notes</span>
            </span>
            <span className="anno">pre-checked if a default exists</span>
          </div>

          <div className="style-or"><span>or add examples for this job</span></div>

          <div className="style-drop wob">
            <Icon name="upload" size={20} className="muted" />
            <div className="sublabel" style={{ textAlign: "center" }}>
              Drop <b>.md</b> files, or <span style={{ color: "var(--accent)" }}>browse</span> · paste markdown
            </div>
            <div className="row center wrap" style={{ gap: 8, justifyContent: "center", marginTop: 4 }}>
              <span className="chip mono"><Icon name="file" size={12} /> my-talk-notes.md <Icon name="x" size={11} /></span>
              <span className="chip mono"><Icon name="file" size={12} /> kubecon-2024.md <Icon name="x" size={11} /></span>
            </div>
          </div>

          <label className="style-toggle row center" style={{ gap: 9 }}>
            <span className="wf-switch"><span className="wf-knob" /></span>
            <span className="sublabel" style={{ fontSize: 13.5 }}>Save as my default style for future jobs</span>
          </label>

          <Anno style={{ marginTop: 2 }}>
            Examples steer format, voice &amp; detail; <b>depth</b> fills in anything they don't pin down. Style/format reference only — never a source of facts.
          </Anno>
        </div>
      )}
    </div>
  );
}

function SubmitA() {
  return (
    <Frame route="video-to-note.app/">
      <div className="submit-centered">
        <div className="eyebrow" style={{ textAlign: "center" }}>Submit a talk</div>
        <h3 className="submit-h">Turn a conference talk into reviewed notes.</h3>
        <div className="row" style={{ gap: 10, marginTop: 6 }}>
          <div className="input lg grow row center" style={{ gap: 10 }}>
            <Icon name="link" size={17} className="muted" />
            <span className="grow" style={{ color: "var(--line-3)" }}>{SUBMIT_PH}</span>
          </div>
          <button className="btn primary wob" style={{ alignSelf: "stretch", padding: "0 20px" }}>
            Submit <Icon name="arrowRight" size={16} />
          </button>
        </div>

        <div className="row between center" style={{ marginTop: 26, marginBottom: 12 }}>
          <span className="eyebrow">Note depth</span>
          <Anno>“?” help on each card</Anno>
        </div>
        <div className="depth-grid">
          {DEPTHS.map((d, i) => <DepthCard key={d.k} d={d} sel={i === 0} />)}
        </div>

        <div className="custom-reveal box sunken wob" style={{ marginTop: 14 }}>
          <div className="row center" style={{ gap: 8, marginBottom: 8 }}>
            <Icon name="edit" size={15} className="muted" />
            <span className="sublabel">Custom prompt — shown only for “I'll prompt it”</span>
          </div>
          <Lines rows={["w90", "w70"]} />
        </div>

        <StylePanel />

        <div className="banner info wob" style={{ marginTop: 16 }}>
          <Icon name="warn" size={16} className="b-ic" />
          <span><b>Est. ~$1.42</b> for this video — shown up front, warns but never blocks.</span>
        </div>
      </div>
    </Frame>
  );
}

function Submit() {
  return (
    <div>
      <div className="screen-head">
        <h2><Icon name="link" size={20} /> Submit</h2>
        <span className="route">/</span>
        <p>Where a run begins: a URL, a note-depth choice, optional style examples, and an up-front cost estimate.</p>
      </div>
      <SubmitA />
    </div>
  );
}

Object.assign(window, { FlowMap, Login, Submit });
