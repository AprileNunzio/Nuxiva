(() => {
  const KEYS = new Set(["google", "google_calendar", "google_gmail", "google_tasks", "google_health", "telegram", "band", "phone"]);
  const ICONS = { google: "sparkle", google_calendar: "calendar", google_gmail: "mail", google_tasks: "check", google_health: "fire", telegram: "chat", band: "bt", phone: "phone" };
  const STATES = new Set(["ok", "running", "waiting", "error"]);
  const REASONS = new Set(["revoked", "unavailable", "unsupported", "timeout", "api_disabled", "scope_missing", "health_profile_missing", "quota", "unauthorized", "forbidden", "not_found", "health_grant", "health_preview", "not_linked"]);

  const row = (r, ctx) => {
    const key = KEYS.has(r.key) ? r.key : "";
    const state = STATES.has(r.state) ? r.state : "waiting";
    if (!key) return "";
    const name = ctx.str(r.name, 40);
    const label = name ? `${ctx.t(`k_${key}`)} · ${name}` : ctx.t(`k_${key}`);
    const reason = REASONS.has(r.reason) ? ctx.t(`r_${r.reason}`) : "";
    const age = ctx.num(r.age);
    const note = state === "error" ? reason || ctx.str(r.error, 140) || ctx.t("s_error")
      : state === "ok" && age !== null && age >= 5 ? ctx.ago(ctx.now() - age) : ctx.t(`s_${state}`);
    return `<li class="sp-${state}"><span class="sp-ic" aria-hidden="true">${ctx.icon(ICONS[key])}</span>`
      + `<span class="sp-name">${ctx.esc(label)}</span><span class="sp-st" role="status">${ctx.esc(note)}</span>`
      + `<i class="sp-dot" aria-hidden="true"></i></li>`;
  };

  NuxivaDesk.register("sync_pulse", {
    headline(d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const rows = ctx.arr(data.rows, 40).filter((x) => x && typeof x === "object");
      if (!rows.length) return "";
      const state = (x) => String(x.state ?? "").toLowerCase();
      if (rows.some((x) => /err|fail/.test(state(x)))) return { text: ctx.t("say_bad"), tone: "bad" };
      if (rows.some((x) => /run|wait/.test(state(x)))) return { text: ctx.t("say_busy") };
      return { text: ctx.t("say_ok"), tone: "ok" };
    },
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const who = data.person && typeof data.person === "object" ? ctx.str(data.person.name, 40) : "";
      const phase = STATES.has(data.phase) ? data.phase : "running";
      const rows = ctx.arr(data.rows, 12).filter((r) => r && typeof r === "object");
      const total = rows.length, done = rows.filter((r) => r.state === "ok").length, errors = rows.filter((r) => r.state === "error").length;
      const head = ctx.head({ icon: "refresh", label: ctx.t(`title_${phase}`), title: who,
        chip: errors ? ctx.count("errors", errors) : `${done}/${total}`, live: phase === "running", state: errors ? "bad" : phase === "ok" ? "ok" : "" });
      if (!total) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      el.innerHTML = `${head}
        <div class="sp-wrap sp-${phase}">
          ${ctx.bar(total ? (done / total) * 100 : 0, errors ? "bad" : "")}
          <ul class="sp-list" aria-live="polite">${rows.map((r) => row(r, ctx)).join("")}</ul>
        </div>`;
    },
  });
})();
