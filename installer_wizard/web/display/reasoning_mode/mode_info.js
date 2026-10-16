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

  function pickSub(st) {
    if (st.pick === "sequential") return H("rf_pick_sequential");
    if (st.pick === "first") return H("rf_pick_first");
    return H("rf_pick_best", { wait: st.wait_s });
  }

  function flow(d) {
    const st = d.strategy;
    const auto = !!d.auto_rules;
    const launched = Math.max(1, d.launched);
    const lanes = Math.min(launched, 4);
    const W = 1180, laneH = 74;
    const top = 30, mid = top + ((lanes - 1) * laneH) / 2;
    const col = auto ? [10, 180, 350, 560, 830, 1010] : [10, 200, 0, 420, 760, 1000];
    const route = H(d.routing.kind === "chat" ? "rf_route_chat" : "rf_route_deep");
    let svg = node(col[0], mid, 160, "rf_question", H("rf_question_sub", { n: d.complexity_words }), "start");
    svg += node(col[1], mid, 160, "rf_route", route, "");
    svg += arrow(col[0] + 160, mid + 32, col[1], mid + 32);
    let from = col[1] + 160;
    if (auto) {
      svg += node(col[2], mid, 180, "rf_auto", esc(`${d.auto_rules.length} → 1`), "accent");
      svg += arrow(from, mid + 32, col[2], mid + 32);
      from = col[2] + 180;
    }
    for (let i = 0; i < lanes; i++) {
      const y = top + i * laneH;
      const ref = d.routing.models[i] ? d.routing.models[i].ref : `#${i + 1}`;
      const label = i === lanes - 1 && launched > lanes ? `+${launched - lanes + 1}` : ref;
      svg += node(col[3], y, 240, "rf_model", esc(label), "lane");
      svg += arrow(from, mid + 32, col[3], y + 32);
      svg += arrow(col[3] + 240, y + 32, col[4], mid + 32);
    }
    svg += node(col[4], mid, 160, st.critic ? "rf_critic" : "rf_pick", pickSub(st), "accent");
    svg += node(col[5], mid, 160, "rf_answer", esc(`≤ ${d.hard_timeout_s} s`), "end");
    svg += arrow(col[4] + 160, mid + 32, col[5], mid + 32);
    const h = top * 2 + lanes * laneH;
    const steps = [
      ["rf_question", H("rf_question_sub", { n: d.complexity_words })],
      ["rf_route", route],
      ...(auto ? [["rf_auto", esc(`${d.auto_rules.length} → 1`)]] : []),
      ["rf_model", esc(`× ${launched}`)],
      [st.critic ? "rf_critic" : "rf_pick", pickSub(st)],
      ["rf_answer", esc(`≤ ${d.hard_timeout_s} s`)],
    ];
    const list = `<ol class="rf-steps">${steps.map(([k, sub]) => `<li>${H(k, {}, "b")}<small>${sub}</small></li>`).join("")}</ol>`;
    return `<svg class="rf-svg" viewBox="0 0 ${W} ${h}" role="img" aria-labelledby="rinfo-flow-title">${svg}</svg>${list}`;
  }

  function card(key, value, hint) {
    return `<div class="ri-card"><span>${H(key)}</span><b>${esc(value)}</b>${hint ? `<small>${hint}</small>` : ""}</div>`;
  }

  function params(d) {
    const st = d.strategy;
    return `<div class="ri-grid">
      ${card("ri_candidates", `${d.launched} / ${d.routing.candidates}`)}
      <div class="ri-card"><span>${H("ri_pick")}</span><b>${H(`ri_pick_${st.pick}`)}</b></div>
      ${st.pick === "best" ? card("ri_wait", `${st.wait_s} s`) : ""}
      ${card("ri_hard", `${d.hard_timeout_s} s`)}
      <div class="ri-card"><span>${H("ri_critic")}</span><b>${H(st.critic ? "ri_yes" : "ri_no")}</b></div>
    </div>`;
  }

  function formulas(d) {
    const l = d.limbic, s = d.scoring, c = d.critic, st = d.strategy;
    const critic = c.base + c.risk_weight + c.dopamine * l.dopamine + c.cortisol * l.cortisol + c.valence * l.valence + c.clarity;
    const rows = [
      `<li>${H("ri_f_conf")}<code>${num(s.confidence_ok)} ${H("ri_f_conf_ok")} · ${num(s.confidence_bad)} ${H("ri_f_conf_bad")}</code></li>`,
    ];
    if (st.critic) {
      rows.push(`<li>${H("ri_f_critic")}<code>${c.base} + ${c.risk_weight}·(1 − ${c.risk_step}·n) + ${c.dopamine}·${num(l.dopamine)} ${c.cortisol}·${num(l.cortisol)} + ${c.valence}·${num(l.valence)} + ${c.clarity}·min(1, ${H("ri_words")}/${c.clarity_words}) ≤ <b>${num(Math.min(1, critic))}</b></code><small>${H("ri_f_critic_terms", { terms: c.risk_terms.join(", ") })}</small></li>`);
      rows.push(`<li>${H("ri_f_step")}<code>${s.confidence_weight}·${H("ri_conf_short")} + ${s.critic_weight}·${H("ri_critic_short")}</code></li>`);
    }
    rows.push(`<li>${H(`ri_f_stop_${st.pick}`, { wait: st.wait_s })}</li>`);
    rows.push(`<li>${H("ri_f_fallback")}</li>`);
    return `<ol class="ri-math">${rows.join("")}</ol>`;
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
      ${H(`ri_rule_${r.when}`, { nor: r.noradrenaline_above, cx: r.complexity_below ?? r.complexity_above, val: r.abs_valence_above, engine: r.engine.name })}
      <small>${esc(r.engine.summary)}</small></li>`).join("")}</ol>`;
  }

  function render(d) {
    data = d;
    shell().innerHTML = `<article class="rinfo-card">
      <div class="ri-head"><span class="ri-icon">${esc(d.icon)}</span><div><h2 id="rinfo-title">${esc(d.name)}</h2>
        <p>${esc(d.summary)}</p></div>
        <button type="button" class="ri-close" data-rinfo-close data-i18n-attr="aria-label:ri_close,title:ri_close">✕</button></div>
      <p class="ri-honest">${H("ri_honest")}</p>
      <section class="ri-section"><h3 id="rinfo-flow-title">${H("ri_flow_title")}</h3>${flow(d)}</section>
      <section class="ri-section"><h3>${H("ri_route_title")}</h3>
        <p class="ri-note">${H(d.routing.kind === "chat" ? "ri_route_chat" : "ri_route_deep")}</p>${models(d)}</section>
      <section class="ri-section"><h3>${H("ri_params_title")}</h3>${params(d)}</section>
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
