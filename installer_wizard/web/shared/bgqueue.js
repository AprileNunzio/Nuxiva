(() => {
  "use strict";
  const SVG = "http://www.w3.org/2000/svg";
  const STATUS = { queued: "bgq_status_queued", failed: "bgq_status_failed", waiting_disk: "bgq_status_disk", done: "bgq_status_done" };
  const put = (node, key, params) => {
    if (node.childElementCount) node.replaceChildren();
    return PageText.bind(node, key, params);
  };
  const raw = (node, text) => {
    if (node.childElementCount) node.replaceChildren();
    node.removeAttribute("data-i18n");
    node.removeAttribute("data-i18n-params");
    node.textContent = text;
  };
  const FAREWELL_MS = 6000;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");

  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  };

  function ring(size) {
    const box = el("span", "bgq-ring");
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
    svg.setAttribute("aria-hidden", "true");
    const r = size / 2 - 2;
    const circ = 2 * Math.PI * r;
    for (const cls of ["track", "value"]) {
      const c = document.createElementNS(SVG, "circle");
      c.setAttribute("class", cls);
      c.setAttribute("cx", size / 2);
      c.setAttribute("cy", size / 2);
      c.setAttribute("r", r);
      if (cls === "value") {
        c.style.strokeDasharray = `${circ}`;
        c.style.strokeDashoffset = `${circ}`;
      }
      svg.append(c);
    }
    const label = el("b");
    const span = el("span");
    label.append(span);
    box.append(svg, label);
    return {
      box,
      set(pct, text) {
        const p = Math.max(0, Math.min(100, Number(pct) || 0));
        svg.lastChild.style.strokeDashoffset = `${circ * (1 - p / 100)}`;
        span.textContent = text ?? "";
      },
    };
  }

  function eta(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0) return null;
    if (seconds < 90) return ["bgq_eta_short", {}];
    if (seconds < 3600) return ["bgq_eta_min", { n: Math.round(seconds / 60) }];
    return ["bgq_eta_hours", { n: (seconds / 3600).toFixed(1).replace(".0", "") }];
  }

  function line(node, parts) {
    const span = (part) => {
      const s = el("span");
      if (Array.isArray(part)) put(s, part[0], part[1]);
      else s.textContent = part;
      return s;
    };
    const items = parts.filter(Boolean);
    node.removeAttribute("data-i18n");
    node.replaceChildren(...items.flatMap((p, i) => (i ? [document.createTextNode(" · "), span(p)] : [span(p)])));
  }

  function mount() {
    const root = el("aside", "bgq");
    root.setAttribute("data-i18n-scope", "web/shared");
    root.setAttribute("aria-live", "polite");
    PageText.attr(root, { "aria-label": "bgq_title" });

    const panel = el("section", "bgq-panel");
    panel.id = "bgq-panel";
    panel.hidden = true;
    const head = el("div", "bgq-head");
    const title = put(el("h3"), "bgq_title");
    const sub = el("p");
    const bar = el("div", "bgq-bar");
    const fill = el("i");
    bar.append(fill);
    head.append(title, sub, bar);
    const list = el("ul", "bgq-list");
    const foot = put(el("div", "bgq-foot"), "bgq_foot");
    panel.append(head, list, foot);

    const pill = el("button", "bgq-pill");
    pill.type = "button";
    pill.setAttribute("aria-expanded", "false");
    pill.setAttribute("aria-controls", panel.id);
    const main = ring(38);
    const text = el("span", "bgq-text");
    const line1 = el("strong");
    const line2 = el("small");
    text.append(line1, line2);
    pill.append(main.box, text);

    root.append(panel, pill);
    document.body.append(root);

    const toggle = (open) => {
      panel.hidden = !open;
      pill.setAttribute("aria-expanded", String(open));
    };
    pill.addEventListener("click", () => toggle(panel.hidden));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") toggle(false); });
    document.addEventListener("pointerdown", (e) => { if (!root.contains(e.target)) toggle(false); }, { passive: true });

    const rows = new Map();
    const samples = [];
    const itemSamples = new Map();
    let seenWork = false;
    let farewell = null;
    let gone = false;
    const lastStatus = new Map();

    function extractSpeed(item) {
      if (item.speed) return item.speed;
      if (item.detail) {
        const m = item.detail.match(/(\d+(?:\.\d+)?\s*(?:[kKMGT]?B\/s|[kKMGT]?iB\/s))/i);
        if (m) return m[1];
      }
      if (item.status !== "running") return "";
      const now = Date.now() / 1000;
      if (!Number(item.size_gb)) return "";
      const doneGb = Number(item.size_gb) * (Number(item.progress) || 0) / 100;
      let history = itemSamples.get(item.id);
      if (!history) {
        history = [];
        itemSamples.set(item.id, history);
      }
      history.push([now, doneGb]);
      while (history.length > 2 && now - history[0][0] > 60) history.shift();
      if (history.length >= 2) {
        const [t0, g0] = history[0];
        const dt = now - t0;
        const dg = doneGb - g0;
        if (dt >= 2 && dg > 0) {
          const mbps = (dg * 1024) / dt;
          return mbps >= 1 ? `${mbps.toFixed(1)} MB/s` : `${Math.round(mbps * 1024)} KB/s`;
        }
      }
      return "";
    }

    function row(item) {
      let r = rows.get(item.id);
      if (!r) {
        const li = el("li", "bgq-item");
        const rg = ring(30);
        const name = el("div", "name");
        const strong = el("strong", null, item.title);
        const miniBar = el("div", "item-bar");
        const miniFill = el("i");
        miniBar.append(miniFill);
        const small = el("small");
        name.append(strong, miniBar, small);
        const stateWrap = el("div", "state-wrap");
        const pctEl = el("span", "state-pct");
        const speedEl = el("span", "state-speed");
        stateWrap.append(pctEl, speedEl);
        li.append(rg.box, name, stateWrap);
        r = { li, rg, small, miniFill, pctEl, speedEl };
        rows.set(item.id, r);
      }
      return r;
    }

    function speed(bg, totalGb) {
      const now = Date.now() / 1000;
      const doneGb = (totalGb * bg.progress) / 100;
      samples.push([now, doneGb]);
      while (samples.length > 2 && now - samples[0][0] > 300) samples.shift();
      const [t0, g0] = samples[0];
      const dt = now - t0;
      if (dt < 20 || doneGb <= g0) return null;
      return eta((totalGb - doneGb) / ((doneGb - g0) / dt));
    }

    function render(bg) {
      if (!bg || !Array.isArray(bg.items) || !bg.items.length) return;
      const finished = bg.finished && bg.items.every((i) => i.status === "done");
      if (!finished) seenWork = true;
      if (!seenWork) return;

      const totalGb = bg.items.reduce((a, i) => a + (Number(i.size_gb) || 0), 0);
      const current = bg.items.find((i) => i.status === "running");
      const curSpeed = current ? extractSpeed(current) : (bg.current_speed || "");
      const pct = Math.round(Number(bg.progress) || 0);

      root.classList.toggle("paused", !!bg.paused);
      root.classList.toggle("done", finished);
      pill.classList.toggle("busy", !!current && !bg.paused && !reduced.matches);
      main.set(bg.progress, finished ? "✓" : `${pct}%`);
      fill.style.width = `${pct}%`;

      const ready = ["bgq_ready_count", { done: bg.done, total: bg.total }];
      if (finished) {
        put(line1, "bgq_complete");
        put(line2, "bgq_complete_sub");
        put(sub, "bgq_ready_count", { done: bg.total, total: bg.total });
        if (!farewell) {
          farewell = setTimeout(() => { gone = true; toggle(false); root.classList.remove("show"); }, FAREWELL_MS);
        }
      } else {
        clearTimeout(farewell);
        farewell = null;
        gone = false;
        const left = speed(bg, totalGb);
        if (bg.paused) {
          put(line1, "bgq_paused");
          put(line2, ready[0], ready[1]);
        } else if (bg.conversation) {
          if (current) raw(line1, current.title);
          else put(line1, "bgq_waiting");
          put(line2, "bgq_resume_after_talk");
        } else if (current) {
          raw(line1, `${current.title} · ${current.progress}%`);
          line(line2, [curSpeed ? `↓ ${curSpeed}` : ["bgq_running", {}], ready, left]);
        } else {
          put(line1, "bgq_next");
          line(line2, [ready, left]);
        }
        const total = ["bgq_total_gb", { gb: totalGb.toFixed(1) }];
        line(sub, bg.paused ? [ready, total, ["bgq_paused_short", {}]] : [ready, total, curSpeed ? `↓ ${curSpeed}` : ""]);
      }

      bg.items.forEach((item, idx) => {
        const r = row(item);
        const before = lastStatus.get(item.id);
        const isRunning = item.status === "running";
        const itemProg = Math.max(0, Math.min(100, Number(item.progress) || 0));
        const itemSpd = extractSpeed(item);

        r.li.className = `bgq-item ${item.status}`;
        if (before && before !== "done" && item.status === "done" && !reduced.matches) {
          r.li.classList.add("just-done");
        }
        r.rg.set(itemProg, isRunning ? `${itemProg}` : "");
        r.miniFill.style.width = isRunning ? `${itemProg}%` : item.status === "done" ? "100%" : "0%";

        if (isRunning) {
          raw(r.pctEl, `${itemProg}%`);
          if (itemSpd) raw(r.speedEl, `↓ ${itemSpd}`);
          else put(r.speedEl, "bgq_running");
          r.small.textContent = item.detail || [Number(item.size_gb) ? `${Number(item.size_gb).toFixed(1)} GB` : "", item.description].filter(Boolean).join(" · ");
        } else if (item.status === "done") {
          raw(r.pctEl, "100%");
          put(r.speedEl, "bgq_status_done");
          r.small.textContent = [Number(item.size_gb) ? `${Number(item.size_gb).toFixed(1)} GB` : "", item.description].filter(Boolean).join(" · ");
        } else if (item.status === "waiting_disk" || item.status === "failed") {
          put(r.pctEl, STATUS[item.status]);
          put(r.speedEl, item.status === "failed" ? "bgq_will_retry" : "bgq_status_disk");
          r.small.textContent = item.message || item.description;
        } else {
          put(r.pctEl, STATUS[item.status] || "bgq_status_queued");
          raw(r.speedEl, Number(item.size_gb) ? `${Number(item.size_gb).toFixed(1)} GB` : "");
          r.small.textContent = item.description;
        }

        if (list.children[idx] !== r.li) list.insertBefore(r.li, list.children[idx] || null);
        lastStatus.set(item.id, item.status);
      });

      if (!gone) root.classList.add("show");
    }


    return render;
  }

  let render = null;
  const onState = (e) => {
    const bg = e.detail && e.detail.background;
    if (!bg) return;
    if (!render) {
      if (!document.body) return;
      render = mount();
    }
    render(bg);
  };
  addEventListener("nuxiva:state", onState);
})();
