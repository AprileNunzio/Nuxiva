(() => {
  const PCT = /(\d{1,3}(?:[.,]\d+)?)\s*%/;
  const initials = (s) => s.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => Array.from(w)[0]).join("").toUpperCase() || "?";

  function people(d, ctx) {
    const src = Array.isArray(d.people) ? d.people : d.items;
    return ctx.arr(src, 12).filter((p) => p && typeof p === "object" && !p.none).map((p) => {
      const name = ctx.pick(p, ["name", "label"], 40);
      const value = ctx.str(p.value, 60);
      const known = typeof p.known === "boolean" ? p.known : p.status === "ok";
      let conf = ctx.num(p.confidence);
      if (conf === null) { const m = value.match(PCT); conf = m ? Number(m[1].replace(",", ".")) / 100 : null; }
      if (conf !== null && conf > 1) conf /= 100;
      const near = typeof p.near === "boolean" ? p.near : /vicin|near|cerca|proche/i.test(value) ? true : /lontan|far|lejos|loin/i.test(value) ? false : null;
      return { name, known, conf: conf === null ? null : Math.max(0, Math.min(1, conf)), near, real: Boolean(p.status || typeof p.known === "boolean") };
    }).filter((p) => p.name && p.real);
  }

  NuxivaDesk.register("people_seen", {
    render(el, d, ctx) {
      const list = people(d && typeof d === "object" ? d : {}, ctx).sort((a, b) => (b.known - a.known) || ((b.near ? 1 : 0) - (a.near ? 1 : 0)));
      const unknown = list.filter((p) => !p.known).length;
      const head = ctx.head({ icon: "eye", label: ctx.t("label"), chip: list.length ? ctx.count("people", list.length) : "", live: list.length > 0, state: unknown ? "warn" : "" });
      if (!list.length) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      el.innerHTML = `${head}<ul class="ps-list">${list.map((p, i) => `<li class="ps-row${p.known ? "" : " unk"}" style="--i:${i}">
          <span class="ps-av" aria-hidden="true">${p.known ? ctx.esc(initials(p.name)) : ctx.icon("user")}${p.near ? `<i class="ps-near"></i>` : ""}</span>
          <span class="ps-txt"><b>${ctx.esc(p.known ? p.name : ctx.t("unknown"))}</b><small>${ctx.esc([p.near === null ? "" : ctx.t(p.near ? "near" : "far"), !p.known && p.name ? p.name : ""].filter(Boolean).join(" · "))}</small></span>
          ${p.known && p.conf !== null ? `<span class="ps-conf" title="${ctx.esc(ctx.t("confidence"))}"><span class="mono">${Math.round(p.conf * 100)}%</span>${ctx.bar(p.conf * 100, p.conf < 0.6 ? "warn" : "")}</span>` : `<span></span>`}</li>`).join("")}</ul>`;
    },
  });
})();
