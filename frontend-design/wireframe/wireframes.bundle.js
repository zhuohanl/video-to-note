(() => {
  const __TWEAKS_STYLE = `
  .twk-panel{position:fixed;right:16px;bottom:16px;z-index:2147483646;width:280px;
    max-height:calc(100vh - 32px);display:flex;flex-direction:column;
    transform:scale(var(--dc-inv-zoom,1));transform-origin:bottom right;
    background:rgba(250,249,247,.78);color:#29261b;
    -webkit-backdrop-filter:blur(24px) saturate(160%);backdrop-filter:blur(24px) saturate(160%);
    border:.5px solid rgba(255,255,255,.6);border-radius:14px;
    box-shadow:0 1px 0 rgba(255,255,255,.5) inset,0 12px 40px rgba(0,0,0,.18);
    font:11.5px/1.4 ui-sans-serif,system-ui,-apple-system,sans-serif;overflow:hidden}
  .twk-hd{display:flex;align-items:center;justify-content:space-between;
    padding:10px 8px 10px 14px;cursor:move;user-select:none}
  .twk-hd b{font-size:12px;font-weight:600;letter-spacing:.01em}
  .twk-x{appearance:none;border:0;background:transparent;color:rgba(41,38,27,.55);
    width:22px;height:22px;border-radius:6px;cursor:default;font-size:13px;line-height:1}
  .twk-x:hover{background:rgba(0,0,0,.06);color:#29261b}
  .twk-body{padding:2px 14px 14px;display:flex;flex-direction:column;gap:10px;
    overflow-y:auto;overflow-x:hidden;min-height:0;
    scrollbar-width:thin;scrollbar-color:rgba(0,0,0,.15) transparent}
  .twk-body::-webkit-scrollbar{width:8px}
  .twk-body::-webkit-scrollbar-track{background:transparent;margin:2px}
  .twk-body::-webkit-scrollbar-thumb{background:rgba(0,0,0,.15);border-radius:4px;
    border:2px solid transparent;background-clip:content-box}
  .twk-body::-webkit-scrollbar-thumb:hover{background:rgba(0,0,0,.25);
    border:2px solid transparent;background-clip:content-box}
  .twk-row{display:flex;flex-direction:column;gap:5px}
  .twk-row-h{flex-direction:row;align-items:center;justify-content:space-between;gap:10px}
  .twk-lbl{display:flex;justify-content:space-between;align-items:baseline;
    color:rgba(41,38,27,.72)}
  .twk-lbl>span:first-child{font-weight:500}
  .twk-val{color:rgba(41,38,27,.5);font-variant-numeric:tabular-nums}

  .twk-sect{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
    color:rgba(41,38,27,.45);padding:10px 0 0}
  .twk-sect:first-child{padding-top:0}

  .twk-field{appearance:none;box-sizing:border-box;width:100%;min-width:0;height:26px;padding:0 8px;
    border:.5px solid rgba(0,0,0,.1);border-radius:7px;
    background:rgba(255,255,255,.6);color:inherit;font:inherit;outline:none}
  .twk-field:focus{border-color:rgba(0,0,0,.25);background:rgba(255,255,255,.85)}
  select.twk-field{padding-right:22px;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='rgba(0,0,0,.5)' d='M0 0h10L5 6z'/></svg>");
    background-repeat:no-repeat;background-position:right 8px center}

  .twk-slider{appearance:none;-webkit-appearance:none;width:100%;height:4px;margin:6px 0;
    border-radius:999px;background:rgba(0,0,0,.12);outline:none}
  .twk-slider::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;
    width:14px;height:14px;border-radius:50%;background:#fff;
    border:.5px solid rgba(0,0,0,.12);box-shadow:0 1px 3px rgba(0,0,0,.2);cursor:default}
  .twk-slider::-moz-range-thumb{width:14px;height:14px;border-radius:50%;
    background:#fff;border:.5px solid rgba(0,0,0,.12);box-shadow:0 1px 3px rgba(0,0,0,.2);cursor:default}

  .twk-seg{position:relative;display:flex;padding:2px;border-radius:8px;
    background:rgba(0,0,0,.06);user-select:none}
  .twk-seg-thumb{position:absolute;top:2px;bottom:2px;border-radius:6px;
    background:rgba(255,255,255,.9);box-shadow:0 1px 2px rgba(0,0,0,.12);
    transition:left .15s cubic-bezier(.3,.7,.4,1),width .15s}
  .twk-seg.dragging .twk-seg-thumb{transition:none}
  .twk-seg button{appearance:none;position:relative;z-index:1;flex:1;border:0;
    background:transparent;color:inherit;font:inherit;font-weight:500;min-height:22px;
    border-radius:6px;cursor:default;padding:4px 6px;line-height:1.2;
    overflow-wrap:anywhere}

  .twk-toggle{position:relative;width:32px;height:18px;border:0;border-radius:999px;
    background:rgba(0,0,0,.15);transition:background .15s;cursor:default;padding:0}
  .twk-toggle[data-on="1"]{background:#34c759}
  .twk-toggle i{position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;
    background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.25);transition:transform .15s}
  .twk-toggle[data-on="1"] i{transform:translateX(14px)}

  .twk-num{display:flex;align-items:center;box-sizing:border-box;min-width:0;height:26px;padding:0 0 0 8px;
    border:.5px solid rgba(0,0,0,.1);border-radius:7px;background:rgba(255,255,255,.6)}
  .twk-num-lbl{font-weight:500;color:rgba(41,38,27,.6);cursor:ew-resize;
    user-select:none;padding-right:8px}
  .twk-num input{flex:1;min-width:0;height:100%;border:0;background:transparent;
    font:inherit;font-variant-numeric:tabular-nums;text-align:right;padding:0 8px 0 0;
    outline:none;color:inherit;-moz-appearance:textfield}
  .twk-num input::-webkit-inner-spin-button,.twk-num input::-webkit-outer-spin-button{
    -webkit-appearance:none;margin:0}
  .twk-num-unit{padding-right:8px;color:rgba(41,38,27,.45)}

  .twk-btn{appearance:none;height:26px;padding:0 12px;border:0;border-radius:7px;
    background:rgba(0,0,0,.78);color:#fff;font:inherit;font-weight:500;cursor:default}
  .twk-btn:hover{background:rgba(0,0,0,.88)}
  .twk-btn.secondary{background:rgba(0,0,0,.06);color:inherit}
  .twk-btn.secondary:hover{background:rgba(0,0,0,.1)}

  .twk-swatch{appearance:none;-webkit-appearance:none;width:56px;height:22px;
    border:.5px solid rgba(0,0,0,.1);border-radius:6px;padding:0;cursor:default;
    background:transparent;flex-shrink:0}
  .twk-swatch::-webkit-color-swatch-wrapper{padding:0}
  .twk-swatch::-webkit-color-swatch{border:0;border-radius:5.5px}
  .twk-swatch::-moz-color-swatch{border:0;border-radius:5.5px}

  .twk-chips{display:flex;gap:6px}
  .twk-chip{position:relative;appearance:none;flex:1;min-width:0;height:46px;
    padding:0;border:0;border-radius:6px;overflow:hidden;cursor:default;
    box-shadow:0 0 0 .5px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.06);
    transition:transform .12s cubic-bezier(.3,.7,.4,1),box-shadow .12s}
  .twk-chip:hover{transform:translateY(-1px);
    box-shadow:0 0 0 .5px rgba(0,0,0,.18),0 4px 10px rgba(0,0,0,.12)}
  .twk-chip[data-on="1"]{box-shadow:0 0 0 1.5px rgba(0,0,0,.85),
    0 2px 6px rgba(0,0,0,.15)}
  .twk-chip>span{position:absolute;top:0;bottom:0;right:0;width:34%;
    display:flex;flex-direction:column;box-shadow:-1px 0 0 rgba(0,0,0,.1)}
  .twk-chip>span>i{flex:1;box-shadow:0 -1px 0 rgba(0,0,0,.1)}
  .twk-chip>span>i:first-child{box-shadow:none}
  .twk-chip svg{position:absolute;top:6px;left:6px;width:13px;height:13px;
    filter:drop-shadow(0 1px 1px rgba(0,0,0,.3))}
`;
  function useTweaks(defaults) {
    const [values, setValues] = React.useState(defaults);
    const setTweak = React.useCallback((keyOrEdits, val) => {
      const edits = typeof keyOrEdits === "object" && keyOrEdits !== null ? keyOrEdits : { [keyOrEdits]: val };
      setValues((prev) => ({ ...prev, ...edits }));
      window.parent.postMessage({ type: "__edit_mode_set_keys", edits }, "*");
      window.dispatchEvent(new CustomEvent("tweakchange", { detail: edits }));
    }, []);
    return [values, setTweak];
  }
  function TweaksPanel({ title = "Tweaks", children }) {
    const [open, setOpen] = React.useState(false);
    const dragRef = React.useRef(null);
    const offsetRef = React.useRef({ x: 16, y: 16 });
    const PAD = 16;
    const clampToViewport = React.useCallback(() => {
      const panel = dragRef.current;
      if (!panel) return;
      const w = panel.offsetWidth, h = panel.offsetHeight;
      const maxRight = Math.max(PAD, window.innerWidth - w - PAD);
      const maxBottom = Math.max(PAD, window.innerHeight - h - PAD);
      offsetRef.current = {
        x: Math.min(maxRight, Math.max(PAD, offsetRef.current.x)),
        y: Math.min(maxBottom, Math.max(PAD, offsetRef.current.y))
      };
      panel.style.right = offsetRef.current.x + "px";
      panel.style.bottom = offsetRef.current.y + "px";
    }, []);
    React.useEffect(() => {
      if (!open) return;
      clampToViewport();
      if (typeof ResizeObserver === "undefined") {
        window.addEventListener("resize", clampToViewport);
        return () => window.removeEventListener("resize", clampToViewport);
      }
      const ro = new ResizeObserver(clampToViewport);
      ro.observe(document.documentElement);
      return () => ro.disconnect();
    }, [open, clampToViewport]);
    React.useEffect(() => {
      const onMsg = (e) => {
        var _a;
        const t = (_a = e == null ? void 0 : e.data) == null ? void 0 : _a.type;
        if (t === "__activate_edit_mode") setOpen(true);
        else if (t === "__deactivate_edit_mode") setOpen(false);
      };
      window.addEventListener("message", onMsg);
      window.parent.postMessage({ type: "__edit_mode_available" }, "*");
      return () => window.removeEventListener("message", onMsg);
    }, []);
    const dismiss = () => {
      setOpen(false);
      window.parent.postMessage({ type: "__edit_mode_dismissed" }, "*");
    };
    const onDragStart = (e) => {
      const panel = dragRef.current;
      if (!panel) return;
      const r = panel.getBoundingClientRect();
      const sx = e.clientX, sy = e.clientY;
      const startRight = window.innerWidth - r.right;
      const startBottom = window.innerHeight - r.bottom;
      const move = (ev) => {
        offsetRef.current = {
          x: startRight - (ev.clientX - sx),
          y: startBottom - (ev.clientY - sy)
        };
        clampToViewport();
      };
      const up = () => {
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", up);
      };
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
    };
    if (!open) return null;
    return /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("style", null, __TWEAKS_STYLE), /* @__PURE__ */ React.createElement(
      "div",
      {
        ref: dragRef,
        className: "twk-panel",
        "data-omelette-chrome": "",
        style: { right: offsetRef.current.x, bottom: offsetRef.current.y }
      },
      /* @__PURE__ */ React.createElement("div", { className: "twk-hd", onMouseDown: onDragStart }, /* @__PURE__ */ React.createElement("b", null, title), /* @__PURE__ */ React.createElement(
        "button",
        {
          className: "twk-x",
          "aria-label": "Close tweaks",
          onMouseDown: (e) => e.stopPropagation(),
          onClick: dismiss
        },
        "\u2715"
      )),
      /* @__PURE__ */ React.createElement("div", { className: "twk-body" }, children)
    ));
  }
  function TweakSection({ label, children }) {
    return /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "twk-sect" }, label), children);
  }
  function TweakRow({ label, value, children, inline = false }) {
    return /* @__PURE__ */ React.createElement("div", { className: inline ? "twk-row twk-row-h" : "twk-row" }, /* @__PURE__ */ React.createElement("div", { className: "twk-lbl" }, /* @__PURE__ */ React.createElement("span", null, label), value != null && /* @__PURE__ */ React.createElement("span", { className: "twk-val" }, value)), children);
  }
  function TweakSlider({ label, value, min = 0, max = 100, step = 1, unit = "", onChange }) {
    return /* @__PURE__ */ React.createElement(TweakRow, { label, value: `${value}${unit}` }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "range",
        className: "twk-slider",
        min,
        max,
        step,
        value,
        onChange: (e) => onChange(Number(e.target.value))
      }
    ));
  }
  function TweakToggle({ label, value, onChange }) {
    return /* @__PURE__ */ React.createElement("div", { className: "twk-row twk-row-h" }, /* @__PURE__ */ React.createElement("div", { className: "twk-lbl" }, /* @__PURE__ */ React.createElement("span", null, label)), /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        className: "twk-toggle",
        "data-on": value ? "1" : "0",
        role: "switch",
        "aria-checked": !!value,
        onClick: () => onChange(!value)
      },
      /* @__PURE__ */ React.createElement("i", null)
    ));
  }
  function TweakRadio({ label, value, options, onChange }) {
    var _a;
    const trackRef = React.useRef(null);
    const [dragging, setDragging] = React.useState(false);
    const valueRef = React.useRef(value);
    valueRef.current = value;
    const labelLen = (o) => String(typeof o === "object" ? o.label : o).length;
    const maxLen = options.reduce((m, o) => Math.max(m, labelLen(o)), 0);
    const fitsAsSegments = maxLen <= ((_a = { 2: 16, 3: 10 }[options.length]) != null ? _a : 0);
    if (!fitsAsSegments) {
      const resolve = (s) => {
        const m = options.find((o) => String(typeof o === "object" ? o.value : o) === s);
        return m === void 0 ? s : typeof m === "object" ? m.value : m;
      };
      return /* @__PURE__ */ React.createElement(
        TweakSelect,
        {
          label,
          value,
          options,
          onChange: (s) => onChange(resolve(s))
        }
      );
    }
    const opts = options.map((o) => typeof o === "object" ? o : { value: o, label: o });
    const idx = Math.max(0, opts.findIndex((o) => o.value === value));
    const n = opts.length;
    const segAt = (clientX) => {
      const r = trackRef.current.getBoundingClientRect();
      const inner = r.width - 4;
      const i = Math.floor((clientX - r.left - 2) / inner * n);
      return opts[Math.max(0, Math.min(n - 1, i))].value;
    };
    const onPointerDown = (e) => {
      setDragging(true);
      const v0 = segAt(e.clientX);
      if (v0 !== valueRef.current) onChange(v0);
      const move = (ev) => {
        if (!trackRef.current) return;
        const v = segAt(ev.clientX);
        if (v !== valueRef.current) onChange(v);
      };
      const up = () => {
        setDragging(false);
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    };
    return /* @__PURE__ */ React.createElement(TweakRow, { label }, /* @__PURE__ */ React.createElement(
      "div",
      {
        ref: trackRef,
        role: "radiogroup",
        onPointerDown,
        className: dragging ? "twk-seg dragging" : "twk-seg"
      },
      /* @__PURE__ */ React.createElement(
        "div",
        {
          className: "twk-seg-thumb",
          style: {
            left: `calc(2px + ${idx} * (100% - 4px) / ${n})`,
            width: `calc((100% - 4px) / ${n})`
          }
        }
      ),
      opts.map((o) => /* @__PURE__ */ React.createElement("button", { key: o.value, type: "button", role: "radio", "aria-checked": o.value === value }, o.label))
    ));
  }
  function TweakSelect({ label, value, options, onChange }) {
    return /* @__PURE__ */ React.createElement(TweakRow, { label }, /* @__PURE__ */ React.createElement("select", { className: "twk-field", value, onChange: (e) => onChange(e.target.value) }, options.map((o) => {
      const v = typeof o === "object" ? o.value : o;
      const l = typeof o === "object" ? o.label : o;
      return /* @__PURE__ */ React.createElement("option", { key: v, value: v }, l);
    })));
  }
  function TweakText({ label, value, placeholder, onChange }) {
    return /* @__PURE__ */ React.createElement(TweakRow, { label }, /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "twk-field",
        type: "text",
        value,
        placeholder,
        onChange: (e) => onChange(e.target.value)
      }
    ));
  }
  function TweakNumber({ label, value, min, max, step = 1, unit = "", onChange }) {
    const clamp = (n) => {
      if (min != null && n < min) return min;
      if (max != null && n > max) return max;
      return n;
    };
    const startRef = React.useRef({ x: 0, val: 0 });
    const onScrubStart = (e) => {
      e.preventDefault();
      startRef.current = { x: e.clientX, val: value };
      const decimals = (String(step).split(".")[1] || "").length;
      const move = (ev) => {
        const dx = ev.clientX - startRef.current.x;
        const raw = startRef.current.val + dx * step;
        const snapped = Math.round(raw / step) * step;
        onChange(clamp(Number(snapped.toFixed(decimals))));
      };
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "twk-num" }, /* @__PURE__ */ React.createElement("span", { className: "twk-num-lbl", onPointerDown: onScrubStart }, label), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        value,
        min,
        max,
        step,
        onChange: (e) => onChange(clamp(Number(e.target.value)))
      }
    ), unit && /* @__PURE__ */ React.createElement("span", { className: "twk-num-unit" }, unit));
  }
  function __twkIsLight(hex) {
    const h = String(hex).replace("#", "");
    const x = h.length === 3 ? h.replace(/./g, (c) => c + c) : h.padEnd(6, "0");
    const n = parseInt(x.slice(0, 6), 16);
    if (Number.isNaN(n)) return true;
    const r = n >> 16 & 255, g = n >> 8 & 255, b = n & 255;
    return r * 299 + g * 587 + b * 114 > 148e3;
  }
  const __TwkCheck = ({ light }) => /* @__PURE__ */ React.createElement("svg", { viewBox: "0 0 14 14", "aria-hidden": "true" }, /* @__PURE__ */ React.createElement(
    "path",
    {
      d: "M3 7.2 5.8 10 11 4.2",
      fill: "none",
      strokeWidth: "2.2",
      strokeLinecap: "round",
      strokeLinejoin: "round",
      stroke: light ? "rgba(0,0,0,.78)" : "#fff"
    }
  ));
  function TweakColor({ label, value, options, onChange }) {
    if (!options || !options.length) {
      return /* @__PURE__ */ React.createElement("div", { className: "twk-row twk-row-h" }, /* @__PURE__ */ React.createElement("div", { className: "twk-lbl" }, /* @__PURE__ */ React.createElement("span", null, label)), /* @__PURE__ */ React.createElement(
        "input",
        {
          type: "color",
          className: "twk-swatch",
          value,
          onChange: (e) => onChange(e.target.value)
        }
      ));
    }
    const key = (o) => String(JSON.stringify(o)).toLowerCase();
    const cur = key(value);
    return /* @__PURE__ */ React.createElement(TweakRow, { label }, /* @__PURE__ */ React.createElement("div", { className: "twk-chips", role: "radiogroup" }, options.map((o, i) => {
      const colors = Array.isArray(o) ? o : [o];
      const [hero, ...rest] = colors;
      const sup = rest.slice(0, 4);
      const on = key(o) === cur;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: i,
          type: "button",
          className: "twk-chip",
          role: "radio",
          "aria-checked": on,
          "data-on": on ? "1" : "0",
          "aria-label": colors.join(", "),
          title: colors.join(" \xB7 "),
          style: { background: hero },
          onClick: () => onChange(o)
        },
        sup.length > 0 && /* @__PURE__ */ React.createElement("span", null, sup.map((c, j) => /* @__PURE__ */ React.createElement("i", { key: j, style: { background: c } }))),
        on && /* @__PURE__ */ React.createElement(__TwkCheck, { light: __twkIsLight(hero) })
      );
    })));
  }
  function TweakButton({ label, onClick, secondary = false }) {
    return /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        className: secondary ? "twk-btn secondary" : "twk-btn",
        onClick
      },
      label
    );
  }
  Object.assign(window, {
    useTweaks,
    TweaksPanel,
    TweakSection,
    TweakRow,
    TweakSlider,
    TweakToggle,
    TweakRadio,
    TweakSelect,
    TweakText,
    TweakNumber,
    TweakColor,
    TweakButton
  });
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
    send: "M22 2L11 13M22 2l-7 20-4-9-9-4z"
  };
  function Icon({ name, size = 18, className = "", style }) {
    const d = ICONS[name] || "";
    const parts = d.split("|");
    return /* @__PURE__ */ React.createElement(
      "svg",
      {
        className: "icn " + className,
        width: size,
        height: size,
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        strokeWidth: "2",
        strokeLinecap: "round",
        strokeLinejoin: "round",
        style,
        "aria-hidden": "true"
      },
      parts.map((p, i) => /* @__PURE__ */ React.createElement("path", { key: i, d: p }))
    );
  }
  function Frame({ route = "video-to-note.app", children, style }) {
    return /* @__PURE__ */ React.createElement("div", { className: "frame", style }, /* @__PURE__ */ React.createElement("div", { className: "frame-bar" }, /* @__PURE__ */ React.createElement("span", { className: "dots" }, /* @__PURE__ */ React.createElement("i", null), /* @__PURE__ */ React.createElement("i", null), /* @__PURE__ */ React.createElement("i", null)), /* @__PURE__ */ React.createElement("span", { className: "urlbar" }, route), /* @__PURE__ */ React.createElement("span", { style: { width: 40 } })), /* @__PURE__ */ React.createElement("div", { className: "frame-body" }, children));
  }
  function Lines({ rows = ["w90", "w80", "w90", "w60"], gap }) {
    return /* @__PURE__ */ React.createElement("div", { className: "lines", style: gap ? { gap } : null }, rows.map((w, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "ln " + w })));
  }
  function ImgPh({ tag, cap, height = 110, style }) {
    return /* @__PURE__ */ React.createElement("div", { className: "imgph wob", style: { height, ...style } }, tag && /* @__PURE__ */ React.createElement("span", { className: "tag" }, tag), cap && /* @__PURE__ */ React.createElement("span", { className: "cap" }, cap));
  }
  function Cls({ kind }) {
    const label = { text_led: "text_led", visual_led: "visual_led", mixed: "mixed" }[kind];
    const cls = { text_led: "text", visual_led: "visual", mixed: "mixed" }[kind];
    return /* @__PURE__ */ React.createElement("span", { className: "chip " + cls }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), label);
  }
  function Anno({ n, children, style }) {
    return /* @__PURE__ */ React.createElement("div", { className: "anno", style }, n && /* @__PURE__ */ React.createElement("span", { className: "anno-pin" }, n), /* @__PURE__ */ React.createElement("span", null, children));
  }
  function StageRail({ phase = 2, withStyle = true }) {
    const phases = ["resolving", "acquiring", "analyzing", "segmenting", "drafting"];
    const branches = ["transcribe", "index", ...withStyle ? ["style"] : []];
    return /* @__PURE__ */ React.createElement("div", { className: "stage-rail2" }, phases.map((p, i) => {
      const state = i < phase ? "done" : i === phase ? "now" : "todo";
      return /* @__PURE__ */ React.createElement(React.Fragment, { key: p }, /* @__PURE__ */ React.createElement("div", { className: "stage2 " + state }, /* @__PURE__ */ React.createElement("div", { className: "stage2-row" }, /* @__PURE__ */ React.createElement("span", { className: "stage-mark" }, state === "done" ? /* @__PURE__ */ React.createElement(Icon, { name: "check", size: 13 }) : state === "now" ? /* @__PURE__ */ React.createElement(Icon, { name: "loader", size: 13 }) : /* @__PURE__ */ React.createElement("span", { className: "stage-num" }, i + 1)), /* @__PURE__ */ React.createElement("span", { className: "stage-name mono" }, p)), p === "analyzing" && /* @__PURE__ */ React.createElement("div", { className: "stage-branches" }, branches.map((b) => /* @__PURE__ */ React.createElement("span", { key: b, className: "branch-chip" + (b === "style" ? " style" : "") }, b === "style" && /* @__PURE__ */ React.createElement(Icon, { name: "sparkle", size: 11 }), b)))), i < phases.length - 1 && /* @__PURE__ */ React.createElement("span", { className: "stage2-conn" }));
    }));
  }
  Object.assign(window, { Icon, Frame, Lines, ImgPh, Cls, Anno, StageRail });
  const DEPTHS = [
    { k: "thorough", t: "Thorough", s: "Capture detail, like you're learning it." },
    { k: "balanced", t: "Balanced", s: "The useful middle." },
    { k: "brief", t: "Brief", s: "High-level takeaways." },
    { k: "custom", t: "I'll prompt it", s: "Describe exactly what you want." }
  ];
  const SUBMIT_PH = "https://www.youtube.com/watch?v=\u2026   \xB7   or a Build / Ignite session URL";
  function FlowMap() {
    const nodes = [
      { n: "1", t: "Login", r: "/login", d: "Single shared credential", ic: "lock" },
      { n: "2", t: "Submit", r: "/", d: "URL \xB7 depth \xB7 style examples", ic: "link" },
      { n: "3", t: "Progress", r: "/jobs/[id]", d: "Stages stream over SSE", ic: "loader" },
      { n: "4", t: "Review", r: "/jobs/[id]", d: "Edit notes, sections, shots", ic: "edit" },
      { n: "5", t: "Export", r: "\u2026/export", d: "Download note.md + images", ic: "download" }
    ];
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "screen-head" }, /* @__PURE__ */ React.createElement("h2", null, /* @__PURE__ */ React.createElement(Icon, { name: "arrowRight", size: 22 }), " Navigation flow"), /* @__PURE__ */ React.createElement("p", null, "Five surfaces, one linear path. Progress and Review live on the same route \u2014 the progress view morphs into the editor as sections stream in.")), /* @__PURE__ */ React.createElement("div", { className: "frame" }, /* @__PURE__ */ React.createElement("div", { className: "frame-body", style: { padding: "calc(34px * var(--d))" } }, /* @__PURE__ */ React.createElement("div", { className: "flow-row" }, nodes.map((nd, i) => /* @__PURE__ */ React.createElement(React.Fragment, { key: nd.n }, /* @__PURE__ */ React.createElement("div", { className: "flow-node wob" + (i % 2 ? " tilt" : "") }, /* @__PURE__ */ React.createElement("div", { className: "flow-top" }, /* @__PURE__ */ React.createElement("span", { className: "flow-num mono" }, nd.n), /* @__PURE__ */ React.createElement(Icon, { name: nd.ic, size: 18 })), /* @__PURE__ */ React.createElement("div", { className: "flow-title label" }, nd.t), /* @__PURE__ */ React.createElement("div", { className: "mono flow-route" }, nd.r), /* @__PURE__ */ React.createElement("div", { className: "sublabel flow-desc" }, nd.d)), i < nodes.length - 1 && /* @__PURE__ */ React.createElement("div", { className: "flow-arrow" }, /* @__PURE__ */ React.createElement(Icon, { name: "arrowRight", size: 26 }))))), /* @__PURE__ */ React.createElement("div", { className: "flow-loops" }, /* @__PURE__ */ React.createElement("div", { className: "flow-loop anno" }, /* @__PURE__ */ React.createElement("span", { className: "anno-pin" }, "\u21BB"), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Review loops:"), " regenerate a section, split / merge boundaries, restore a prior revision, capture a frame \u2014 all synchronous, no re-queue.")), /* @__PURE__ */ React.createElement("div", { className: "flow-loop anno" }, /* @__PURE__ */ React.createElement("span", { className: "anno-pin" }, "!"), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Same route, two modes:"), " ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "/jobs/[id]"), " starts as Progress and becomes Review without a navigation."))))));
  }
  function Login() {
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "screen-head" }, /* @__PURE__ */ React.createElement("h2", null, /* @__PURE__ */ React.createElement(Icon, { name: "lock", size: 20 }), " Login"), /* @__PURE__ */ React.createElement("span", { className: "route" }, "/login"), /* @__PURE__ */ React.createElement("p", null, "A single shared username + password gates the whole app. Success sets a signed httpOnly session cookie \u2014 the SSE stream rides the same cookie.")), /* @__PURE__ */ React.createElement(Frame, { route: "video-to-note.app/login" }, /* @__PURE__ */ React.createElement("div", { className: "login-wrap" }, /* @__PURE__ */ React.createElement("div", { className: "login-card box flat wob" }, /* @__PURE__ */ React.createElement("div", { className: "brand", style: { fontSize: 22, marginBottom: 4 } }, /* @__PURE__ */ React.createElement("span", { className: "mark" }, /* @__PURE__ */ React.createElement(Icon, { name: "file", size: 15 })), " Video-to-Note"), /* @__PURE__ */ React.createElement("div", { className: "sublabel", style: { marginBottom: 20 } }, "A reading room for talks."), /* @__PURE__ */ React.createElement("div", { className: "eyebrow", style: { marginBottom: 6 } }, "Username"), /* @__PURE__ */ React.createElement("div", { className: "input", style: { marginBottom: 14 } }, "shared-user"), /* @__PURE__ */ React.createElement("div", { className: "eyebrow", style: { marginBottom: 6 } }, "Password"), /* @__PURE__ */ React.createElement("div", { className: "input", style: { marginBottom: 20 } }, "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"), /* @__PURE__ */ React.createElement("button", { className: "btn primary wob", style: { width: "100%", justifyContent: "center" } }, "Sign in ", /* @__PURE__ */ React.createElement(Icon, { name: "arrowRight", size: 16 }))), /* @__PURE__ */ React.createElement(Anno, { n: "i", style: { marginTop: 20, maxWidth: 380 } }, "Shared login = no per-person attribution. Swaps cleanly to Entra ID later behind the same cookie boundary."))));
  }
  function DepthCard({ d, sel, big }) {
    return /* @__PURE__ */ React.createElement("div", { className: "depth-card box wob" + (sel ? " sel" : "") + (big ? " big" : "") }, /* @__PURE__ */ React.createElement("div", { className: "row between center" }, /* @__PURE__ */ React.createElement("span", { className: "label", style: { fontSize: big ? 17 : 15 } }, d.t), /* @__PURE__ */ React.createElement(Icon, { name: "help", size: 16, className: "muted" })), /* @__PURE__ */ React.createElement("div", { className: "sublabel", style: { marginTop: 4 } }, d.s), sel && /* @__PURE__ */ React.createElement("span", { className: "depth-tick" }, /* @__PURE__ */ React.createElement(Icon, { name: "check", size: 13 })));
  }
  function StylePanel() {
    const [open, setOpen] = React.useState(true);
    return /* @__PURE__ */ React.createElement("div", { className: "style-panel box wob", style: { marginTop: 14 } }, /* @__PURE__ */ React.createElement("button", { className: "style-head", onClick: () => setOpen((o) => !o) }, /* @__PURE__ */ React.createElement("span", { className: "row center", style: { gap: 9 } }, /* @__PURE__ */ React.createElement(Icon, { name: "sparkle", size: 16, className: "muted" }), /* @__PURE__ */ React.createElement("span", { className: "label" }, "Match my style"), /* @__PURE__ */ React.createElement("span", { className: "sublabel", style: { fontSize: 13 } }, "optional")), /* @__PURE__ */ React.createElement(Icon, { name: "chevron", size: 16, className: "muted", style: { transform: open ? "rotate(180deg)" : "none" } })), open && /* @__PURE__ */ React.createElement("div", { className: "style-body" }, /* @__PURE__ */ React.createElement("div", { className: "style-saved row center between wob" }, /* @__PURE__ */ React.createElement("span", { className: "row center", style: { gap: 9 } }, /* @__PURE__ */ React.createElement("span", { className: "depth-radio", style: { borderRadius: 5 } }, /* @__PURE__ */ React.createElement("span", { className: "depth-radio-dot", style: { borderRadius: 2 } })), /* @__PURE__ */ React.createElement("span", { className: "label", style: { fontSize: 14 } }, "Use my saved style"), /* @__PURE__ */ React.createElement("span", { className: "chip mono" }, "2 notes")), /* @__PURE__ */ React.createElement("span", { className: "anno" }, "pre-checked if a default exists")), /* @__PURE__ */ React.createElement("div", { className: "style-or" }, /* @__PURE__ */ React.createElement("span", null, "or add examples for this job")), /* @__PURE__ */ React.createElement("div", { className: "style-drop wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "upload", size: 20, className: "muted" }), /* @__PURE__ */ React.createElement("div", { className: "sublabel", style: { textAlign: "center" } }, "Drop ", /* @__PURE__ */ React.createElement("b", null, ".md"), " files, or ", /* @__PURE__ */ React.createElement("span", { style: { color: "var(--accent)" } }, "browse"), " \xB7 paste markdown"), /* @__PURE__ */ React.createElement("div", { className: "row center wrap", style: { gap: 8, justifyContent: "center", marginTop: 4 } }, /* @__PURE__ */ React.createElement("span", { className: "chip mono" }, /* @__PURE__ */ React.createElement(Icon, { name: "file", size: 12 }), " my-talk-notes.md ", /* @__PURE__ */ React.createElement(Icon, { name: "x", size: 11 })), /* @__PURE__ */ React.createElement("span", { className: "chip mono" }, /* @__PURE__ */ React.createElement(Icon, { name: "file", size: 12 }), " kubecon-2024.md ", /* @__PURE__ */ React.createElement(Icon, { name: "x", size: 11 })))), /* @__PURE__ */ React.createElement("label", { className: "style-toggle row center", style: { gap: 9 } }, /* @__PURE__ */ React.createElement("span", { className: "wf-switch" }, /* @__PURE__ */ React.createElement("span", { className: "wf-knob" })), /* @__PURE__ */ React.createElement("span", { className: "sublabel", style: { fontSize: 13.5 } }, "Save as my default style for future jobs")), /* @__PURE__ */ React.createElement(Anno, { style: { marginTop: 2 } }, "Examples steer format, voice & detail; ", /* @__PURE__ */ React.createElement("b", null, "depth"), " fills in anything they don't pin down. Style/format reference only \u2014 never a source of facts.")));
  }
  function SubmitA() {
    return /* @__PURE__ */ React.createElement(Frame, { route: "video-to-note.app/" }, /* @__PURE__ */ React.createElement("div", { className: "submit-centered" }, /* @__PURE__ */ React.createElement("div", { className: "eyebrow", style: { textAlign: "center" } }, "Submit a talk"), /* @__PURE__ */ React.createElement("h3", { className: "submit-h" }, "Turn a conference talk into reviewed notes."), /* @__PURE__ */ React.createElement("div", { className: "row", style: { gap: 10, marginTop: 6 } }, /* @__PURE__ */ React.createElement("div", { className: "input lg grow row center", style: { gap: 10 } }, /* @__PURE__ */ React.createElement(Icon, { name: "link", size: 17, className: "muted" }), /* @__PURE__ */ React.createElement("span", { className: "grow", style: { color: "var(--line-3)" } }, SUBMIT_PH)), /* @__PURE__ */ React.createElement("button", { className: "btn primary wob", style: { alignSelf: "stretch", padding: "0 20px" } }, "Submit ", /* @__PURE__ */ React.createElement(Icon, { name: "arrowRight", size: 16 }))), /* @__PURE__ */ React.createElement("div", { className: "row between center", style: { marginTop: 26, marginBottom: 12 } }, /* @__PURE__ */ React.createElement("span", { className: "eyebrow" }, "Note depth"), /* @__PURE__ */ React.createElement(Anno, null, "\u201C?\u201D help on each card")), /* @__PURE__ */ React.createElement("div", { className: "depth-grid" }, DEPTHS.map((d, i) => /* @__PURE__ */ React.createElement(DepthCard, { key: d.k, d, sel: i === 0 }))), /* @__PURE__ */ React.createElement("div", { className: "custom-reveal box sunken wob", style: { marginTop: 14 } }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 8, marginBottom: 8 } }, /* @__PURE__ */ React.createElement(Icon, { name: "edit", size: 15, className: "muted" }), /* @__PURE__ */ React.createElement("span", { className: "sublabel" }, "Custom prompt \u2014 shown only for \u201CI'll prompt it\u201D")), /* @__PURE__ */ React.createElement(Lines, { rows: ["w90", "w70"] })), /* @__PURE__ */ React.createElement(StylePanel, null), /* @__PURE__ */ React.createElement("div", { className: "banner info wob", style: { marginTop: 16 } }, /* @__PURE__ */ React.createElement(Icon, { name: "warn", size: 16, className: "b-ic" }), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Est. ~$1.42"), " for this video \u2014 shown up front, warns but never blocks."))));
  }
  function Submit() {
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "screen-head" }, /* @__PURE__ */ React.createElement("h2", null, /* @__PURE__ */ React.createElement(Icon, { name: "link", size: 20 }), " Submit"), /* @__PURE__ */ React.createElement("span", { className: "route" }, "/"), /* @__PURE__ */ React.createElement("p", null, "Where a run begins: a URL, a note-depth choice, optional style examples, and an up-front cost estimate.")), /* @__PURE__ */ React.createElement(SubmitA, null));
  }
  Object.assign(window, { FlowMap, Login, Submit });
  const SECTIONS = [
    { i: 1, t: "Opening & session goals", c: "text_led", r: "0:00 \u2013 4:12", st: "ready" },
    { i: 2, t: "Architecture overview", c: "mixed", r: "4:12 \u2013 12:40", st: "ready" },
    { i: 3, t: "Live demo: deploy worker", c: "visual_led", r: "12:40 \u2013 24:05", st: "ready" },
    { i: 4, t: "Q&A", c: "text_led", r: "24:05 \u2013 31:20", st: "ready" }
  ];
  function Scrubber({ compact }) {
    return /* @__PURE__ */ React.createElement("div", { className: "scrubber box flat wob" }, /* @__PURE__ */ React.createElement(ImgPh, { tag: "video proxy \xB7 720p", height: compact ? 120 : 150, style: { border: "none", borderRadius: 0 } }), /* @__PURE__ */ React.createElement("div", { className: "scrub-controls" }, /* @__PURE__ */ React.createElement("button", { className: "btn icon sm wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "play", size: 14 })), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 12 } }, "12:40 / 31:20"), /* @__PURE__ */ React.createElement("div", { className: "scrub-track" }, /* @__PURE__ */ React.createElement("span", { className: "scrub-fill", style: { width: "41%" } }), [8, 22, 41, 77].map((p) => /* @__PURE__ */ React.createElement("span", { key: p, className: "scrub-mark", style: { left: p + "%" } })), /* @__PURE__ */ React.createElement("span", { className: "scrub-head", style: { left: "41%" } }))), /* @__PURE__ */ React.createElement("button", { className: "btn sm wob", style: { margin: "10px", marginTop: 0 } }, /* @__PURE__ */ React.createElement(Icon, { name: "camera", size: 14 }), " Capture frame here"));
  }
  function Outline({ active = 3 }) {
    return /* @__PURE__ */ React.createElement("div", { className: "outline box flat wob" }, /* @__PURE__ */ React.createElement("div", { className: "row between center", style: { marginBottom: 10 } }, /* @__PURE__ */ React.createElement("span", { className: "eyebrow" }, "Outline"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11 } }, "4 sections")), /* @__PURE__ */ React.createElement("div", { className: "col", style: { gap: 2 } }, SECTIONS.map((s) => /* @__PURE__ */ React.createElement("div", { key: s.i, className: "outline-item" + (s.i === active ? " on" : "") }, /* @__PURE__ */ React.createElement("span", { className: "mono outline-num" }, String(s.i).padStart(2, "0")), /* @__PURE__ */ React.createElement("span", { className: "grow outline-t" }, s.t), /* @__PURE__ */ React.createElement(Cls, { kind: s.c })))));
  }
  function SectionActions({ size = "", structuralDisabled, menu }) {
    const dis = structuralDisabled ? " is-disabled" : "";
    return /* @__PURE__ */ React.createElement("div", { className: "sec-actions" }, /* @__PURE__ */ React.createElement("div", { className: "row wrap", style: { gap: 8 } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost " + size }, /* @__PURE__ */ React.createElement(Icon, { name: "refresh", size: 14 }), " Regenerate"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost " + size + dis, title: structuralDisabled ? "available once drafting finishes" : "" }, /* @__PURE__ */ React.createElement(Icon, { name: "scissors", size: 14 }), " Split"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost " + size + dis, title: structuralDisabled ? "available once drafting finishes" : "" }, /* @__PURE__ */ React.createElement(Icon, { name: "merge", size: 14 }), " Merge up"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost " + size + (menu === "revisions" ? " on" : "") }, /* @__PURE__ */ React.createElement(Icon, { name: "history", size: 14 }), " Revisions"), structuralDisabled && /* @__PURE__ */ React.createElement("span", { className: "anno", style: { alignSelf: "center" } }, "Split / Merge disabled until ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "done"))), menu === "revisions" && /* @__PURE__ */ React.createElement(RevisionsMenu, null), menu === "regen" && /* @__PURE__ */ React.createElement(RegenWarning, null));
  }
  function RevisionsMenu() {
    const revs = [
      { v: "v3", t: "Current (edited)", meta: "your edits \xB7 just now", cur: true },
      { v: "v2", t: "Regenerated", meta: "depth: thorough \xB7 2m ago" },
      { v: "v1", t: "Original draft", meta: "first pass \xB7 4m ago" }
    ];
    return /* @__PURE__ */ React.createElement("div", { className: "popover rev-menu wob" }, /* @__PURE__ */ React.createElement("div", { className: "pop-head" }, /* @__PURE__ */ React.createElement("span", { className: "eyebrow" }, "Revisions"), /* @__PURE__ */ React.createElement(Icon, { name: "x", size: 14, className: "muted" })), /* @__PURE__ */ React.createElement("div", { className: "col", style: { gap: 2 } }, revs.map((r) => /* @__PURE__ */ React.createElement("div", { key: r.v, className: "rev-row" + (r.cur ? " cur" : "") }, /* @__PURE__ */ React.createElement("span", { className: "mono rev-v" }, r.v), /* @__PURE__ */ React.createElement("div", { className: "grow" }, /* @__PURE__ */ React.createElement("div", { className: "label", style: { fontSize: 13 } }, r.t), /* @__PURE__ */ React.createElement("div", { className: "sublabel", style: { fontSize: 12 } }, r.meta)), r.cur ? /* @__PURE__ */ React.createElement("span", { className: "chip mono" }, "current") : /* @__PURE__ */ React.createElement("button", { className: "btn sm wob" }, "Restore")))));
  }
  function RegenWarning() {
    return /* @__PURE__ */ React.createElement("div", { className: "popover regen-warn wob" }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 8, marginBottom: 6 } }, /* @__PURE__ */ React.createElement(Icon, { name: "warn", size: 16, style: { color: "var(--cls-visual)" } }), /* @__PURE__ */ React.createElement("span", { className: "label", style: { fontSize: 14 } }, "Regenerate section?")), /* @__PURE__ */ React.createElement("div", { className: "sublabel", style: { fontSize: 13, marginBottom: 12, lineHeight: 1.45 } }, "This replaces your manual edits with a fresh draft. A snapshot is saved to ", /* @__PURE__ */ React.createElement("b", null, "Revisions"), " first \u2014 you can always restore it."), /* @__PURE__ */ React.createElement("div", { className: "row", style: { gap: 8, justifyContent: "flex-end" } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm wob" }, "Keep my edits"), /* @__PURE__ */ React.createElement("button", { className: "btn primary sm wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "refresh", size: 13 }), " Regenerate anyway")));
  }
  function ShotTray({ degraded }) {
    return /* @__PURE__ */ React.createElement("div", { className: "shot-tray" }, /* @__PURE__ */ React.createElement("div", { className: "row between center", style: { marginBottom: 8 } }, /* @__PURE__ */ React.createElement("span", { className: "eyebrow" }, "Screenshots"), /* @__PURE__ */ React.createElement("span", { className: "anno" }, "toggle \xB7 caption \xB7 reorder \xB7 delete")), /* @__PURE__ */ React.createElement("div", { className: "row wrap", style: { gap: 10 } }, [1, 2, 3].map((n) => /* @__PURE__ */ React.createElement("div", { key: n, className: "shot" }, /* @__PURE__ */ React.createElement(ImgPh, { cap: "0:1" + n + ":40", height: 74, style: { width: 124 } }), /* @__PURE__ */ React.createElement("span", { className: "shot-pick" + (n < 3 ? " on" : "") }, n < 3 ? /* @__PURE__ */ React.createElement(Icon, { name: "check", size: 12 }) : null))), degraded ? /* @__PURE__ */ React.createElement("div", { className: "shot-add wob is-disabled", title: "re-download the proxy to capture" }, /* @__PURE__ */ React.createElement(Icon, { name: "camera", size: 16 }), /* @__PURE__ */ React.createElement("span", { className: "sublabel", style: { fontSize: 11 } }, "capture off")) : /* @__PURE__ */ React.createElement("button", { className: "shot-add wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "plus", size: 18 }), /* @__PURE__ */ React.createElement("span", { className: "sublabel", style: { fontSize: 12 } }, "Capture"))));
  }
  function MediaUnavailable() {
    return /* @__PURE__ */ React.createElement("div", { className: "box flat wob media-gone" }, /* @__PURE__ */ React.createElement("div", { className: "media-gone-art" }, /* @__PURE__ */ React.createElement(Icon, { name: "youtube", size: 26, className: "muted" }), /* @__PURE__ */ React.createElement("span", { className: "media-gone-x" }, /* @__PURE__ */ React.createElement(Icon, { name: "x", size: 14 }))), /* @__PURE__ */ React.createElement("div", { className: "media-gone-body" }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 7 } }, /* @__PURE__ */ React.createElement(Icon, { name: "warn", size: 15, style: { color: "var(--cls-visual)" } }), /* @__PURE__ */ React.createElement("span", { className: "label", style: { fontSize: 14, whiteSpace: "nowrap" } }, "Proxy expired")), /* @__PURE__ */ React.createElement("div", { className: "sublabel", style: { fontSize: 12.5, lineHeight: 1.45 } }, "The scrub proxy was cleaned up (7-day TTL). Existing screenshots are kept; re-download to scrub or capture new frames."), /* @__PURE__ */ React.createElement("button", { className: "btn sm wob", style: { alignSelf: "flex-start" } }, /* @__PURE__ */ React.createElement(Icon, { name: "download", size: 14 }), " Re-download proxy")));
  }
  function ExportBar() {
    return /* @__PURE__ */ React.createElement("div", { className: "export-bar" }, /* @__PURE__ */ React.createElement("span", { className: "row center", style: { gap: 9 } }, /* @__PURE__ */ React.createElement("span", { className: "export-badge sm" }, /* @__PURE__ */ React.createElement(Icon, { name: "check", size: 14 })), /* @__PURE__ */ React.createElement("span", { className: "sublabel", style: { fontSize: 13 } }, "4 sections \xB7 9 screenshots \xB7 reviewed")), /* @__PURE__ */ React.createElement("span", { className: "row center", style: { gap: 8 } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "eye", size: 13 }), " Preview note.md"), /* @__PURE__ */ React.createElement("button", { className: "btn primary sm wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "download", size: 14 }), " Export ZIP")));
  }
  function SectionCard({ s, mode = "preview", active, banner, menu, structuralDisabled, degraded }) {
    return /* @__PURE__ */ React.createElement("div", { className: "sec-card box wob" + (active ? " active" : ""), "data-screen-label": "section-" + s.i }, /* @__PURE__ */ React.createElement("div", { className: "row between center wrap", style: { gap: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 10 } }, /* @__PURE__ */ React.createElement("span", { className: "mono sec-num" }, String(s.i).padStart(2, "0")), /* @__PURE__ */ React.createElement("span", { className: "label sec-title" }, s.t), /* @__PURE__ */ React.createElement(Icon, { name: "edit", size: 14, className: "muted" })), /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 8 } }, /* @__PURE__ */ React.createElement(Cls, { kind: s.c }), /* @__PURE__ */ React.createElement("span", { className: "chip mono" }, /* @__PURE__ */ React.createElement(Icon, { name: "clock", size: 12 }), " ", s.r))), banner === "boundaries" && /* @__PURE__ */ React.createElement("div", { className: "banner warn wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "warn", size: 15, className: "b-ic" }), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Boundaries changed"), " \u2014 regenerate this section to fit its new span.")), /* @__PURE__ */ React.createElement("div", { className: "md-editor box sunken wob" }, /* @__PURE__ */ React.createElement("div", { className: "md-toolbar" }, /* @__PURE__ */ React.createElement("button", { className: "md-tab" + (mode === "edit" ? " on" : "") }, /* @__PURE__ */ React.createElement(Icon, { name: "edit", size: 13 }), " Edit"), /* @__PURE__ */ React.createElement("button", { className: "md-tab" + (mode === "preview" ? " on" : "") }, /* @__PURE__ */ React.createElement(Icon, { name: "eye", size: 13 }), " Preview"), /* @__PURE__ */ React.createElement("span", { className: "grow" }), /* @__PURE__ */ React.createElement("span", { className: "anno" }, "debounced PATCH \u2192 markdown_edited")), mode === "edit" ? /* @__PURE__ */ React.createElement("div", { className: "md-body mono md-src" }, /* @__PURE__ */ React.createElement("div", null, "## ", s.t), /* @__PURE__ */ React.createElement("div", { className: "ln w90" }), /* @__PURE__ */ React.createElement("div", { className: "ln w80" }), /* @__PURE__ */ React.createElement("div", null, "![demo](images/0003-demo.png)"), /* @__PURE__ */ React.createElement("div", { className: "ln w70" })) : /* @__PURE__ */ React.createElement("div", { className: "md-body md-prose" }, /* @__PURE__ */ React.createElement(Lines, { rows: ["w90", "w80", "w90"] }), /* @__PURE__ */ React.createElement(ImgPh, { cap: "0:13:40", height: 120, style: { margin: "12px 0" } }), /* @__PURE__ */ React.createElement(Lines, { rows: ["w70", "w50"] }))), /* @__PURE__ */ React.createElement(ShotTray, { degraded }), /* @__PURE__ */ React.createElement("hr", { className: "divider", style: { margin: "4px 0" } }), /* @__PURE__ */ React.createElement(SectionActions, { size: "sm", menu, structuralDisabled }));
  }
  function Progress() {
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "screen-head" }, /* @__PURE__ */ React.createElement("h2", null, /* @__PURE__ */ React.createElement(Icon, { name: "loader", size: 20 }), " Progress \u2192 review"), /* @__PURE__ */ React.createElement("span", { className: "route" }, "/jobs/[jobId]"), /* @__PURE__ */ React.createElement("p", null, "Subscribed to the SSE stream. The stage rail advances; each section pops in the moment it's drafted, so reading can start before the run finishes.")), /* @__PURE__ */ React.createElement(Frame, { route: "video-to-note.app/jobs/3f9c\u2026" }, /* @__PURE__ */ React.createElement("div", { className: "row between center wrap", style: { gap: 12, marginBottom: 16 } }, /* @__PURE__ */ React.createElement(StageRail, { phase: 4, withStyle: true }), /* @__PURE__ */ React.createElement("span", { className: "chip mono" }, /* @__PURE__ */ React.createElement(Icon, { name: "youtube", size: 12 }), " 58 min \xB7 captions")), /* @__PURE__ */ React.createElement("div", { className: "col", style: { gap: 10, marginBottom: 14 } }, /* @__PURE__ */ React.createElement("div", { className: "banner info wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "warn", size: 16, className: "b-ic" }), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Est. ~$1.42"), " \u2014 informational, never blocks. Actual cost recorded after the run.")), /* @__PURE__ */ React.createElement("div", { className: "banner ok wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "sparkle", size: 16, className: "b-ic" }), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Following your examples:"), " fine-grained sections, detailed notes. ", /* @__PURE__ */ React.createElement("span", { className: "muted" }, "Depth \u201CThorough\u201D overridden \u2014 ", /* @__PURE__ */ React.createElement("u", null, "switch back?")))), /* @__PURE__ */ React.createElement("div", { className: "banner warn wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "warn", size: 16, className: "b-ic" }), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Transcript from speech, not official captions"), " \u2014 proper nouns & code may need a closer check."))), /* @__PURE__ */ React.createElement("div", { className: "col", style: { gap: 12 } }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 8 } }, /* @__PURE__ */ React.createElement("span", { className: "eyebrow" }, "Drafting sections"), /* @__PURE__ */ React.createElement("span", { className: "anno", style: { whiteSpace: "nowrap" } }, /* @__PURE__ */ React.createElement("span", { className: "anno-pin" }, "\u2192"), " streamed by order_index")), SECTIONS.slice(0, 2).map((s, idx) => /* @__PURE__ */ React.createElement("div", { key: s.i, className: "prog-sec box wob ready" }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 10 } }, /* @__PURE__ */ React.createElement("span", { className: "mono sec-num" }, String(s.i).padStart(2, "0")), /* @__PURE__ */ React.createElement("span", { className: "label" }, s.t), /* @__PURE__ */ React.createElement(Cls, { kind: s.c }), /* @__PURE__ */ React.createElement("span", { className: "grow" }), /* @__PURE__ */ React.createElement("span", { className: "chip ok-chip" }, /* @__PURE__ */ React.createElement(Icon, { name: "check", size: 12 }), " ready")), /* @__PURE__ */ React.createElement(Lines, { rows: ["w90", "w70"], gap: 7 }), idx === 0 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("hr", { className: "divider", style: { margin: "2px 0" } }), /* @__PURE__ */ React.createElement(SectionActions, { size: "sm", structuralDisabled: true })))), /* @__PURE__ */ React.createElement("div", { className: "prog-sec box wob drafting" }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 10 } }, /* @__PURE__ */ React.createElement("span", { className: "mono sec-num" }, "03"), /* @__PURE__ */ React.createElement("span", { className: "label" }, "Live demo: deploy worker"), /* @__PURE__ */ React.createElement(Cls, { kind: "visual_led" }), /* @__PURE__ */ React.createElement("span", { className: "grow" }), /* @__PURE__ */ React.createElement("span", { className: "chip mono" }, /* @__PURE__ */ React.createElement(Icon, { name: "loader", size: 12 }), " drafting\u2026")), /* @__PURE__ */ React.createElement("div", { className: "skel" }, /* @__PURE__ */ React.createElement("span", null), /* @__PURE__ */ React.createElement("span", null), /* @__PURE__ */ React.createElement("span", null))), /* @__PURE__ */ React.createElement("div", { className: "prog-empty box sunken wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "file", size: 18, className: "muted" }), /* @__PURE__ */ React.createElement("span", { className: "sublabel" }, "Sections will appear here as they're drafted.")))), /* @__PURE__ */ React.createElement(Anno, { n: "i", style: { marginTop: 14, maxWidth: 620 } }, "Same route as Review. When the last section is ready a ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "done"), " event fires and the view is fully in edit mode \u2014 no navigation."));
  }
  function ReviewA({ state = "ready" }) {
    const degraded = state === "media";
    const banner = state === "boundaries" ? "boundaries" : null;
    const menu = state === "revisions" ? "revisions" : state === "regen" ? "regen" : null;
    return /* @__PURE__ */ React.createElement(Frame, { route: "video-to-note.app/jobs/3f9c\u2026" }, /* @__PURE__ */ React.createElement("div", { className: "rev-a" }, /* @__PURE__ */ React.createElement("aside", { className: "rev-a-rail" }, degraded ? /* @__PURE__ */ React.createElement(MediaUnavailable, null) : /* @__PURE__ */ React.createElement(Scrubber, null), /* @__PURE__ */ React.createElement(Outline, { active: 3 })), /* @__PURE__ */ React.createElement("main", { className: "rev-a-list" }, /* @__PURE__ */ React.createElement(SectionCard, { s: SECTIONS[1], mode: "preview", degraded }), /* @__PURE__ */ React.createElement(SectionCard, { s: SECTIONS[2], mode: "edit", active: true, degraded, banner, menu }))), /* @__PURE__ */ React.createElement(ExportBar, null));
  }
  function Review() {
    const [st, setSt] = React.useState("ready");
    const STATES = [
      ["ready", "Default"],
      ["revisions", "Revisions menu"],
      ["regen", "Regenerate warning"],
      ["boundaries", "Boundaries changed"],
      ["media", "Media unavailable"]
    ];
    const caps = {
      ready: "review_ready \u2014 full editing. Sticky video + outline rail; each section card has the markdown editor, classification badge, timestamp, screenshot tray, and Regenerate / Split / Merge / Revisions. ExportBar pinned at the bottom.",
      revisions: "Revisions menu \u2014 prior versions of a section (original draft, regenerated, current edits) with one-click Restore. Opened from the Revisions action.",
      regen: "Regenerate warning \u2014 regenerating a section that has manual edits asks first; a snapshot is saved to Revisions so the edits are recoverable.",
      boundaries: "Boundaries changed \u2014 after a Split or Merge, the affected section shows a non-blocking \u201Cregenerate to fit\u201D banner.",
      media: "Degraded (media_unavailable) \u2014 the scrub proxy expired (7-day TTL). The scrubber and capture affordances are hidden and replaced by a \u201Cre-download to scrub / capture\u201D action; existing screenshots remain."
    };
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "screen-head" }, /* @__PURE__ */ React.createElement("h2", null, /* @__PURE__ */ React.createElement(Icon, { name: "edit", size: 20 }), " Review editor"), /* @__PURE__ */ React.createElement("span", { className: "route" }, "/jobs/[jobId]"), /* @__PURE__ */ React.createElement("p", null, "The workhorse. Edit markdown, adjust section boundaries, regenerate a single section, swap revisions, and capture missing frames \u2014 all before export.")), /* @__PURE__ */ React.createElement("div", { className: "variants wob" }, STATES.map(([k, l]) => /* @__PURE__ */ React.createElement("button", { key: k, className: st === k ? "on" : "", onClick: () => setSt(k) }, l))), /* @__PURE__ */ React.createElement("div", { className: "variant-cap" }, caps[st]), /* @__PURE__ */ React.createElement(ReviewA, { state: st }));
  }
  function Export() {
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "screen-head" }, /* @__PURE__ */ React.createElement("h2", null, /* @__PURE__ */ React.createElement(Icon, { name: "download", size: 20 }), " Export"), /* @__PURE__ */ React.createElement("span", { className: "route" }, "/jobs/[jobId]/export"), /* @__PURE__ */ React.createElement("p", null, "Assembles a ZIP from current DB state + Blob assets: a markdown file with relative image paths, an images folder, and a metadata file for audit / re-import.")), /* @__PURE__ */ React.createElement(Frame, { route: "video-to-note.app/jobs/3f9c\u2026/export" }, /* @__PURE__ */ React.createElement("div", { className: "export-wrap" }, /* @__PURE__ */ React.createElement("div", { className: "export-card box flat wob" }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 12, marginBottom: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "export-badge" }, /* @__PURE__ */ React.createElement(Icon, { name: "check", size: 20 })), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "label", style: { fontSize: 18 } }, "Notes ready to export"), /* @__PURE__ */ React.createElement("div", { className: "sublabel" }, "4 sections \xB7 9 screenshots"))), /* @__PURE__ */ React.createElement("hr", { className: "divider", style: { margin: "14px 0" } }), /* @__PURE__ */ React.createElement("div", { className: "eyebrow", style: { marginBottom: 10 } }, "ZIP contents"), /* @__PURE__ */ React.createElement("div", { className: "file-tree mono" }, /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 8 } }, /* @__PURE__ */ React.createElement(Icon, { name: "file", size: 14 }), " note.md"), /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 8, paddingLeft: 18 } }, /* @__PURE__ */ React.createElement(Icon, { name: "image", size: 14 }), " images/ ", /* @__PURE__ */ React.createElement("span", { className: "muted" }, "0001-intro.png \xB7 0002-demo.png \xB7 \u2026")), /* @__PURE__ */ React.createElement("div", { className: "row center", style: { gap: 8 } }, /* @__PURE__ */ React.createElement(Icon, { name: "file", size: 14 }), " metadata.json")), /* @__PURE__ */ React.createElement("button", { className: "btn primary wob", style: { width: "100%", justifyContent: "center", marginTop: 18 } }, /* @__PURE__ */ React.createElement(Icon, { name: "download", size: 16 }), " Export & download ZIP")), /* @__PURE__ */ React.createElement("div", { className: "col", style: { gap: 14, maxWidth: 300 } }, /* @__PURE__ */ React.createElement(Anno, { n: "i" }, "metadata.json stores source URL, depth, transcript source + per-section / per-shot timestamps."), /* @__PURE__ */ React.createElement("div", { className: "banner ok wob" }, /* @__PURE__ */ React.createElement(Icon, { name: "check", size: 15, className: "b-ic" }), /* @__PURE__ */ React.createElement("span", null, "Reproducible \u2014 re-assembled any time from current state."))))));
  }
  Object.assign(window, { Progress, Review, Export });
  const TWEAK_DEFAULTS = (
    /*EDITMODE-BEGIN*/
    {
      "sketchy": true,
      "annotations": true,
      "density": "regular",
      "accent": "#2E5AAC"
    }
  );
  const TABS = [
    { k: "flow", n: "Flow", C: () => /* @__PURE__ */ React.createElement(FlowMap, null) },
    { k: "login", n: "Login", C: () => /* @__PURE__ */ React.createElement(Login, null) },
    { k: "submit", n: "Submit", C: () => /* @__PURE__ */ React.createElement(Submit, null) },
    { k: "progress", n: "Progress", C: () => /* @__PURE__ */ React.createElement(Progress, null) },
    { k: "review", n: "Review", C: () => /* @__PURE__ */ React.createElement(Review, null) },
    { k: "export", n: "Export", C: () => /* @__PURE__ */ React.createElement(Export, null) }
  ];
  function App() {
    const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
    const [tab, setTab] = React.useState(() => {
      const h = (location.hash || "").replace("#", "");
      return TABS.some((x) => x.k === h) ? h : "flow";
    });
    React.useEffect(() => {
      location.hash = tab;
    }, [tab]);
    const Active = (TABS.find((x) => x.k === tab) || TABS[0]).C;
    const rootStyle = {
      "--accent": t.accent,
      "--accent-soft": `color-mix(in srgb, ${t.accent} 13%, #ffffff)`
    };
    return /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "wf-root " + (t.sketchy ? "sketchy" : "clean"),
        "data-density": t.density,
        "data-annotations": t.annotations ? "on" : "off",
        style: rootStyle
      },
      /* @__PURE__ */ React.createElement("header", { className: "appbar" }, /* @__PURE__ */ React.createElement("div", { className: "brand" }, /* @__PURE__ */ React.createElement("span", { className: "mark" }, /* @__PURE__ */ React.createElement(Icon, { name: "file", size: 15 })), "Video-to-Note"), /* @__PURE__ */ React.createElement("nav", { className: "tabs" }, TABS.map((x, i) => /* @__PURE__ */ React.createElement("button", { key: x.k, className: "tab" + (tab === x.k ? " active" : ""), onClick: () => setTab(x.k) }, /* @__PURE__ */ React.createElement("span", { className: "num" }, i), x.n))), /* @__PURE__ */ React.createElement("span", { className: "spacer" }), /* @__PURE__ */ React.createElement("span", { className: "hint anno" }, t.sketchy ? "low-fi sketch" : "clean wireframe")),
      /* @__PURE__ */ React.createElement("div", { className: "canvas" }, /* @__PURE__ */ React.createElement(Active, null)),
      /* @__PURE__ */ React.createElement(TweaksPanel, null, /* @__PURE__ */ React.createElement(TweakSection, { label: "Rendering" }), /* @__PURE__ */ React.createElement(TweakToggle, { label: "Sketchy", value: t.sketchy, onChange: (v) => setTweak("sketchy", v) }), /* @__PURE__ */ React.createElement(TweakToggle, { label: "Annotations", value: t.annotations, onChange: (v) => setTweak("annotations", v) }), /* @__PURE__ */ React.createElement(
        TweakRadio,
        {
          label: "Density",
          value: t.density,
          options: ["compact", "regular", "roomy"],
          onChange: (v) => setTweak("density", v)
        }
      ), /* @__PURE__ */ React.createElement(TweakSection, { label: "Accent" }), /* @__PURE__ */ React.createElement(
        TweakColor,
        {
          label: "Accent",
          value: t.accent,
          options: ["#2E5AAC", "#2A8267", "#475569", "#7A5AE0"],
          onChange: (v) => setTweak("accent", v)
        }
      ))
    );
  }
  ReactDOM.createRoot(document.getElementById("root")).render(/* @__PURE__ */ React.createElement(App, null));
})();
