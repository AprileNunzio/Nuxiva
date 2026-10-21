(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const I18n = window.SetupI18n;
  const Net = window.SetupNet;
  const LOCALES = Object.freeze({ it: "it-IT", en: "en-US", es: "es-ES", fr: "fr-FR" });

  const state = { session: null, boot: null, hardware: null, draft: {}, busy: false, link: null };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function log(line) {
    const box = $("synapse-log-stream");
    const ts = new Date().toLocaleTimeString(I18n.current, { hour12: false });
    box.textContent = `${box.textContent}${box.textContent ? "\n" : ""}[${ts}] ${line}`.split("\n").slice(-80).join("\n");
    box.scrollTop = box.scrollHeight;
  }

  function status(text, tone = "") {
    const node = $("bottom-status-msg");
    node.textContent = text || "";
    node.dataset.tone = tone;
  }

  function fail(error) {
    const message = error instanceof Net.SetupError ? (error.message || I18n.t("err-generic")) : I18n.t(error.message || "err-generic");
    status(message, "error");
    log(message);
  }

  function defs() {
    return window.SetupStepDefs || {};
  }

  function current() {
    return defs()[state.session.current_step];
  }

  async function hardware() {
    if (!state.hardware) state.hardware = await Net.json("/api/setup/hardware");
    return state.hardware;
  }

  async function save(updates, step = state.session.current_step) {
    state.session = await Net.json("/api/setup/session/update", { method: "POST", json: { step, updates } });
    return state.session;
  }

  const ctx = {
    el, log, status, fail, save, hardware,
    t: I18n.t,
    net: Net,
    locales: LOCALES,
    get session() { return state.session; },
    get config() { return state.session.config; },
    get boot() { return state.boot; },
    get draft() { return state.draft; },
    lang: () => I18n.current,
    refresh: () => { renderGuide(); renderAnalytics(); },
    goToStep: (n) => goToStep(n),
    switchLanguage: (lang) => switchLanguage(lang)
  };

  function renderStepper() {
    const track = $("stepper-track");
    track.replaceChildren();
    for (let i = 1; i <= state.session.steps; i++) {
      const done = state.session.completed.includes(i);
      const active = i === state.session.current_step;
      const li = el("li", ["step-node", active ? "active" : done ? "completed" : "pending"].join(" "));
      const button = el("button", "step-node-btn");
      button.type = "button";
      button.disabled = i > state.session.max_reached_step || state.busy;
      button.setAttribute("aria-current", active ? "step" : "false");
      button.append(el("span", "step-node-circle", done && !active ? "✓" : i), el("span", "step-node-label", I18n.t(`step-${i}-name`)));
      button.addEventListener("click", () => goToStep(i));
      li.append(button);
      track.append(li);
    }
  }

  function renderGuide() {
    const step = state.session.current_step;
    $("guide-badge").textContent = I18n.t("badge", { n: String(step).padStart(2, "0"), total: String(state.session.steps).padStart(2, "0") });
    $("guide-title").textContent = I18n.t(`title-step-${step}`);
    $("guide-desc").textContent = I18n.t(`desc-step-${step}`);
    const list = $("guide-checklist");
    list.replaceChildren();
    const checks = current() && current().checks ? current().checks(ctx) : [];
    checks.forEach((check) => {
      const li = el("li", `chk-item ${check.ok ? "checked" : check.ok === false ? "failed" : ""}`);
      li.append(el("span", "chk-item-dot", check.ok ? "✓" : check.ok === false ? "✕" : "○"), el("span", "", I18n.t(check.key, check.vars || {})));
      list.append(li);
    });
  }

  function renderAnalytics() {
    const list = $("analytics-list");
    list.replaceChildren();
    const rows = current() && current().analytics ? current().analytics(ctx) : [];
    rows.forEach(([key, value]) => {
      const box = el("div", "metric-box");
      box.append(el("span", "m-label", I18n.t(key)), el("b", "m-val", value === null || value === undefined || value === "" ? "—" : value));
      list.append(box);
    });
  }

  function renderStep() {
    const step = state.session.current_step;
    document.querySelectorAll(".stage-screen").forEach((screen) => { screen.hidden = Number(screen.dataset.step) !== step; });
    $("btn-back").hidden = step <= 1;
    $("btn-next").hidden = step >= state.session.steps;
    renderStepper();
    if (current() && current().render) {
      Promise.resolve(current().render(ctx)).catch(fail).finally(() => ctx.refresh());
    }
    ctx.refresh();
  }

  function leave() {
    if (current() && current().leave) current().leave(ctx);
  }

  async function goToStep(target) {
    if (state.busy || target === state.session.current_step) return;
    leave();
    try {
      state.session = await Net.json("/api/setup/session/navigate", { method: "POST", json: { target_step: target } });
      status("");
      renderStep();
    } catch (error) {
      fail(error);
    }
  }

  async function next() {
    if (state.busy) return;
    const def = current();
    state.busy = true;
    $("btn-next").disabled = true;
    try {
      const updates = def && def.collect ? await def.collect(ctx) : {};
      await save(updates);
      log(I18n.t("log-step-saved", { step: I18n.t(`step-${state.session.current_step}-name`) }));
      state.busy = false;
      await goToStep(state.session.current_step + 1);
    } catch (error) {
      fail(error);
    } finally {
      state.busy = false;
      $("btn-next").disabled = false;
    }
  }

  async function switchLanguage(lang) {
    const code = I18n.supported.includes(lang) ? lang : "it";
    await I18n.applyLanguage(code);
    document.querySelectorAll(".lang-pill").forEach((b) => b.classList.toggle("active", b.dataset.lang === code));
    state.draft.locale = LOCALES[code];
    if (state.session) renderStep();
  }

  function paintConnection() {
    if (!state.link) return;
    $("conn-dot").className = `tele-dot ${state.link.online ? "online" : "offline"}`;
    $("conn-txt").textContent = I18n.t(state.link.online ? "conn-online" : "conn-offline");
    if (state.link.ms !== undefined) $("tele-ping").textContent = `${state.link.ms} ms`;
  }

  function watchConnection() {
    Net.onStatus((s) => {
      state.link = s;
      paintConnection();
    });
  }

  function bind() {
    $("btn-back").addEventListener("click", () => goToStep(state.session.current_step - 1));
    $("btn-next").addEventListener("click", next);
    $("btn-recalibrate").addEventListener("click", () => {
      leave();
      renderStep();
    });
    document.querySelectorAll(".lang-pill").forEach((b) => b.addEventListener("click", () => switchLanguage(b.dataset.lang).catch(fail)));
    window.addEventListener("pagehide", leave);
  }

  async function start() {
    let initial = "it";
    let remembered = "";
    try {
      remembered = localStorage.getItem("nuxiva_ui_lang") || "";
      initial = (remembered || navigator.language || "it").slice(0, 2);
    } catch (error) {
      console.warn("setup: lingua salvata non leggibile", error);
    }
    await switchLanguage(initial);
    watchConnection();
    bind();
    state.boot = await Net.json("/api/setup");
    if (!state.boot.needed) {
      window.location.replace("/");
      return;
    }
    if (state.boot.local && state.boot.code) log(I18n.t("log-code", { code: state.boot.code }));
    state.session = await Net.json("/api/setup/session");
    const saved = (state.session.config.locale || "").slice(0, 2);
    if (saved && saved !== I18n.current && !remembered) await switchLanguage(saved);
    $("hud-brand-text").textContent = (state.session.config.assistant_name || "NUXIVA").toUpperCase();
    renderStep();
  }

  window.addEventListener("setup-i18n-changed", () => {
    paintConnection();
    if (state.session) ctx.refresh();
  });

  document.addEventListener("DOMContentLoaded", () => {
    start().catch((error) => {
      fail(error);
      log(I18n.t("err-start"));
    });
  });
})();
