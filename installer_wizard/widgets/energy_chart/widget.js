(() => {
  const ISO = /^[A-Z]{3}$/;

  function chart(values, ctx) {
    const v = values.slice(-288);
    if (v.length < 3) return "";
    const max = Math.max(...v, 1), min = Math.min(0, ...v), span = max - min || 1;
    const y = (x) => (40 - ((x - min) / span) * 38).toFixed(2);
    const pts = v.map((x, i) => `${((i / (v.length - 1)) * 100).toFixed(2)},${y(x)}`);
    const zero = min < 0 ? `<line class="ec-zero" x1="0" x2="100" y1="${y(0)}" y2="${y(0)}"/>` : "";
    return `<figure class="ec-chart"><svg viewBox="0 0 100 42" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="ec-g" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgb(var(--tone))" stop-opacity="0.45"/><stop offset="1" stop-color="rgb(var(--tone))" stop-opacity="0"/></linearGradient></defs>
        ${zero}<path class="ec-area" d="M0,${y(Math.max(0, min))} L${pts.join(" L")} L100,${y(Math.max(0, min))} Z" fill="url(#ec-g)"/><path class="ec-line" d="M${pts.join(" L")}"/></svg>
        <figcaption><span>${ctx.esc(ctx.t("peak"))} ${ctx.esc(ctx.fmt(max / 1000, { maximumFractionDigits: 2 }))} kW</span><span>${ctx.esc(ctx.t("history"))}</span></figcaption></figure>`;
  }

  NuxivaDesk.register("energy_chart", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const load = ctx.num(data.power_w ?? data.load_w ?? data.consumption_w);
      const solar = ctx.num(data.solar_w ?? data.production_w);
      const grid = ctx.num(data.grid_w);
      const battery = ctx.num(data.battery_pct);
      const batteryW = ctx.num(data.battery_w);
      const today = ctx.num(data.today_kwh);
      const solarToday = ctx.num(data.solar_today_kwh);
      const cost = ctx.num(data.cost_today);
      const cur = ctx.str(data.currency, 3).toUpperCase();
      const history = ctx.arr(data.history, 400).map((x) => ctx.num(x)).filter((x) => x !== null);
      if (load === null && solar === null && grid === null && !history.length) {
        el.innerHTML = `${ctx.head({ icon: "bolt", label: ctx.t("label") })}${ctx.metrics(data.content)}`;
        return;
      }
      const kw = (w) => (w === null ? "—" : Math.abs(w) >= 1000 ? `${ctx.fmt(w / 1000, { maximumFractionDigits: 2 })} kW` : `${ctx.fmt(Math.round(w))} W`);
      const exporting = grid !== null && grid < 0;
      const self = load && solar !== null ? Math.max(0, Math.min(100, (solar / load) * 100)) : null;
      const node = (cls, icon, label, value, flow) => `<div class="ec-node ${cls}${flow ? " flow" : ""}"><span class="ec-ic">${ctx.icon(icon)}</span><b>${ctx.esc(value)}</b><small>${ctx.esc(label)}</small></div>`;
      const link = (on, reverse) => `<span class="ec-link${on ? " on" : ""}${reverse ? " rev" : ""}" aria-hidden="true"><i></i></span>`;
      const kv = [
        today !== null ? `<dt>${ctx.esc(ctx.t("today"))}</dt><dd class="mono">${ctx.esc(ctx.fmt(today, { maximumFractionDigits: 1 }))} kWh</dd>` : "",
        solarToday !== null ? `<dt>${ctx.esc(ctx.t("solar_today"))}</dt><dd class="mono">${ctx.esc(ctx.fmt(solarToday, { maximumFractionDigits: 1 }))} kWh</dd>` : "",
        cost !== null ? `<dt>${ctx.esc(ctx.t("cost"))}</dt><dd class="mono">${ctx.esc(ISO.test(cur) ? ctx.fmt(cost, { style: "currency", currency: cur }) : ctx.fmt(cost, { maximumFractionDigits: 2 }))}</dd>` : "",
        battery !== null ? `<dt>${ctx.esc(ctx.t("battery"))}</dt><dd class="mono">${ctx.esc(ctx.fmt(Math.round(battery)))}%${batteryW ? ` · ${ctx.esc(kw(batteryW))}` : ""}</dd>` : "",
      ].join("");
      el.innerHTML = `${ctx.head({ icon: "bolt", label: ctx.t("label"), chip: exporting ? ctx.t("exporting") : self !== null && self >= 99 ? ctx.t("self_powered") : "", state: exporting || (self !== null && self >= 99) ? "ok" : "", live: true })}
        <div class="ec-flow">
          ${solar !== null ? `${node("ec-solar", "sun", ctx.t("solar"), kw(solar), solar > 20)}${link(solar > 20, false)}` : ""}
          ${node("ec-home", "home", ctx.t("home"), kw(load), true)}
          ${grid !== null ? `${link(Math.abs(grid) > 20, !exporting)}${node(`ec-grid${exporting ? " export" : ""}`, "bolt", ctx.t(exporting ? "grid_out" : "grid_in"), kw(Math.abs(grid)), Math.abs(grid) > 20)}` : ""}
        </div>
        ${self !== null ? `<div class="ec-self"><span>${ctx.esc(ctx.t("self_share"))}</span>${ctx.bar(self)}<b>${ctx.esc(String(Math.round(self)))}%</b></div>` : ""}
        ${chart(history, ctx)}
        ${kv ? `<dl class="wk-kv ec-kv">${kv}</dl>` : ""}`;
    },
  });
})();
