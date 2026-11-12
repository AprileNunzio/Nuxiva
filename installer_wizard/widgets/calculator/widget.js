(() => {
  const FUNCS = Object.freeze({ sin: "sin", cos: "cos", tan: "tan", asin: "asin", acos: "acos", atan: "atan", ln: "ln", log: "log", sqrt: "sqrt", abs: "abs" });
  const CONST = Object.freeze({ pi: Math.PI, e: Math.E });
  const TOKEN = /\s*(asin|acos|atan|sin|cos|tan|ln|log|sqrt|abs|pi|ans|e|\d+(?:\.\d*)?(?:e[+-]?\d+)?|\.\d+|[-+*/^%()!])/iy;
  const MAX_TOKENS = 200;
  const HISTORY = 5;
  const OPS = new Set(["+", "-", "*", "/", "^"]);

  function factorial(n) {
    if (!Number.isInteger(n) || n < 0 || n > 170) throw new RangeError("factorial");
    let r = 1;
    for (let i = 2; i <= n; i++) r *= i;
    return r;
  }

  const normalize = (src) => String(src).toLowerCase().replace(/×/g, "*").replace(/÷/g, "/").replace(/[−–]/g, "-").replace(/π/g, "pi").replace(/√/g, "sqrt").replace(/,/g, ".").replace(/\*\*/g, "^").replace(/\s+/g, "");

  function tokenize(src) {
    const out = [];
    TOKEN.lastIndex = 0;
    const text = normalize(src);
    while (TOKEN.lastIndex < text.length) {
      const m = TOKEN.exec(text);
      if (!m) throw new SyntaxError("token");
      const t = m[1].toLowerCase();
      const prev = out[out.length - 1];
      const startsValue = t === "(" || Object.hasOwn(FUNCS, t) || Object.hasOwn(CONST, t) || t === "ans" || /^[\d.]/.test(t);
      const endsValue = prev !== undefined && (prev === ")" || prev === "!" || prev === "%" || Object.hasOwn(CONST, prev) || prev === "ans" || /^[\d.]/.test(prev));
      if (startsValue && endsValue) out.push("*");
      out.push(t);
      if (out.length > MAX_TOKENS) throw new RangeError("length");
    }
    return out;
  }

  function evaluate(src, opts) {
    const tokens = tokenize(src);
    let open = 0;
    for (const t of tokens) { if (t === "(" || Object.hasOwn(FUNCS, t)) open++; else if (t === ")") open--; }
    while (open-- > 0) tokens.push(")");
    let i = 0;
    const peek = () => tokens[i];
    const next = () => tokens[i++];
    const angle = (v) => (opts.deg ? (v * Math.PI) / 180 : v);
    const inverse = (v) => (opts.deg ? (v * 180) / Math.PI : v);
    const call = (f, v) => {
      switch (f) {
        case "sin": return Math.sin(angle(v));
        case "cos": return Math.cos(angle(v));
        case "tan": return Math.tan(angle(v));
        case "asin": return inverse(Math.asin(v));
        case "acos": return inverse(Math.acos(v));
        case "atan": return inverse(Math.atan(v));
        case "ln": return Math.log(v);
        case "log": return Math.log10(v);
        case "sqrt": return Math.sqrt(v);
        default: return Math.abs(v);
      }
    };
    const primary = () => {
      const t = next();
      if (t === undefined) throw new SyntaxError("end");
      if (Object.hasOwn(FUNCS, t)) {
        const v = expression();
        if (next() !== ")") throw new SyntaxError(")");
        return call(t, v);
      }
      if (t === "(") {
        const v = expression();
        if (next() !== ")") throw new SyntaxError(")");
        return v;
      }
      if (Object.hasOwn(CONST, t)) return CONST[t];
      if (t === "ans") return opts.ans;
      const n = Number(t);
      if (!Number.isFinite(n)) throw new SyntaxError(t);
      return n;
    };
    const postfix = () => {
      let v = primary();
      while (peek() === "!" || peek() === "%") v = next() === "!" ? factorial(v) : v / 100;
      return v;
    };
    const power = () => {
      const b = postfix();
      if (peek() === "^") { next(); return b ** unary(); }
      return b;
    };
    const unary = () => {
      if (peek() === "-") { next(); return -unary(); }
      if (peek() === "+") { next(); return unary(); }
      return power();
    };
    const term = () => {
      let v = unary();
      while (peek() === "*" || peek() === "/") {
        const op = next(), r = unary();
        v = op === "*" ? v * r : v / r;
      }
      return v;
    };
    const expression = () => {
      let v = term();
      while (peek() === "+" || peek() === "-") {
        const op = next();
        const left = v;
        const r = term();
        const percent = tokens[i - 1] === "%";
        v = op === "+" ? left + (percent ? left * r : r) : left - (percent ? left * r : r);
      }
      return v;
    };
    const out = expression();
    if (i !== tokens.length || !Number.isFinite(out)) throw new SyntaxError("trailing");
    return Math.abs(out) < 1e-12 ? 0 : out;
  }

  const pretty = (src) => src.replace(/ans/g, "ANS").replace(/sqrt/g, "√").replace(/pi/g, "π").replace(/\*/g, "×").replace(/\//g, "÷").replace(/-/g, "−");

  function format(v, ctx) {
    const a = Math.abs(v);
    if (a !== 0 && (a >= 1e15 || a < 1e-9)) return v.toExponential(8).replace(/\.?0+e/, "e");
    return ctx.fmt(Number(v.toPrecision(12)), { maximumFractionDigits: 10, useGrouping: true });
  }

  const KEYS = [
    ["C", "op", "C"], ["DEL", "op", "⌫"], ["%", "op", "%"], ["/", "op", "÷"],
    ["7", "", "7"], ["8", "", "8"], ["9", "", "9"], ["*", "op", "×"],
    ["4", "", "4"], ["5", "", "5"], ["6", "", "6"], ["-", "op", "−"],
    ["1", "", "1"], ["2", "", "2"], ["3", "", "3"], ["+", "op", "+"],
    ["ans", "op", "ANS"], ["0", "", "0"], [".", "", ","], ["=", "eq", "="],
  ];
  const SCI = [
    ["sin(", "sin"], ["cos(", "cos"], ["tan(", "tan"], ["^", "xʸ"],
    ["asin(", "sin⁻¹"], ["acos(", "cos⁻¹"], ["atan(", "tan⁻¹"], ["sqrt(", "√"],
    ["ln(", "ln"], ["log(", "log"], ["(", "("], [")", ")"],
    ["pi", "π"], ["e", "e"], ["!", "n!"], ["abs(", "|x|"],
  ];

  function state(el) {
    if (!el._calc) el._calc = { src: "", sci: false, deg: true, ans: 0, history: [], fresh: false, err: false, applied: "" };
    return el._calc;
  }

  NuxivaDesk.register("calculator", {
    render(el, d, ctx) {
      const st = state(el);
      const data = d && typeof d === "object" ? d : {};
      const decimal = ctx.fmt(1.5).replace(/\d/g, "") || ".";
      el.innerHTML = `<div class="calc-wrapper" tabindex="0" role="application" aria-label="${ctx.esc(ctx.t("label"))}">
          <div class="calc-head">
            ${ctx.head({ icon: "calc", label: ctx.t("label") })}
            <button class="wk-btn calc-angle" type="button" data-act="angle" aria-pressed="${st.deg}"></button>
            <button class="wk-btn calc-mode" type="button" data-act="mode" aria-pressed="${st.sci}">${ctx.esc(ctx.t("scientific"))}</button>
          </div>
          <div class="calc-screen">
            <div class="calc-history" aria-live="polite"></div>
            <div class="calc-curr">0</div>
            <div class="calc-preview" aria-hidden="true"></div>
          </div>
          <div class="calc-grid">
            <div class="calc-sci-keys">${SCI.map(([v, l]) => `<button type="button" data-val="${ctx.esc(v)}">${ctx.esc(l)}</button>`).join("")}</div>
            <div class="calc-basic-keys">${KEYS.map(([v, c, l]) => `<button type="button" data-val="${ctx.esc(v)}"${c ? ` class="calc-${c}"` : ""}>${ctx.esc(v === "." ? decimal : l)}</button>`).join("")}</div>
          </div>
          <ol class="calc-log"></ol>
        </div>`;
      const root = el.firstElementChild;
      const histEl = root.querySelector(".calc-history");
      const currEl = root.querySelector(".calc-curr");
      const prevEl = root.querySelector(".calc-preview");
      const logEl = root.querySelector(".calc-log");
      const angleBtn = root.querySelector(".calc-angle");
      const modeBtn = root.querySelector(".calc-mode");
      const opts = () => ({ deg: st.deg, ans: st.ans });
      const shown = () => pretty(st.src).replace(/\./g, decimal);

      function paint() {
        root.classList.toggle("sci", st.sci);
        modeBtn.setAttribute("aria-pressed", String(st.sci));
        angleBtn.textContent = st.deg ? "DEG" : "RAD";
        angleBtn.setAttribute("aria-pressed", String(st.deg));
        angleBtn.hidden = !st.sci;
        root.classList.toggle("err", st.err);
        currEl.textContent = st.err ? ctx.t("error") : shown() || "0";
        currEl.classList.toggle("long", currEl.textContent.length > 14);
        let preview = "";
        if (st.src && !st.fresh && /[-+*/^%!(a-z]/i.test(st.src)) {
          try { preview = `= ${format(evaluate(st.src, opts()), ctx)}`; } catch (_) { preview = ""; }
        }
        prevEl.textContent = preview;
        logEl.innerHTML = st.history.map((h, i) => `<li><button type="button" data-hist="${i}" title="${ctx.esc(pretty(h.src))}"><span>${ctx.esc(pretty(h.src))}</span><b>${ctx.esc(format(h.value, ctx))}</b></button></li>`).join("");
      }

      function solve() {
        if (!st.src) return;
        try {
          const value = evaluate(st.src, opts());
          histEl.textContent = `${shown()} =`;
          st.history = [{ src: st.src, value }, ...st.history].slice(0, HISTORY);
          st.ans = value;
          st.src = String(Number(value.toPrecision(12)));
          if (st.src.includes("e")) st.src = value.toExponential(10);
          st.fresh = true;
          st.err = false;
        } catch (_) {
          histEl.textContent = shown();
          st.src = "";
          st.fresh = false;
          st.err = true;
        }
        paint();
      }

      function press(val) {
        st.err = false;
        if (val === "C") { st.src = ""; st.fresh = false; histEl.textContent = ""; }
        else if (val === "DEL") { st.src = st.fresh ? "" : st.src.replace(/(asin|acos|atan|sin|cos|tan|sqrt|abs|ln|log)\($|ans$|pi$|.$/, ""); st.fresh = false; }
        else if (val === "=") { solve(); return; }
        else {
          if (st.fresh) { st.src = OPS.has(val) || val === "%" || val === "!" ? "ans" : ""; st.fresh = false; }
          if (st.src.length > 160) return;
          if (val === "." && /[\d.]*$/.exec(st.src)[0].includes(".")) return;
          if (OPS.has(val) && OPS.has(st.src.slice(-1)) && !(val === "-" && st.src.slice(-1) !== "-")) st.src = st.src.slice(0, -1);
          st.src += val;
        }
        paint();
      }

      root.addEventListener("click", (e) => {
        const btn = e.target instanceof Element ? e.target.closest("button") : null;
        if (!btn || !root.contains(btn)) return;
        if (btn.dataset.act === "mode") st.sci = !st.sci;
        else if (btn.dataset.act === "angle") st.deg = !st.deg;
        else if (btn.dataset.hist !== undefined) {
          const h = st.history[Number(btn.dataset.hist)];
          if (h) { st.src = h.src; st.fresh = false; }
        } else if (btn.dataset.val) { press(btn.dataset.val); return; }
        paint();
      });

      root.addEventListener("keydown", (e) => {
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        const map = { Enter: "=", "=": "=", Backspace: "DEL", Delete: "C", Escape: "C", x: "*", X: "*", ",": ".", "^": "^" };
        const k = map[e.key] || (/^[\d.+\-*/%()!]$/.test(e.key) ? e.key : "");
        if (!k) return;
        e.preventDefault();
        press(k);
      });

      const expr = ctx.str(data.expression ?? data.expr, 160);
      if (expr && expr !== st.applied) {
        st.applied = expr;
        try { tokenize(expr); st.src = normalize(expr); st.fresh = false; solve(); }
        catch (_) { st.src = ""; }
      }
      paint();
    },
    destroy(el) { el._calc = null; },
  });
})();
