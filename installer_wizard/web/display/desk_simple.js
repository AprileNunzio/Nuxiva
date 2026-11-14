(() => {
  const TONES = new Set(["ok", "warn", "bad"]);
  const clean = (value, max = 160) => (typeof value === "string" ? value : "").replace(/[\u0000-\u001F\u007F]/g, " ").replace(/\s+/g, " ").trim().slice(0, max);

  function say(impl, data, ctx) {
    if (!impl || typeof impl.headline !== "function") return { text: "", tone: "" };
    try {
      const out = impl.headline(data, ctx);
      if (typeof out === "string") return { text: clean(out), tone: "" };
      if (out && typeof out === "object") return { text: clean(out.text), tone: TONES.has(out.tone) ? out.tone : "" };
    } catch (err) {
      console.warn("headline non disponibile", err);
    }
    return { text: "", tone: "" };
  }

  function node(card) {
    let hero = card.el.querySelector(":scope > .ws");
    if (hero && hero.tagName !== "DIV") { hero.remove(); hero = null; }
    if (!hero) {
      hero = document.createElement("div");
      hero.className = "ws";
      card.el.insertBefore(hero, card.el.firstChild);
    }
    return hero;
  }

  function apply(card, ctx) {
    const inst = card.inst;
    if (!inst || !inst.simple) return;
    const hero = node(card);
    const title = clean(ctx.t("simple_title"), 60) || clean(inst.name, 60);
    const line = say(card.impl, inst.data, ctx);
    card.el.classList.add("simple", "simple-open");
    card.el.classList.remove("simple-collapsed");
    hero.dataset.say = line.tone;
    hero.innerHTML = `<span class="ws-icon">${ctx.icon(inst.simple.icon)}</span>`
      + `<span class="ws-text"><span class="ws-title">${ctx.esc(title)}</span>`
      + `${line.text ? `<span class="ws-say${line.tone ? ` say-${line.tone}` : ""}">${ctx.esc(line.text)}</span>` : ""}</span>`;
  }

  function forget() {}

  window.NuxivaDeskSimple = Object.freeze({ apply, forget });
})();
