(() => {
  const D = window.NuxivaDisplay, { fmt } = D;
  const KIND_KEYS = { wake: "enroll_kind_wake", command: "enroll_kind_command", reading: "enroll_kind_reading" };
  const MAX_TRIES = 3;
  const START_DELAY = 3500;
  const NEXT_DELAY = 900;
  const t = (key, params) => PageText.t("web/display", key, params);
  let session = null, seenRequest = "";

  function box() {
    let el = document.getElementById("enroll");
    if (!el) {
      el = document.createElement("div");
      el.id = "enroll";
      el.className = "enroll";
      el.setAttribute("role", "dialog");
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
      el.addEventListener("click", (e) => {
        if (e.target.closest("[data-stop]")) finish(true);
        if (e.target.closest("[data-skip]")) advance(false);
      });
    }
    return el;
  }

  function note(key, params, tone = "") {
    if (!session) return;
    session.note = { key, params: params || {}, tone };
    draw();
  }

  function draw() {
    const s = session, total = s.plan.length, item = s.plan[Math.min(s.index, total - 1)];
    const pct = Math.round((s.index / total) * 100);
    const n = s.note || { key: "enroll_hint", params: {}, tone: "" };
    box().innerHTML = `<div class="en-card">
      <div class="en-head">${PageText.html("enroll_title", { name: s.name })}</div>
      <div class="en-bar"><i style="width:${pct}%"></i></div>
      <div class="en-step">${PageText.html("enroll_step", { n: Math.min(s.index + 1, total), total })} · ${PageText.html(KIND_KEYS[item.kind] || KIND_KEYS.reading, { name: s.assistant })}</div>
      <div class="en-text">${fmt.esc(item.text)}</div>
      <div class="en-meter" aria-hidden="true"><i id="en-level"></i></div>
      ${s.heard ? `<div class="en-note">${PageText.html("enroll_heard", { text: s.heard })}</div>` : ""}
      <div class="en-note ${n.tone}">${PageText.html(n.key, n.params)}</div>
      <div class="en-actions">
        ${s.tries >= MAX_TRIES - 1 ? `<button class="pill-btn" data-skip>${PageText.html("enroll_skip")}</button>` : ""}
        <button class="pill-btn" data-stop>${PageText.html("enroll_stop")}</button>
      </div></div>`;
    box().classList.add("show");
  }

  function expect() {
    if (session && session.train) D.Ear.send({ type: "enroll_expect", kind: session.plan[session.index].kind });
  }

  function levelNote(level) {
    if (!level) return null;
    if (level.advice === "lower" || level.clipping > 0.02) return "enroll_too_loud";
    if (level.advice === "raise" || level.rms < 0.01) return "enroll_too_soft";
    return null;
  }

  async function save(s) {
    const r = await fetch(`/api/people/${encodeURIComponent(s.slug)}/voice-training`, {
      method: "POST", headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
      body: JSON.stringify({ lang: s.lang, answers: s.answers }) });
    if (!r.ok) throw new Error(`salvataggio non riuscito (${r.status})`);
    return r.json();
  }

  function say(text) {
    if (!text) return;
    D.typeInto(document.getElementById("say"), text);
    D.speak(text);
  }

  async function finish(stopped) {
    if (!session) return;
    D.Ear.send({ type: "enroll_stop" });
    const s = session;
    session = null;
    box().classList.remove("show");
    let text = stopped ? t("enroll_stopped") : t("enroll_done_voice", { name: s.name });
    if (s.train && s.answers.length) {
      try {
        const result = await save(s);
        if (!stopped) text = t("enroll_done_trained", { name: s.name, score: result.score });
      } catch (err) {
        console.warn("Addestramento vocale non salvato", err);
        text = t("enroll_save_failed");
      }
    }
    say(text);
  }

  function advance(matched) {
    if (!session) return;
    session.pausing = false;
    session.index += 1;
    session.tries = 0;
    session.heard = "";
    if (session.index >= session.plan.length) { finish(false); return; }
    session.note = matched ? { key: "enroll_ok_next", params: {}, tone: "ok" } : null;
    draw();
    expect();
  }

  D.Enroll = {
    start(ui) {
      if (!D.local || session) return;
      const plan = Array.isArray(ui.plan) && ui.plan.length ? ui.plan : (ui.sentences || []).map((text) => ({ kind: "reading", text }));
      if (!plan.length) return;
      const assistant = (window.NUXIVA_ASSISTANT && window.NUXIVA_ASSISTANT.name) || "";
      session = { slug: ui.slug, name: ui.name, assistant: ui.assistant || assistant, lang: ui.lang || "it", train: !!ui.train,
                  plan, index: 0, tries: 0, answers: [], heard: "", note: { key: "enroll_get_ready", params: {}, tone: "" } };
      draw();
      setTimeout(() => {
        if (!session) return;
        D.Ear.send({ type: "enroll_start", slug: session.slug, train: session.train });
        session.note = null;
        draw();
        expect();
      }, START_DELAY);
    },
    level(rms) {
      const bar = document.getElementById("en-level");
      if (bar) bar.style.width = `${Math.round(Math.min(1, rms) * 100)}%`;
    },
    progress(ev) {
      if (!session) return;
      if (!("heard" in ev) && session.started === undefined) { session.started = ev.count || 0; return; }
      if (session.pausing) return;
      const item = session.plan[session.index];
      if (session.train) session.heard = ev.heard || "";
      if (!ev.ok) {
        session.tries += 1;
        const wantsName = item.kind === "wake" || item.kind === "command";
        if (session.tries >= MAX_TRIES) {
          if (session.train) session.answers.push({ index: session.index, heard: ev.heard || "", level: ev.level || {} });
          session.pausing = true;
          note("enroll_moving_on", {}, "warn");
          setTimeout(() => advance(false), NEXT_DELAY * 2);
          return;
        }
        note(wantsName ? "enroll_retry_name" : "enroll_retry", { name: ev.name || session.assistant }, "warn");
        return;
      }
      if (session.train) session.answers.push({ index: session.index, heard: ev.heard || "", level: ev.level || {} });
      const advice = levelNote(ev.level);
      session.note = { key: advice || "enroll_ok", params: {}, tone: advice ? "warn" : "ok" };
      session.pausing = true;
      draw();
      setTimeout(() => advance(true), NEXT_DELAY);
    },
    fromState(request, sysState) {
      if (!request || !request.id || request.id === seenRequest) return;
      const s = sysState || (window.NuxivaDisplay && window.NuxivaDisplay.state);
      if (s) {
        if (s.phase && !["READY", "DEGRADED"].includes(s.phase)) return;
        if (!s.installed && s.phase !== "READY") return;
        const steps = s.steps || {};
        const busy = Object.values(steps).some((st) => ["running", "checking", "retrying"].includes(st.status));
        if (busy) return;
        const ear = steps.ear || {};
        const voice = steps.voice || {};
        if (ear.status && ear.status !== "done") return;
        if (voice.status && voice.status !== "done") return;
      }
      seenRequest = request.id;
      if (Date.now() / 1000 - (request.at || 0) < 600) this.start(request);
    },
    unavailable() {
      session = null;
      box().classList.remove("show");
      say(t("enroll_unavailable"));
    },
    get active() { return !!session; },
  };
})();
