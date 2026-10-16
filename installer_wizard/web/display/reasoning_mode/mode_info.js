(() => {
  "use strict";

  const H = (key, params, tag) => PageText.html(key, params, tag);
  const esc = (v) => window.Nuxiva.fmt.esc(v);
  const num = (v, d = 2) => Number(v).toFixed(d);
  let root = null;
  let data = null;
  let words = 12;
  let lastFocus = null;

  function shell() {
    if (root) return root;
    root = document.createElement("div");
    root.className = "rinfo";
    root.hidden = true;
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-labelledby", "rinfo-title");
    root.addEventListener("click", (e) => {
      if (e.target === root || e.target.closest("[data-rinfo-close]")) close();
    });
    root.addEventListener("input", (e) => {
      if (e.target.id === "rinfo-words") {
        words = Number(e.target.value) || 1;
        paintAuto();
      }
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && root && !root.hidden) close(); });
    document.body.appendChild(root);
    return root;
  }

  function node(x, y, w, key, sub, tone) {
    return `<g class="rf-node ${tone || ""}" transform="translate(${x},${y})">
      <rect width="${w}" height="64" rx="14"></rect>
      <foreignObject x="10" y="8" width="${w - 20}" height="52"><div class="rf-label">${H(key, {}, "b")}<small>${sub}</small></div></foreignObject>
    </g>`;
  }

  function arrow(x1, y1, x2, y2, dashed) {
    return `<path class="rf-edge${dashed ? " dashed" : ""}" d="M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}"></path>`;
  }

  function flow(d) {
    const p = d.profile;
    const auto = !!d.auto_rules;
    const branches = Math.min(d.budget.result, Math.max(1, d.routing.candidates));
    const lanes = Math.min(branches, 4);
    const W = 1180, laneH = 74;
    const top = 30, mid = top + ((lanes - 1) * laneH) / 2;
    let svg = "";
    const col = [10, 190, 370, 560, 820, 1000];
    svg += node(col[0], mid, 160, "rf_question", H("rf_question_sub", { n: d.complexity_words }), "start");
    svg += node(col[1], mid, 160, "rf_route", H(d.routing.kind === "chat" ? "rf_route_chat" : "rf_route_deep"), "");
    svg += arrow(col[0] + 160, mid + 32, col[1], mid + 32);
    svg += node(col[2], mid, 170, auto ? "rf_profile_auto" : "rf_profile", auto ? "4 → 1" : `${p.parallel_branches}×${p.mcts_depth}`, auto ? "accent" : "");
    svg += arrow(col[1] + 160, mid + 32, col[2], mid + 32);
    for (let i = 0; i < lanes; i++) {
      const y = top + i * laneH;
      const label = i === lanes - 1 && branches > lanes ? `+${branches - lanes + 1}` : `#${i + 1}`;
      svg += node(col[3], y, 220, "rf_branch", esc(`${label} · ${auto ? "≤5" : p.mcts_depth} ⟳`), "lane");
      svg += arrow(col[2] + 170, mid + 32, col[3], y + 32);
      svg += arrow(col[3] + 220, y + 32, col[4], mid + 32);
    }
    svg += node(col[4], mid, 150, "rf_ignition", esc(auto ? "0.72–0.92" : `≥ ${num(p.ignition_threshold)}`), "accent");
    svg += node(col[5], mid, 160, "rf_answer", esc(`≤ ${auto ? "0.45–7.5" : num(p.timeout_s, 2)} s`), "end");
    svg += arrow(col[4] + 150, mid + 32, col[5], mid + 32);
    const h = top * 2 + lanes * laneH;
    const steps = [
      ["rf_question", H("rf_question_sub", { n: d.complexity_words })],
      ["rf_route", H(d.routing.kind === "chat" ? "rf_route_chat" : "rf_route_deep")],
      [auto ? "rf_profile_auto" : "rf_profile", auto ? "4 → 1" : `${p.parallel_branches}×${p.mcts_depth}`],
      ["rf_branch", esc(`×${branches} · ${auto ? "≤5" : p.mcts_depth} ⟳`)],
      ["rf_ignition", esc(auto ? "0.72–0.92" : `≥ ${num(p.ignition_threshold)}`)],
      ["rf_answer", esc(`≤ ${auto ? "0.45–7.5" : num(p.timeout_s, 2)} s`)],
    ];
    const list = `<ol class="rf-steps">${steps.map(([k, sub]) => `<li>${H(k, {}, "b")}<small>${sub}</small></li>`).join("")}</ol>`;
    return `<svg class="rf-svg" viewBox="0 0 ${W} ${h}" role="img" aria-labelledby="rinfo-flow-title">${svg}</svg>${list}`;
  }

  function card(key, value, hint) {
    return `<div class="ri-card"><span>${H(key)}</span><b>${esc(value)}</b>${hint ? `<small>${hint}</small>` : ""}</div>`;
  }

  function yes(v) {
    return H(v ? "ri_yes" : "ri_no");
  }

  function params(p) {
    return `<div class="ri-grid">
      ${card("ri_branches", p.parallel_branches)}
      ${card("ri_depth", p.mcts_depth)}
      ${card("ri_threshold", num(p.ignition_threshold))}
      ${card("ri_timeout", `${num(p.timeout_s)} s`)}
      <div class="ri-card"><span>${H("ri_limbic")}</span><b>${yes(p.use_limbic)}</b></div>
      <div class="ri-card"><span>${H("ri_critic")}</span><b>${yes(p.use_twin_critic)}</b></div>
    </div>`;
  }

  function formulas(d) {
    const l = d.limbic, s = d.scoring, c = d.critic, b = d.budget;
    const base = d.profile.parallel_branches;
    const budget = b.rule === "stress"
      ? `⌊${base} ÷ 4⌋ = <b>${b.result}</b>`
      : `round(${base} × (0.5 + 0.5·${num(l.dopamine)} + 0.2·${num(l.serotonin)})) = round(${base} × ${num(b.factor, 3)}) = <b>${b.result}</b>`;
    const critic = c.base + c.risk_weight + c.dopamine * l.dopamine + c.cortisol * l.cortisol + c.valence * l.valence + c.clarity;
    return `<ol class="ri-math">
      <li>${H("ri_f_budget")}<code>${budget}</code><small>${H(b.rule === "stress" ? "ri_f_budget_stress" : "ri_f_budget_explore")}</small></li>
      <li>${H("ri_f_lanes")}<code>min(${b.result}, ${d.routing.candidates}) = <b>${Math.min(b.result, Math.max(1, d.routing.candidates))}</b></code><small>${H("ri_f_lanes_why")}</small></li>
      <li>${H("ri_f_conf")}<code>${num(s.confidence_ok)} ${H("ri_f_conf_ok")} · ${num(s.confidence_bad)} ${H("ri_f_conf_bad")}</code></li>
      <li>${H("ri_f_critic")}<code>${c.base} + ${c.risk_weight}·(1 − ${c.risk_step}·n) + ${c.dopamine}·${num(l.dopamine)} ${c.cortisol}·${num(l.cortisol)} + ${c.valence}·${num(l.valence)} + ${c.clarity}·min(1, ${H("ri_words")}/${c.clarity_words}) ≤ <b>${num(Math.min(1, critic))}</b></code><small>${H("ri_f_critic_terms", { terms: c.risk_terms.join(", ") })}</small></li>
      <li>${H("ri_f_step")}<code>${s.confidence_weight}·${H("ri_conf_short")} + ${s.critic_weight}·${H("ri_critic_short")}</code></li>
      <li>${H("ri_f_mean")}<code>Sₖ = (Sₖ₋₁·(k−1) + passoₖ) ÷ k</code></li>
      <li>${H("ri_f_ignite")}<code>Sₖ ≥ ${d.profile.ignition_threshold ? num(d.profile.ignition_threshold) : "θ"}</code></li>
      <li>${H("ri_f_prune")}<code>passo &lt; ${num(s.prune_factor)}·θ = ${num(s.prune_below, 3)}</code></li>
      <li>${H("ri_f_fallback")}</li>
    </ol>`;
  }

  function models(d) {
    if (!d.routing.models.length) return `<p class="ri-note">${H("ri_no_models")}</p>`;
    return `<ul class="ri-models">${d.routing.models.map((m, i) => `<li><span class="ri-rank">${i + 1}</span><b>${esc(m.ref)}</b>
      <small>${m.avg_ms == null ? H("ri_no_stats") : H("ri_stats", { ms: m.avg_ms, ok: m.ok, fail: m.fail })}</small></li>`).join("")}</ul>`;
  }

  function autoPanel(d) {
    if (!d.auto_rules) return "";
    return `<section class="ri-section"><h3>${H("ri_auto_title")}</h3><p class="ri-note">${H("ri_auto_desc", { words: d.complexity_words })}</p>
      <label class="ri-slider">${H("ri_words_label")} <input id="rinfo-words" type="range" min="1" max="90" value="${words}"><b id="rinfo-words-v"></b></label>
      <div id="rinfo-auto"></div></section>`;
  }

  function pickAuto(d) {
    const complexity = Math.min(1, words / d.complexity_words);
    const l = d.limbic;
    const r = d.auto_rules;
    if (l.noradrenaline > r[0].noradrenaline_above && complexity < r[0].complexity_below) return [r[0], complexity];
    if (Math.abs(l.valence) > r[1].abs_valence_above) return [r[1], complexity];
    if (complexity > r[2].complexity_above) return [r[2], complexity];
    return [r[3], complexity];
  }

  function paintAuto() {
    const box = document.getElementById("rinfo-auto");
    if (!box || !data || !data.auto_rules) return;
    const [chosen, complexity] = pickAuto(data);
    document.getElementById("rinfo-words-v").textContent = `${words} → ${num(complexity)}`;
    box.innerHTML = `<ol class="ri-rules">${data.auto_rules.map((r) => `<li class="${r === chosen ? "on" : ""}">
      ${H(`ri_rule_${r.when}`, { nor: r.noradrenaline_above, cx: r.complexity_below ?? r.complexity_above, val: r.abs_valence_above })}
      <small>${esc(r.profile)} · ${r.params.parallel_branches}×${r.params.mcts_depth} · θ ${num(r.params.ignition_threshold)} · ${num(r.params.timeout_s)} s</small></li>`).join("")}</ol>`;
  }

  function render(d) {
    data = d;
    const p = d.profile;
    shell().innerHTML = `<article class="rinfo-card">
      <div class="ri-head"><span class="ri-icon">${esc(d.icon)}</span><div><h2 id="rinfo-title">${esc(d.name)}</h2>
        <p>${H("ri_label", { label: d.label })} · SLA ${d.sla_ms} ms · VRAM ${d.vram_mb} MB</p></div>
        <button type="button" class="ri-close" data-rinfo-close data-i18n-attr="aria-label:ri_close,title:ri_close">✕</button></div>
      <p class="ri-honest">${H("ri_honest")}</p>
      <section class="ri-section"><h3 id="rinfo-flow-title">${H("ri_flow_title")}</h3>${flow(d)}</section>
      <section class="ri-section"><h3>${H("ri_route_title")}</h3>
        <p class="ri-note">${H(d.routing.kind === "chat" ? "ri_route_chat" : "ri_route_deep", { sla: d.sla_ms, limit: d.routing.threshold_ms })}</p>${models(d)}</section>
      ${d.auto_rules ? "" : `<section class="ri-section"><h3>${H("ri_params_title")}</h3>${params(p)}</section>`}
      ${autoPanel(d)}
      <section class="ri-section"><h3>${H("ri_math_title")}</h3>${formulas(d)}</section>
      <section class="ri-section"><h3>${H("ri_limbic_title")}</h3><div class="ri-grid">
        ${Object.entries(d.limbic).map(([k, v]) => card(`ri_l_${k}`, num(v))).join("")}</div>
        <p class="ri-note">${H("ri_limbic_desc")}</p></section>
    </article>`;
    paintAuto();
  }

  async function open(mode) {
    lastFocus = document.activeElement;
    const box = shell();
    box.hidden = false;
    box.innerHTML = `<article class="rinfo-card"><p class="ri-note">${H("ri_loading")}</p></article>`;
    try {
      const r = await fetch(`/api/assistant/mode/explain?mode=${encodeURIComponent(mode)}`, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      render(await r.json());
      const btn = box.querySelector(".ri-close");
      if (btn) btn.focus();
    } catch (err) {
      console.warn("Spiegazione del motore non disponibile", err);
      box.innerHTML = `<article class="rinfo-card"><p class="ri-note">${H("ri_error")}</p>
        <button type="button" class="ri-close" data-rinfo-close>✕</button></article>`;
    }
  }

  function close() {
    if (!root) return;
    root.hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  window.NuxivaReasoningInfo = Object.freeze({ open, close });
})();
