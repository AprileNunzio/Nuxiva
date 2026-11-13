(() => {
  "use strict";
  const D = window.NuxivaDisplay;
  const NS = (window.NuxivaDefense = window.NuxivaDefense || {});
  const SCOPE = "web/display/defense";
  const T = window.PageText ? PageText.scope(SCOPE) : (key) => key;
  const POSTURES = new Set(["calm", "watch", "alert", "attack"]);
  const KINDS = new Set(["port_scan", "host_sweep", "syn_flood", "brute_force", "arp_spoof", "dns_tunnel", "icmp_flood", "exfiltration"]);
  const LIBS = ["/vendor/three.min.js", "/vendor/OrbitControls.js", "/static/display/defense/countries.js", "/static/display/defense/scene.js"];
  let root = null;
  let stage = null;
  let view = null;
  let current = null;
  let selected = "";
  let loading = null;
  let regions = null;

  function el(tag, cls, parent) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function regionName(code) {
    if (!code) return T("unknown_country");
    try {
      regions = regions || new Intl.DisplayNames([document.documentElement.lang || "it"], { type: "region" });
      return regions.of(code) || code;
    } catch (error) {
      return code;
    }
  }

  function build() {
    root = el("section", "defense-screen hidden", document.body);
    root.setAttribute("data-i18n-scope", SCOPE);
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-labelledby", "defense-title");
    stage = el("div", "defense-stage", root);
    const head = el("div", "defense-head", root);
    const titles = el("div", "defense-titles", head);
    PageText.bind(el("p", "defense-kicker", titles), "kicker");
    const title = el("h2", "defense-title", titles);
    title.id = "defense-title";
    el("p", "defense-sentence", titles).id = "defense-sentence";
    const close = el("button", "defense-close", head);
    close.type = "button";
    PageText.bind(close, "close");
    close.addEventListener("click", () => dismiss());
    const side = el("aside", "defense-side", root);
    PageText.bind(el("h3", "defense-section", side), "incidents_title");
    el("ul", "defense-list", side).id = "defense-incidents";
    PageText.bind(el("h3", "defense-section", side), "defenses_title");
    el("ul", "defense-list", side).id = "defense-defenses";
    el("p", "defense-foot", root).id = "defense-foot";
    PageText.bind(el("p", "defense-hint", root), "hint");
    root.addEventListener("keydown", (event) => { if (event.key === "Escape") dismiss(); });
  }

  function set(id, key, params) {
    const node = document.getElementById(id);
    if (node) PageText.bind(node, key, params);
  }

  function row(list, lines, tone, active, onClick) {
    const item = el("li", `defense-row tone-${tone}${active ? " is-active" : ""}`, list);
    lines.forEach((line, index) => {
      const node = el(index === 0 ? "strong" : "span", "", item);
      if (line.key) PageText.bind(node, line.key, line.params);
      else node.textContent = line.text;
    });
    if (onClick) {
      item.tabIndex = 0;
      item.addEventListener("click", onClick);
      item.addEventListener("keydown", (event) => { if (event.key === "Enter") onClick(); });
    }
  }

  function minutes(expires) {
    return Math.max(1, Math.round((expires * 1000 - Date.now()) / 60000));
  }

  function paint(data) {
    const posture = POSTURES.has(data.posture) ? data.posture : "calm";
    root.dataset.posture = posture;
    set("defense-title", `p_${posture}`);
    set("defense-sentence", data.mode === "off" || data.mode === "monitor" ? "h_observing" : `h_${posture}`);
    const incidents = document.getElementById("defense-incidents");
    const defenses = document.getElementById("defense-defenses");
    incidents.replaceChildren();
    defenses.replaceChildren();
    if (!data.incidents.length) row(incidents, [{ key: "no_incidents" }], "calm", false);
    data.incidents.forEach((i) => {
      const where = [{ key: "from_country", params: { country: regionName(i.country) } }];
      row(incidents, [{ key: `kind_${KINDS.has(i.kind) ? i.kind : "unknown"}` }, ...where, { key: `stage_${i.stage}` },
        { key: "hit", params: { count: i.targets } }], i.level, i.id === selected, () => { selected = selected === i.id ? "" : i.id; paint(current); });
      if (i.id === selected) row(incidents, [{ text: i.src }, ...i.hosts.map((h) => ({ text: h }))], "detail", false);
    });
    if (!data.defenses.length) row(defenses, [{ key: "no_defenses" }], "calm", false);
    data.defenses.forEach((d) => row(defenses, [{ key: `defense_${d.kind}` }, { text: d.target },
      { key: "left", params: { minutes: minutes(d.expires) } }, { key: d.auto ? "by_nuxiva" : "by_you" }], "defense", false));
    set("defense-foot", "devices", { lan: data.lan, trusted: data.trusted });
    if (view) view.update(data);
  }

  function libs() {
    if (!loading) {
      const load = D.loadScript || ((src) => new Promise((ok, ko) => {
        const node = document.createElement("script");
        node.src = src;
        node.onload = ok;
        node.onerror = () => ko(new Error(src));
        document.head.appendChild(node);
      }));
      const optional = (src) => load(src).catch(() => null);
      loading = LIBS.reduce((chain, src) => chain.then(() => {
        if (src.endsWith("three.min.js")) return window.THREE ? null : load(src);
        return src.endsWith("OrbitControls.js") ? optional(src) : load(src);
      }), Promise.resolve());
      loading.catch(() => { loading = null; });
    }
    return loading;
  }

  async function open(data) {
    if (!root) build();
    current = data;
    await PageText.ready([SCOPE]);
    root.classList.remove("hidden");
    if (window.NuxivaResources) window.NuxivaResources.claim("defense");
    paint(data);
    if (D.pingActivity) D.pingActivity(true);
    if (!view) {
      try {
        await libs();
        if (root.classList.contains("hidden")) return;
        view = NS.createScene(stage, { onPick: (id) => { selected = id; paint(current); } });
        paint(current);
        root.classList.remove("no-3d");
      } catch (error) {
        root.classList.add("no-3d");
        console.error("difesa: vista 3D non disponibile", error);
      }
    }
    const close = root.querySelector(".defense-close");
    if (close) close.focus({ preventScroll: true });
  }

  function hide() {
    if (view) { view.dispose(); view = null; }
    if (root) root.classList.add("hidden");
    if (window.NuxivaResources) window.NuxivaResources.release("defense");
    selected = "";
  }

  function dismiss() {
    hide();
  }

  function isOpen() {
    return !!root && !root.classList.contains("hidden");
  }

  function event(ev) {
    if (!ev || typeof ev !== "object" || !ev.scene || typeof ev.scene !== "object") {
      if (ev && ev.type === "defense_view" && ev.open === false) hide();
      return;
    }
    if (ev.type === "defense_view") {
      if (ev.open === true) open(ev.scene);
      else hide();
      return;
    }
    if (ev.type !== "defense_state") return;
    if (isOpen()) { current = ev.scene; paint(ev.scene); }
  }

  NS.View = { event, open, hide, isOpen };
  D.DefenseView = NS.View;
})();
