(() => {
  const MAX = 4;
  const CELLS = 3;
  const CELL = "l30 0 c2 -5 6 -5 8 0 l6 0 l3 4 l4 -32 l4 38 l3 -10 l8 0 c4 -9 12 -9 16 0 l18 0";
  const TRACE = `M0 30 ${CELL.repeat(CELLS).replace(/l18 0l30 0/g, "l48 0")}`;
  const HEART = "M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.4.7-1.2 2.2-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z";
  let seq = 0;

  const value = (v, lo, hi, ctx) => {
    const n = ctx.num(v);
    return n !== null && n >= lo && n <= hi ? Math.round(n) : null;
  };

  const row = (raw, ctx) => {
    const d = raw && typeof raw === "object" ? raw : {};
    const person = d.person && typeof d.person === "object" ? d.person : {};
    const vals = d.values && typeof d.values === "object" ? d.values : {};
    const name = ctx.str(person.name, 40);
    return {
      slug: ctx.str(person.slug, 64), name, first: name.split(" ")[0], initials: ctx.str(person.initials, 3),
      heart: value(vals.heart_rate, 40, 180, ctx), breath: value(vals.resp_rate, 5, 40, ctx), source: d.source === "device" ? "device" : "camera",
    };
  };

  const parse = (raw, ctx) => {
    const d = raw && typeof raw === "object" ? raw : {};
    return ctx.arr(d.people, MAX).map((p) => row(p, ctx)).filter((p) => p.heart !== null);
  };

  const timing = (bpm) => {
    const beat = 60000 / bpm, now = Date.now();
    return `--beat:${(beat / 1000).toFixed(3)}s;--sweep:${((beat * CELLS) / 1000).toFixed(3)}s;--sync:-${((now % beat) / 1000).toFixed(3)}s;--sync-sweep:-${((now % (beat * CELLS)) / 1000).toFixed(3)}s`;
  };

  const ecg = () => {
    const id = `vc-m${++seq}`;
    return `<svg class="vc-ecg" viewBox="0 0 ${CELLS * 100} 44" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="${id}-g" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.85" stop-color="#fff" stop-opacity="0.9"/><stop offset="1" stop-color="#fff"/></linearGradient>
        <linearGradient id="${id}-e" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.12" stop-color="#fff"/><stop offset="0.88" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
        <mask id="${id}-s" maskUnits="userSpaceOnUse" x="0" y="0" width="${CELLS * 100}" height="44"><rect class="vc-sweep" x="-90" y="0" width="90" height="44" fill="url(#${id}-g)"/></mask>
        <mask id="${id}-f" maskUnits="userSpaceOnUse" x="0" y="0" width="${CELLS * 100}" height="44"><rect width="${CELLS * 100}" height="44" fill="url(#${id}-e)"/></mask>
      </defs>
      <g mask="url(#${id}-f)"><path class="vc-base" d="${TRACE}"/><path class="vc-live" d="${TRACE}" mask="url(#${id}-s)"/></g>
    </svg>`;
  };

  const card = (p, ctx, solo) => {
    const breath = p.breath === null ? "" : `<span class="vc-breath"><b data-k="breath">${ctx.esc(ctx.fmt(p.breath))}</b><small>${ctx.esc(ctx.t("m_breath"))} ${ctx.esc(ctx.t("per_min"))}</small></span>`;
    const label = `${ctx.t("aria_row", { name: p.name, bpm: p.heart })}. ${ctx.t(p.source === "device" ? "src_device" : "src_camera")}. ${ctx.t("not_medical")}`;
    return `<li class="vc-row${solo ? " vc-solo" : ""}" data-slug="${ctx.esc(p.slug)}" style="${timing(p.heart)}" aria-label="${ctx.esc(label)}">
      ${solo ? "" : `<span class="vc-who">${ctx.esc(p.first || p.name)}</span>`}
      <span class="vc-core">
        <span class="vc-heart" aria-hidden="true"><i></i><svg viewBox="0 0 24 24"><path d="${HEART}"/></svg></span>
        <span class="vc-bpm"><b data-k="bpm">${ctx.esc(ctx.fmt(p.heart))}</b><small>${ctx.esc(ctx.t("unit"))}</small></span>
        ${breath}
      </span>
      ${ecg()}
    </li>`;
  };

  const shape = (list) => list.map((p) => `${p.slug}:${p.heart}:${p.breath === null}`).join("|");

  function render(el, raw, ctx) {
    const list = parse(raw, ctx);
    if (!list.length) {
      el.innerHTML = "";
      el.dataset.shape = "";
      return;
    }
    const solo = list.length === 1;
    el.dataset.shape = shape(list);
    el.innerHTML = `${ctx.head({ label: ctx.t("title"), title: solo ? list[0].name : ctx.count("people", list.length) })}
        <ul class="vc-list${solo ? "" : " vc-many"}" role="status" aria-live="polite">${list.map((p) => card(p, ctx, solo)).join("")}</ul>`;
  }

  NuxivaDesk.register("vital_check", {
    render,
    update(el, raw, ctx) {
      const list = parse(raw, ctx);
      if (!list.length || el.dataset.shape !== shape(list)) {
        render(el, raw, ctx);
        return;
      }
      for (const p of list) {
        const li = [...el.querySelectorAll(".vc-row")].find((n) => n.dataset.slug === p.slug);
        const b = li && li.querySelector('[data-k="breath"]');
        if (b && p.breath !== null) b.textContent = ctx.fmt(p.breath);
      }
    },
  });
})();
