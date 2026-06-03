/* wf-kit.jsx — shared wireframe primitives + inline icon set (lucide-style strokes) */

/* ---- Icons (lucide geometry, 24x24 viewBox) ---- */
const ICONS = {
  link: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71",
  youtube: "M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z|M9.75 15.02l5.75-3.27-5.75-3.27z",
  play: "M6 3l14 9-14 9z",
  pause: "M6 4h4v16H6zM14 4h4v16h-4z",
  scissors: "M6 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM20 4L8.12 15.88M14.47 14.48L20 20M8.12 8.12L12 12",
  merge: "M6 3v6a6 6 0 0 0 6 6h6M6 21V9M18 21l3-3-3-3|M6 3a2 2 0 1 0 0 0",
  refresh: "M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5",
  history: "M3 3v5h5M3.05 13A9 9 0 1 0 6 5.3L3 8M12 7v5l4 2",
  camera: "M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  image: "M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM21 15l-5-5L5 21",
  download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
  warn: "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01",
  check: "M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3",
  loader: "M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
  chevron: "M6 9l6 6 6-6",
  help: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01",
  edit: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  lock: "M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2zM7 11V7a5 5 0 0 1 10 0v4",
  user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  arrowRight: "M5 12h14M12 5l7 7-7 7",
  arrowDown: "M12 5v14M5 12l7 7 7-7",
  trash: "M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2",
  grip: "M9 5a1 1 0 1 0 0 0M9 12a1 1 0 1 0 0 0M9 19a1 1 0 1 0 0 0M15 5a1 1 0 1 0 0 0M15 12a1 1 0 1 0 0 0M15 19a1 1 0 1 0 0 0",
  plus: "M12 5v14M5 12h14",
  x: "M18 6L6 18M6 6l12 12",
  dots: "M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
  sparkle: "M12 3l1.9 5.8a2 2 0 0 0 1.3 1.3L21 12l-5.8 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.8a2 2 0 0 0-1.3-1.3L3 12l5.8-1.9a2 2 0 0 0 1.3-1.3z",
  upload: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12",
  paste: "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M9 2h6a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4z",
};
function Icon({ name, size = 18, className = "", style }) {
  const d = ICONS[name] || "";
  const parts = d.split("|");
  return (
    <svg className={"icn " + className} width={size} height={size} viewBox="0 0 24 24"
         fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
         strokeLinejoin="round" style={style} aria-hidden="true">
      {parts.map((p, i) => <path key={i} d={p} />)}
    </svg>
  );
}

/* ---- Browser frame ---- */
function Frame({ route = "video-to-note.app", children, style }) {
  return (
    <div className="frame" style={style}>
      <div className="frame-bar">
        <span className="dots"><i></i><i></i><i></i></span>
        <span className="urlbar">{route}</span>
        <span style={{ width: 40 }}></span>
      </div>
      <div className="frame-body">{children}</div>
    </div>
  );
}

/* ---- Placeholder text lines ---- */
function Lines({ rows = ["w90", "w80", "w90", "w60"], gap }) {
  return (
    <div className="lines" style={gap ? { gap } : null}>
      {rows.map((w, i) => <div key={i} className={"ln " + w}></div>)}
    </div>
  );
}

/* ---- Image / screenshot placeholder ---- */
function ImgPh({ tag, cap, height = 110, style }) {
  return (
    <div className="imgph wob" style={{ height, ...style }}>
      {tag && <span className="tag">{tag}</span>}
      {cap && <span className="cap">{cap}</span>}
    </div>
  );
}

/* ---- Classification badge ---- */
function Cls({ kind }) {
  const label = { text_led: "text_led", visual_led: "visual_led", mixed: "mixed" }[kind];
  const cls = { text_led: "text", visual_led: "visual", mixed: "mixed" }[kind];
  return <span className={"chip " + cls}><span className="dot"></span>{label}</span>;
}

/* ---- Annotation (margin note) ---- */
function Anno({ n, children, style }) {
  return (
    <div className="anno" style={style}>
      {n && <span className="anno-pin">{n}</span>}
      <span>{children}</span>
    </div>
  );
}

/* ---- Stage rail (progress) — phases, with analyzing branches ---- */
function StageRail({ phase = 2, withStyle = true }) {
  const phases = ["resolving", "acquiring", "analyzing", "segmenting", "drafting"];
  const branches = ["transcribe", "index", ...(withStyle ? ["style"] : [])];
  return (
    <div className="stage-rail2">
      {phases.map((p, i) => {
        const state = i < phase ? "done" : i === phase ? "now" : "todo";
        return (
          <React.Fragment key={p}>
            <div className={"stage2 " + state}>
              <div className="stage2-row">
                <span className="stage-mark">
                  {state === "done" ? <Icon name="check" size={13} />
                    : state === "now" ? <Icon name="loader" size={13} />
                    : <span className="stage-num">{i + 1}</span>}
                </span>
                <span className="stage-name mono">{p}</span>
              </div>
              {p === "analyzing" && (
                <div className="stage-branches">
                  {branches.map(b => (
                    <span key={b} className={"branch-chip" + (b === "style" ? " style" : "")}>
                      {b === "style" && <Icon name="sparkle" size={11} />}{b}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {i < phases.length - 1 && <span className="stage2-conn" />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

Object.assign(window, { Icon, Frame, Lines, ImgPh, Cls, Anno, StageRail });
