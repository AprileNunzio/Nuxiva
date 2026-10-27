(() => {
  const D = window.NuxivaDisplay;
  const T = window.PageText ? PageText.scope("web/display") : (k) => k;
  const SVG = "http://www.w3.org/2000/svg";
  const BARS = 44, POLL_MS = 8000, VOICE_HOLD = 1800;
  const MOODS = new Set(["felice", "sereno", "entusiasta", "innamorato", "grato", "neutro", "stanco", "annoiato", "stressato", "preoccupato", "triste", "arrabbiato", "malato"]);
  const VITAL_ORDER = ["heart_rate", "spo2", "body_temp", "skin_temp", "resp_rate", "hrv"];
  const FIELDS = new Set(["nickname", "coffee", "wake_time", "sleep_time", "food_dislikes", "food_likes", "music", "sports"]);
  const state = { panel: null, level: 0, heardAt: 0, frame: 0, bars: [], levels: new Array(BARS).fill(0), timer: 0, moodId: "" };
  const refs = {};

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const svg = (tag, attrs) => {
    const n = document.createElementNS(SVG, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    return n;
  };
  const head = (key, name) => {
    const h = el("div", "rl-head");
    h.append(el("span", "rl-k", T(key)), el("span", "rl-n", name || ""));
    const chip = el("span", "rl-chip");
    h.append(chip);
    return { node: h, name: h.children[1], chip };
  };

  function ago(ts) {
    const s = Math.max(0, Date.now() / 1000 - ts);
    if (s < 90) return T("rl_now");
    if (s < 3600) return T("rl_min", { n: Math.round(s / 60) });
    if (s < 86400) return T("rl_hour", { n: Math.round(s / 3600) });
    return T("rl_day", { n: Math.round(s / 86400) });
  }

  function buildVoice() {
    const block = el("section", "rl-block voice");
    block.setAttribute("aria-label", T("rl_voice"));
    const h = head("rl_voice");
    const bars = el("div", "rl-bars");
    bars.setAttribute("aria-hidden", "true");
    for (let i = 0; i < BARS; i++) { const b = el("i"); bars.append(b); state.bars.push(b); }
    const line = el("div", "rl-line");
    const who = el("span");
    const pct = el("span", "mono");
    line.append(who, pct);
    block.append(h.node, bars, line);
    Object.assign(refs, { voice: block, voiceChip: h.chip, voiceWho: who, voicePct: pct });
    return block;
  }

  function buildHome() {
    const block = el("section", "rl-block home");
    const h = head("rl_home");
    const list = el("div", "rl-block");
    block.append(h.node, list);
    Object.assign(refs, { home: block, homeCount: h.name, homeList: list });
    return block;
  }

  function buildScan() {
    const block = el("section", "rl-block scan");
    const h = head("rl_scanner");
    const mood = el("div", "rl-mood");
    const word = el("b");
    const level = el("span");
    mood.append(word, level);
    const bar = el("div", "rl-level");
    bar.append(el("i"));
    const say = el("div", "rl-say");
    const acts = el("div", "rl-acts");
    const ok = el("button", "rl-act ok", T("rl_right"));
    const bad = el("button", "rl-act bad", T("rl_wrong"));
    ok.type = bad.type = "button";
    ok.addEventListener("click", () => judge("mood", state.moodId, "ok"));
    bad.addEventListener("click", () => judge("mood", state.moodId, "wrong"));
    const week = el("span", "rl-n", T("rl_week"));
    week.style.marginLeft = "auto";
    acts.append(ok, bad, week);
    const spark = svg("svg", { class: "rl-spark", viewBox: "0 0 350 44", preserveAspectRatio: "none", role: "img" });
    spark.setAttribute("aria-label", T("rl_week"));
    block.classList.add("rl-more-host");
    spark.classList.add("rl-more");
    block.append(h.node, mood, bar, say, acts, spark);
    Object.assign(refs, { scan: block, scanHead: h, mood, word, level, bar: bar.firstChild, say, acts, ok, bad, spark });
    return block;
  }

  function buildVitals() {
    const block = el("section", "rl-block vitals");
    const h = head("rl_vitals");
    const grid = el("div", "rl-vitals");
    block.append(h.node, grid);
    Object.assign(refs, { vitals: block, vitalsChip: h.chip, vitalsGrid: grid });
    return block;
  }

  function buildLearn() {
    const block = el("section", "rl-block learn rl-more");
    const h = head("rl_learned");
    const list = el("div", "rl-block");
    block.append(h.node, list);
    Object.assign(refs, { learn: block, learnList: list });
    return block;
  }

  function mount() {
    const left = el("aside", "rail left");
    const right = el("aside", "rail right");
    left.append(buildVoice(), buildHome());
    right.append(buildScan(), buildVitals(), buildLearn());
    const hud = document.querySelector(".hud");
    hud.prepend(right);
    hud.prepend(left);
  }

  function judge(kind, id, verdict) {
    const focus = state.panel && state.panel.focus;
    if (!focus || !id) return;
    fetch("/api/display/people-panel/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
      body: JSON.stringify({ kind, slug: focus.slug, id, verdict }),
    }).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return refresh(); })
      .catch((err) => console.warn("Giudizio non registrato", err));
  }

  function renderHome(roster, familyNear) {
    const rows = roster || [];
    const home = rows.filter((r) => r.home).length;
    refs.homeCount.textContent = T(home === 1 ? "rl_present_one" : "rl_present_n", { n: home });
    const isFamilyNear = familyNear ?? (D.isFamilyNear ? D.isFamilyNear() : true);
    refs.home.hidden = rows.length === 0 || !isFamilyNear;
    refs.homeList.replaceChildren(...rows.map((r, i) => {
      const row = el("div", `rl-person ${r.home ? "home" : "away"}`);
      const av = el("span", `rl-av t${i % 4}`, r.initials);
      const who = el("div", "rl-who");
      const sub = r.home ? T("rl_at_home") : r.seen ? `${T("rl_away")} · ${T("rl_seen", { when: ago(r.seen) })}` : T("rl_never");
      who.append(el("b", "", r.name), el("small", "", sub));
      row.append(av, who, el("i", "rl-dot"));
      return row;
    }));
  }

  function spark(series) {
    const pts = (series || []).map((d, i, a) => ({ x: (i / Math.max(1, a.length - 1)) * 350, y: d.level === null ? null : 38 - ((d.level - 1) / 4) * 32 }));
    const known = pts.filter((p) => p.y !== null);
    refs.spark.replaceChildren();
    if (known.length < 2) return;
    refs.spark.append(svg("path", { d: known.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ") }));
    const last = known[known.length - 1];
    refs.spark.append(svg("circle", { cx: last.x, cy: last.y, r: 3.4 }));
  }

  function renderScan(focus) {
    refs.scan.hidden = !focus || !!(D.state && D.state.privacy && D.state.privacy.away);
    if (refs.scan.hidden) return;
    refs.scanHead.name.textContent = focus.name;
    refs.scanHead.chip.textContent = T("rl_face");
    const m = focus.mood && MOODS.has(focus.mood.mood) ? focus.mood : null;
    state.moodId = m ? m.id : "";
    refs.mood.classList.toggle("empty", !m);
    refs.word.textContent = m ? T(`mood_${m.mood}`) : T("rl_no_mood");
    refs.level.textContent = m ? T("rl_level", { n: m.intensity }) : "";
    refs.bar.style.width = m ? `${m.intensity * 20}%` : "0%";
    refs.say.textContent = m && m.evidence ? `«${m.evidence}»` : "";
    refs.say.hidden = !(m && m.evidence);
    const askable = !!(m && m.source === "assistente" && !m.feedback);
    refs.ok.hidden = refs.bad.hidden = !askable;
    spark(focus.series);
  }

  function renderVitals(focus) {
    const values = focus && !(D.state && D.state.privacy && D.state.privacy.away) ? focus.vitals || {} : {};
    const keys = VITAL_ORDER.filter((k) => values[k]);
    refs.vitals.hidden = !keys.length;
    if (!keys.length) return;
    const newest = keys.map((k) => values[k]).sort((a, b) => a.age - b.age)[0];
    refs.vitalsChip.textContent = `${T(`src_${newest.kind}`)} · ${T("rl_ago_s", { n: Math.round(newest.age) })}`;
    refs.vitalsGrid.replaceChildren(...keys.map((k) => {
      const v = values[k];
      const cell = el("div", `rl-vital v-${k}`);
      const num = el("b", "", String(v.value));
      num.append(el("small", "", v.unit));
      cell.append(el("span", "", T(`vt_${k}`)), num);
      return cell;
    }));
  }

  function renderLearn(focus) {
    const rows = focus && !(D.state && D.state.privacy && D.state.privacy.away) ? focus.learned : [];
    refs.learn.hidden = !rows.length;
    refs.learnList.replaceChildren(...rows.map((r) => {
      const row = el("div", "rl-learn");
      const undo = el("button", "rl-act", T("rl_undo"));
      undo.type = "button";
      undo.addEventListener("click", () => judge("learned", r.id, "wrong"));
      row.append(el("span", "", r.value), el("small", "", T(`learn_${FIELDS.has(r.field) ? r.field : "other"}`)), undo);
      return row;
    }));
  }

  function render() {
    const p = state.panel;
    if (!p) return;
    renderHome(p.roster, p.family_near);
    renderScan(p.focus);
    renderVitals(p.focus);
    renderLearn(p.focus);
    avoid();
  }

  async function refresh() {
    try {
      const r = await fetch("/api/display/people-panel", { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      state.panel = await r.json();
      render();
    } catch (err) {
      console.info("Pannello persone non disponibile", err);
    }
  }

  function paintVoice() {
    state.frame = requestAnimationFrame(paintVoice);
    const live = Date.now() - state.heardAt < VOICE_HOLD;
    const v = live ? Math.min(1, state.level * 3.2) : 0;
    state.levels.shift();
    state.levels.push(v);
    const last = state.levels;
    state.bars.forEach((b, i) => {
      const env = Math.sin((i / (BARS - 1)) * Math.PI);
      const shape = 0.45 + 0.55 * Math.abs(Math.sin(i * 0.9) * Math.cos(i * 0.35));
      const h = 4 + env * (6 + 54 * last[Math.max(0, last.length - 1 - Math.round(Math.abs(i - BARS / 2) * 0.6))] * shape);
      b.style.height = `${h.toFixed(1)}px`;
    });
    refs.voice.classList.toggle("live", live);
    refs.voiceChip.textContent = `● ${T(live ? "rl_listening" : "rl_silent")}`;
    refs.voicePct.textContent = live ? `${Math.round(Math.min(1, state.level * 3.2) * 100)}%` : "";
    const names = D.presentNames || [];
    refs.voiceWho.replaceChildren(...(live && names.length === 1 ? [`${T("rl_speaking")} `, Object.assign(el("b"), { textContent: names[0] })] : [""]));
  }

  function avoid() {
    const desk = document.getElementById("desk");
    const boxes = desk ? [...desk.querySelectorAll(".widget:not(.hidden):not(.fullscreen)")].map((w) => w.getBoundingClientRect()).filter((r) => r.width > 0) : [];
    document.body.classList.toggle("rail-compact", boxes.length > 0);
    document.querySelectorAll(".rail > section").forEach((block) => {
      if (block.hidden) return;
      const r = block.getBoundingClientRect();
      const hit = boxes.some((b) => r.left < b.right + 12 && r.right > b.left - 12 && r.top < b.bottom + 12 && r.bottom > b.top - 12);
      block.classList.toggle("yield", hit);
    });
  }

  function watchDesk() {
    const desk = document.getElementById("desk");
    if (!desk) return;
    new MutationObserver(avoid).observe(desk, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "style"] });
    window.addEventListener("resize", avoid);
    setInterval(avoid, 1500);
    avoid();
  }

  function start() {
    mount();
    window.addEventListener("nuxiva-ear-level", (e) => { state.level = Number(e.detail) || 0; state.heardAt = state.level > 0.02 ? Date.now() : state.heardAt; });
    if (window.PageText) PageText.onChange(() => { render(); });
    refresh();
    state.timer = setInterval(() => { if (!document.hidden) refresh(); }, POLL_MS);
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) paintVoice();
    watchDesk();
  }

  D.Rail = { refresh };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
