(() => {
  const FADE_MS = 120;
  const KINDS = new Set(["empty", "guest_only", "authorized", "mixed", "uncertain"]);
  const OPEN = new Set(["authorized", "mixed"]);
  const PRIVATE = new Set(["personal", "sensitive"]);
  let kind = "";

  const isPrivate = (card) => !!(card.inst && (card.inst.personal || PRIVATE.has(card.inst.sensitivity)));

  function seal() {
    const desk = window.NuxivaDesk;
    if (!desk || typeof desk.cards !== "function") return;
    for (const card of desk.cards()) {
      if (!isPrivate(card) || card.el.classList.contains("w-sealed")) continue;
      card.el.classList.add("w-sealed");
      setTimeout(() => {
        const body = card.el.querySelector(".w-body");
        if (body) body.replaceChildren();
      }, FADE_MS);
    }
  }

  function apply(next) {
    const value = KINDS.has(next) ? next : "uncertain";
    if (value === kind) return;
    kind = value;
    document.body.dataset.audience = value;
    document.body.classList.toggle("nucleus-only", !OPEN.has(value));
    if (value !== "authorized") seal();
    window.dispatchEvent(new CustomEvent("nuxiva:audience", { detail: { kind: value } }));
  }

  window.addEventListener("nuxiva:state", (ev) => apply(ev.detail && ev.detail.audience && ev.detail.audience.kind));
  window.NuxivaShutter = Object.freeze({ get kind() { return kind; }, apply });
})();
