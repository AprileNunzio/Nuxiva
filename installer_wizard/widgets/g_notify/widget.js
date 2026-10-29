(() => {
  const R = 26, C = 2 * Math.PI * R, WINDOW = 1800;
  const GROUP_ICON = { birthday: "gift", event: "pin", appointment: "clock" };
  const KIND = { mail: ["mail", "new_mail", "new"], calendar: ["calendar", "new_event", "new"], tasks: ["check", "tasks", "due"], notes: ["pen", "note", "new"] };

  function stop(el) { clearInterval(el._gnT); el._gnT = 0; }

  function tick(el, at, ctx) {
    const left = Math.max(0, at - ctx.now());
    const span = el.querySelector(".gn-left"), arc = el.querySelector(".gn-arc"), ring = el.querySelector(".gn-ring");
    if (!span || !span.isConnected) { stop(el); return; }
    span.textContent = left <= 0 ? ctx.t("now") : left >= 3600 ? `${Math.floor(left / 3600)}h ${Math.floor((left % 3600) / 60)}m` : ctx.mmss(left);
    if (arc) arc.style.strokeDashoffset = `${C * (1 - Math.min(1, left / WINDOW))}`;
    if (ring) ring.classList.toggle("due", left <= 0);
    if (left <= 0) stop(el);
  }

  const initial = (s) => (Array.from(s.replace(/["'<>]/g, "").trim())[0] || "?").toUpperCase();

  function event(d, ctx) {
    const title = ctx.str(d.title, 160), where = ctx.str(d.text, 160), at = ctx.stamp(d.at);
    if (!title && !at) return `${ctx.head({ icon: "calendar", label: ctx.t("appointment"), title: ctx.str(d.who, 40) })}${ctx.empty(ctx.t("calm"))}`;
    return `${ctx.head({ icon: "calendar", label: ctx.t("appointment"), title: ctx.str(d.who, 40), chip: ctx.t("soon"), live: true })}
      <div class="wk-hero gn-hero"><span class="gn-ring"><svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="${R}" class="gn-track"/>
        <circle cx="32" cy="32" r="${R}" class="gn-arc" stroke-dasharray="${C}" stroke-dashoffset="${C}"/></svg><b class="gn-left">—</b></span>
        <span class="gn-main"><span class="wk-title">${ctx.esc(title)}</span>
          ${at ? `<span class="wk-sub">${ctx.icon("clock")} ${ctx.esc(ctx.when(at))}</span>` : ""}
          ${where ? `<span class="wk-sub gn-where">${ctx.icon("pin")} ${ctx.esc(where)}</span>` : ""}</span></div>`;
  }

  function brief(d, ctx) {
    const items = ctx.arr(d.items, 3).filter((x) => x && typeof x === "object" && ctx.str(x.label, 30));
    const groups = ctx.arr(d.groups, 4).filter((g) => g && typeof g === "object" && Array.isArray(g.entries) && g.entries.length);
    const text = ctx.str(d.text, 300);
    return `${ctx.head({ icon: "sun", label: ctx.t("your_day"), title: ctx.str(d.who, 40) })}
      ${items.length ? `<div class="wk-cols ${items.length === 3 ? "three" : ""} gn-stats">${items.map((x) => `<div class="wk-col"><span class="wk-num sm">${ctx.esc(ctx.str(x.value, 6) || "0")}</span><h5>${ctx.esc(ctx.str(x.label, 30))}</h5></div>`).join("")}</div>` : ""}
      ${groups.map((g) => {
        const entries = g.entries.filter((e) => e && typeof e === "object" && ctx.str(e.title, 120));
        return `<div class="wk-col gn-group"><h5>${ctx.icon(GROUP_ICON[g.key] || "bell")}${ctx.esc(ctx.str(g.label, 30))}</h5><ul class="wk-list">${entries.slice(0, 4).map((e) => `<li class="wk-row gn-entry">
          <span><b>${ctx.esc(ctx.str(e.title, 120))}</b>${ctx.str(e.where, 80) ? `<small>${ctx.esc(ctx.str(e.where, 80))}</small>` : ""}</span><span class="wk-val mono">${ctx.esc(ctx.str(e.time, 20))}</span></li>`).join("")}</ul>
          ${entries.length > 4 ? `<div class="wk-faint gn-more">${ctx.esc(ctx.t("more", { n: entries.length - 4 }))}</div>` : ""}</div>`;
      }).join("")}
      ${text ? `<div class="wk-text gn-say">${ctx.esc(text)}</div>` : ""}
      ${!items.length && !groups.length && !text ? ctx.empty(ctx.t("calm")) : ""}`;
  }

  function note(d, ctx) {
    const [ic, label, chip] = KIND[d.kind] || KIND.mail;
    const from = ctx.str(d.from, 120), title = ctx.str(d.title, 200), text = ctx.str(d.text, 400);
    const any = Boolean(from || title || text);
    return `${ctx.head({ icon: ic, label: ctx.t(label), title: ctx.str(d.who, 40), chip: any ? ctx.t(chip) : "", live: any })}
      ${from ? `<div class="gn-from"><span class="gn-avatar" aria-hidden="true">${ctx.esc(initial(from))}</span><span class="wk-sub">${ctx.esc(from)}</span></div>` : ""}
      ${title ? `<div class="wk-title gn-subject">${ctx.esc(title)}</div>` : ""}
      ${text ? `<div class="wk-sub gn-text">${ctx.esc(text)}</div>` : ""}
      ${!any ? ctx.empty(ctx.t("calm")) : ""}`;
  }

  function render(el, d, ctx) {
    stop(el);
    const data = d && typeof d === "object" ? d : {};
    el.innerHTML = data.kind === "event" ? event(data, ctx) : data.kind === "brief" ? brief(data, ctx) : note(data, ctx);
    const at = data.kind === "event" ? ctx.stamp(data.at) : null;
    if (at) {
      tick(el, at, ctx);
      if (at > ctx.now()) el._gnT = setInterval(() => tick(el, at, ctx), 1000);
    }
  }

  NuxivaDesk.register("g_notify", { render, destroy: stop });
})();
