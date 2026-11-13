(() => {
  const TONES = new Set(["ok", "warn", "bad"]);
  const opened = new Set();

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

  function node(card, collapsible) {
    let hero = card.el.querySelector(":scope > .ws");
    const wanted = collapsible ? "BUTTON" : "DIV";
    if (hero && hero.tagName !== wanted) { hero.remove(); hero = null; }
    if (!hero) {
      hero = document.createElement(collapsible ? "button" : "div");
      hero.className = "ws";
      if (collapsible) hero.type = "button";
      card.el.insertBefore(hero, card.el.firstChild);
    }
    return hero;
  }

  function apply(card, ctx, relayout) {
    const inst = card.inst;
    if (!inst || !inst.simple) return;
    const mode = inst.simple.mode === "collapse" ? "collapse" : "open";
    const collapsible = mode === "collapse";
    const hero = node(card, collapsible);
    const title = clean(ctx.t("simple_title"), 60) || clean(inst.name, 60);
    const line = say(card.impl, inst.data, ctx);
    const expanded = collapsible && opened.has(inst.key);
    const more = ctx.tc("simple_more"), less = ctx.tc("simple_less");
    card.el.classList.add("simple");
    card.el.classList.toggle("simple-collapsed", collapsible && !expanded);
    card.el.classList.toggle("simple-open", !collapsible || expanded);
    hero.dataset.mode = mode;
    hero.dataset.say = line.tone;
    hero.innerHTML = `<span class="ws-icon">${ctx.icon(inst.simple.icon)}</span>`
      + `<span class="ws-text"><span class="ws-title">${ctx.esc(title)}</span>`
      + `${line.text ? `<span class="ws-say${line.tone ? ` say-${line.tone}` : ""}">${ctx.esc(line.text)}</span>` : ""}</span>`
      + `${collapsible ? `<span class="ws-more">${ctx.esc(expanded ? less : more)}${ctx.icon("chevron")}</span>` : ""}`;
    if (collapsible) {
      hero.setAttribute("aria-expanded", expanded ? "true" : "false");
      hero.onclick = () => {
        if (opened.has(inst.key)) opened.delete(inst.key); else opened.add(inst.key);
        apply(card, ctx, relayout);
        if (typeof relayout === "function") relayout();
      };
    }
  }

  function forget(key) { opened.delete(key); }

  window.NuxivaDeskSimple = Object.freeze({ apply, forget });
})();
