/* wf-app.jsx — tab shell + tweaks */

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "sketchy": true,
  "annotations": true,
  "density": "regular",
  "accent": "#2E5AAC"
}/*EDITMODE-END*/;

const TABS = [
  { k: "flow",     n: "Flow",     C: () => <FlowMap /> },
  { k: "login",    n: "Login",    C: () => <Login /> },
  { k: "submit",   n: "Submit",   C: () => <Submit /> },
  { k: "progress", n: "Progress", C: () => <Progress /> },
  { k: "review",   n: "Review",   C: () => <Review /> },
  { k: "export",   n: "Export",   C: () => <Export /> },
];

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tab, setTab] = React.useState(() => {
    const h = (location.hash || "").replace("#", "");
    return TABS.some(x => x.k === h) ? h : "flow";
  });
  React.useEffect(() => { location.hash = tab; }, [tab]);

  const Active = (TABS.find(x => x.k === tab) || TABS[0]).C;
  const rootStyle = {
    "--accent": t.accent,
    "--accent-soft": `color-mix(in srgb, ${t.accent} 13%, #ffffff)`,
  };

  return (
    <div className={"wf-root " + (t.sketchy ? "sketchy" : "clean")}
         data-density={t.density}
         data-annotations={t.annotations ? "on" : "off"}
         style={rootStyle}>

      <header className="appbar">
        <div className="brand">
          <span className="mark"><Icon name="file" size={15} /></span>
          Video-to-Note
        </div>
        <nav className="tabs">
          {TABS.map((x, i) => (
            <button key={x.k} className={"tab" + (tab === x.k ? " active" : "")} onClick={() => setTab(x.k)}>
              <span className="num">{i}</span>{x.n}
            </button>
          ))}
        </nav>
        <span className="spacer"></span>
        <span className="hint anno">{t.sketchy ? "low-fi sketch" : "clean wireframe"}</span>
      </header>

      <div className="canvas">
        <Active />
      </div>

      <TweaksPanel>
        <TweakSection label="Rendering" />
        <TweakToggle label="Sketchy" value={t.sketchy} onChange={v => setTweak("sketchy", v)} />
        <TweakToggle label="Annotations" value={t.annotations} onChange={v => setTweak("annotations", v)} />
        <TweakRadio label="Density" value={t.density}
                    options={["compact", "regular", "roomy"]}
                    onChange={v => setTweak("density", v)} />
        <TweakSection label="Accent" />
        <TweakColor label="Accent" value={t.accent}
                    options={["#2E5AAC", "#2A8267", "#475569", "#7A5AE0"]}
                    onChange={v => setTweak("accent", v)} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
