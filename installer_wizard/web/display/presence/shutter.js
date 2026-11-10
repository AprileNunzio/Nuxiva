(() => {
  const KINDS = new Set(["empty", "guest_only", "authorized", "mixed", "uncertain"]);
  const OPEN = new Set(["authorized", "mixed"]);
  const PRIVATE = new Set(["personal", "sensitive"]);
  const SENSITIVE_IDS = new Set(["vault", "passwords", "bank", "credentials", "secrets"]);
  const SENSITIVE_RE = /\b(password|passphrase|iban|conto\s+corrente|carta\s+di\s+credito|cvv|secret[_\s-]?key|api[_\s-]?key|seed\s+phrase)\b/i;
  const UNLOCK_TTL_MS = 45000;
  const STEP_TTL_MS = 12000;
  const unlockedUntil = new Map();
  const pendingStep = new Map();
  let kind = "";
  let browserDesk = false;

  const t = (key, fallback) => (window.PageText && typeof window.PageText.t === "function" ? window.PageText.t(key) || fallback : fallback);
  const isPrivate = (card) => !!(card.inst && (card.inst.personal || PRIVATE.has(card.inst.sensitivity)));

  function isSensitive(card) {
    if (!card || !card.inst) return false;
    if (card.inst.sensitivity === "sensitive" || SENSITIVE_IDS.has(card.inst.id)) return true;
    const d = card.inst.data;
    if (d && (d.sensitive === true || d.requires_double_permission === true)) return true;
    const raw = JSON.stringify(d || "");
    if (SENSITIVE_RE.test(raw)) return true;
    const body = card.el && card.el.querySelector(".w-body");
    return !!(body && SENSITIVE_RE.test(body.textContent || ""));
  }

  function ensureDoubleGate(card) {
    const key = card.inst.key || card.inst.id;
    const now = Date.now();
    const openUntil = unlockedUntil.get(key) || 0;
    let gateEl = card.el.querySelector(".w-double-gate");
    if (openUntil > now) {
      card.el.classList.remove("w-double-locked");
      if (gateEl) gateEl.remove();
      return;
    }
    card.el.classList.add("w-double-locked");
    const stepAt = pendingStep.get(key) || 0;
    const inStep2 = stepAt > 0 && now - stepAt < STEP_TTL_MS;
    if (!gateEl) {
      gateEl = document.createElement("div");
      gateEl.className = "w-double-gate";
      card.el.appendChild(gateEl);
    }
    const mode = inStep2 ? "step2" : "step1";
    if (gateEl.dataset.mode === mode) return;
    gateEl.dataset.mode = mode;
    gateEl.innerHTML = `<div class="w-dg-box">`
      + `<span class="w-dg-icon">🔐</span>`
      + `<strong class="w-dg-title">${t("privacy_sensitive_gate_title", "Contenuto sensibile protetto")}</strong>`
      + `<p class="w-dg-sub">${t("privacy_sensitive_gate_sub", "Password, conto o dati riservati: richiesto doppio permesso.")}</p>`
      + `<button type="button" class="w-dg-btn ${inStep2 ? "confirm" : ""}">`
      + `${inStep2 ? t("privacy_sensitive_step2", "Conferma secondo permesso (2/2)") : t("privacy_sensitive_step1", "Richiedi permesso di visione (1/2)")}`
      + `</button></div>`;
    const btn = gateEl.querySelector(".w-dg-btn");
    if (btn) {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const ts = Date.now();
        const first = pendingStep.get(key) || 0;
        if (first > 0 && ts - first < STEP_TTL_MS) {
          pendingStep.delete(key);
          unlockedUntil.set(key, ts + UNLOCK_TTL_MS);
          ensureDoubleGate(card);
          setTimeout(() => syncCards(), UNLOCK_TTL_MS + 100);
        } else {
          pendingStep.set(key, ts);
          gateEl.dataset.mode = "";
          ensureDoubleGate(card);
          setTimeout(() => {
            if (pendingStep.get(key) === ts) {
              pendingStep.delete(key);
              if (gateEl.isConnected) { gateEl.dataset.mode = ""; ensureDoubleGate(card); }
            }
          }, STEP_TTL_MS + 50);
        }
      });
    }
  }

  function syncCards() {
    const desk = window.NuxivaDesk;
    if (!desk || typeof desk.cards !== "function") return;
    const authorized = kind === "authorized";
    for (const card of desk.cards()) {
      if (!authorized && isPrivate(card)) {
        card.el.classList.add("w-sealed");
      } else {
        card.el.classList.remove("w-sealed");
      }
      if (authorized && isSensitive(card)) {
        ensureDoubleGate(card);
      } else {
        card.el.classList.remove("w-double-locked");
        const g = card.el.querySelector(".w-double-gate");
        if (g) g.remove();
      }
    }
  }

  function effectiveKind(rawKind, state) {
    const base = KINDS.has(rawKind) ? rawKind : "uncertain";
    if (base === "authorized" || base === "mixed" || base === "guest_only") return base;
    const people = (state && state.presence && state.presence.people) || [];
    const hasStranger = people.some((p) => p && !p.known);
    if (hasStranger) return base;
    const hasKnownOwner = people.some((p) => p && p.known && (!p.role || ["owner", "family"].includes(p.role)));
    const nowSec = Date.now() / 1000;
    const recentGreeting = !!(state && state.greeting && state.greeting.at && nowSec - state.greeting.at < 60 && (state.greeting.names || []).length);
    const recentDialogue = !!(state && state.live_dialogue && state.live_dialogue.ts && nowSec - state.live_dialogue.ts < 60);
    const D = window.NuxivaDisplay;
    const displayPresent = !!(D && ((D.presentNames && D.presentNames.length > 0) || (D.greetSeen && Date.now() - D.greetSeen < 45000)));
    if (hasKnownOwner || recentGreeting || recentDialogue || displayPresent) return "authorized";
    return base;
  }

  function apply(next, browser = false) {
    const value = KINDS.has(next) ? next : "uncertain";
    const changed = value !== kind || browser !== browserDesk;
    kind = value;
    browserDesk = browser;
    document.body.dataset.audience = value;
    document.body.classList.toggle("nucleus-only", !browserDesk && !OPEN.has(value));
    syncCards();
    if (changed) window.dispatchEvent(new CustomEvent("nuxiva:audience", { detail: { kind: value } }));
  }

  function gate(audience) {
    document.body.dataset.gate = audience && audience.gate === true ? "on" : "off";
  }

  window.addEventListener("nuxiva:state", (ev) => {
    const state = ev.detail || {};
    const audience = state.audience;
    gate(audience);
    const resolved = effectiveKind(audience && audience.kind, state);
    apply(resolved, audience?.browser_desk === true && audience.gate === false);
  });
  window.NuxivaShutter = Object.freeze({ get kind() { return kind; }, apply, syncCards });
})();
