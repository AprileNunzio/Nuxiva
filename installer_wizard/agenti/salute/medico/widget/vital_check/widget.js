(() => {
  const MAX = 4;
  const HEART = `<svg class="vc-heart" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.4.7-1.2 2.2-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>`;

  const value = (v, lo, hi, ctx) => {
    const n = ctx.num(v);
    return n !== null && n >= lo && n <= hi ? Math.round(n) : null;
  };

  const row = (raw, ctx) => {
    const d = raw && typeof raw === "object" ? raw : {};
    const person = d.person && typeof d.person === "object" ? d.person : {};
    const vals = d.values && typeof d.values === "object" ? d.values : {};
    return {
      name: ctx.str(person.name, 40), first: ctx.str(person.name, 40).split(" ")[0], initials: ctx.str(person.initials, 3),
      heart: value(vals.heart_rate, 40, 180, ctx), breath: value(vals.resp_rate, 5, 40, ctx), source: d.source === "device" ? "device" : "camera",
    };
  };

  const parse = (raw, ctx) => {
    const d = raw && typeof raw === "object" ? raw : {};
    return ctx.arr(d.people, MAX).map((p) => row(p, ctx)).filter((p) => p.heart !== null);
  };

  const sync = () => `-${(Date.now() % 1200) / 1000}s`;

  const card = (p, ctx, solo) => {
    const beat = `${(60 / p.heart).toFixed(3)}s`;
    const breath = p.breath === null ? "" : `<span class="vc-breath"><small>${ctx.esc(ctx.t("m_breath"))}</small><b>${ctx.esc(ctx.fmt(p.breath))}</b><small>${ctx.esc(ctx.t("per_min"))}</small></span>`;
    const label = ctx.t("aria_row", { name: p.name, bpm: p.heart });
    return `<li class="vc-row${solo ? " vc-solo" : ""}" style="--beat:${beat};--sync:${sync()}" aria-label="${ctx.esc(label)}">
      <span class="vc-who">${solo ? "" : `<i aria-hidden="true">${ctx.esc(p.initials)}</i>`}<span>${ctx.esc(p.first || p.name)}</span></span>
      <span class="vc-bpm">${HEART}<b>${ctx.esc(ctx.fmt(p.heart))}</b><small>bpm</small></span>
      ${breath}
      <span class="vc-src">${ctx.esc(ctx.t(p.source === "device" ? "src_device" : "src_camera"))}</span>
    </li>`;
  };

  NuxivaDesk.register("vital_check", {
    render(el, raw, ctx) {
      const list = parse(raw, ctx);
      if (!list.length) {
        el.innerHTML = "";
        return;
      }
      const solo = list.length === 1;
      el.innerHTML = `${ctx.head({ icon: solo ? "user" : "users", label: ctx.t("title"), title: solo ? list[0].name : ctx.count("people", list.length) })}
        <ul class="vc-list${solo ? "" : " vc-many"}" role="status" aria-live="polite">${list.map((p) => card(p, ctx, solo)).join("")}</ul>
        <p class="vc-note">${ctx.esc(ctx.t("not_medical"))}</p>`;
    },
  });
})();
