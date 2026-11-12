(() => {
  "use strict";
  const D = window.NuxivaDisplay;
  const T = window.PageText ? PageText.scope("web/display") : (key) => key;
  const HAZARDS = new Set(["medical", "fire", "intrusion", "violence"]);
  const STAGES = new Set(["ask", "remind", "ack", "stop"]);
  const NUMBER = /^[0-9]{2,6}$/;
  let root = null;
  let timer = 0;
  let deadline = 0;
  let current = { hazard: "medical", number: "112", tone: "spoken" };

  function el(tag, cls, parent) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function build() {
    root = el("section", "rescue-screen hidden", document.body);
    root.setAttribute("role", "alertdialog");
    root.setAttribute("aria-live", "assertive");
    root.setAttribute("aria-labelledby", "rescue-title");
    const wrap = el("div", "rescue-wrap", root);
    el("p", "rescue-kicker", wrap).id = "rescue-kicker";
    const title = el("h2", "rescue-title", wrap);
    title.id = "rescue-title";
    el("p", "rescue-body", wrap).id = "rescue-body";
    el("p", "rescue-count", wrap).id = "rescue-count";
    const actions = el("div", "rescue-actions", wrap);
    actions.id = "rescue-actions";
    const ok = el("button", "rescue-btn rescue-ok", actions);
    ok.type = "button";
    PageText.bind(ok, "rescue_ok");
    ok.addEventListener("click", () => answer("ok"));
    const help = el("button", "rescue-btn rescue-help", actions);
    help.type = "button";
    PageText.bind(help, "rescue_help");
    help.addEventListener("click", () => answer("not_ok"));
    el("p", "rescue-number", wrap).id = "rescue-number";
    PageText.bind(el("p", "rescue-disclaimer", wrap), "rescue_disclaimer");
  }

  function text(id, key, params) {
    const node = document.getElementById(id);
    if (!node) return;
    if (key) PageText.bind(node, key, params);
    else PageText.plain(node, "");
  }

  function answer(value) {
    if (D.Ear && D.Ear.send) D.Ear.send({ type: "rescue_answer", answer: value });
    if (value === "ok") hide();
    else show("remind", current);
  }

  function hide() {
    clearInterval(timer);
    timer = 0;
    if (root) root.classList.add("hidden");
  }

  function tick() {
    const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
    text("rescue-count", left > 0 ? "rescue_countdown" : "", { seconds: left });
    if (left <= 0) { clearInterval(timer); timer = 0; }
  }

  function show(stage, ev) {
    if (!root) build();
    root.dataset.hazard = current.hazard;
    root.dataset.stage = stage;
    root.classList.toggle("rescue-discreet", current.tone === "discreet");
    text("rescue-kicker", `rescue_hazard_${current.hazard}`);
    text("rescue-number", "rescue_number", { number: current.number });
    document.getElementById("rescue-actions").hidden = stage === "ack";
    if (stage === "ask") {
      text("rescue-title", "rescue_ask_title");
      text("rescue-body", current.tone === "discreet" ? "rescue_ask_discreet" : "rescue_ask_body");
      deadline = Date.now() + Math.max(5, Math.min(120, Number(ev.seconds) || 30)) * 1000;
      clearInterval(timer);
      timer = setInterval(tick, 1000);
      tick();
      if (current.tone !== "discreet" && D.speak) D.speak(T("rescue_ask_spoken"));
    } else if (stage === "remind") {
      clearInterval(timer);
      timer = 0;
      text("rescue-count", "");
      text("rescue-title", "rescue_remind_title");
      text("rescue-body", "rescue_remind_body", { number: current.number });
      if (current.tone !== "discreet" && D.speak) D.speak(T("rescue_remind_body", { number: current.number }));
    } else {
      clearInterval(timer);
      timer = 0;
      text("rescue-count", "");
      text("rescue-title", "rescue_ack_title");
      text("rescue-body", ev.name ? "rescue_ack_body" : "rescue_ack_anon", { name: ev.name || "" });
      if (current.tone !== "discreet" && D.speak) D.speak(T(ev.name ? "rescue_ack_body" : "rescue_ack_anon", { name: ev.name || "" }));
    }
    root.classList.remove("hidden");
    if (D.pingActivity) D.pingActivity(true);
  }

  function event(ev) {
    if (!ev || !STAGES.has(ev.stage)) return;
    if (ev.stage === "stop") return hide();
    current = {
      hazard: HAZARDS.has(ev.hazard) ? ev.hazard : "medical",
      number: NUMBER.test(String(ev.number || "")) ? String(ev.number) : "112",
      tone: ev.tone === "discreet" ? "discreet" : "spoken",
    };
    show(ev.stage, ev);
  }

  D.RescuePrompt = Object.freeze({ event, hide });
})();
