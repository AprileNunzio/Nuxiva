(() => {
  const KEYS = Object.freeze({
    today: /^(today|oggi|hoy|aujourd|giorno|day)/i,
    month: /^(month|mese|mes|mois)/i,
    budget: /^(budget|presupuesto|limite|limit|tetto)/i,
  });
  const ISO = /^[A-Z]{3}$/;
  const SYMBOL = Object.freeze({ "€": "EUR", "$": "USD", "£": "GBP", "¥": "JPY", "CHF": "CHF" });

  function money(text, ctx) {
    const s = ctx.str(text, 40);
    const m = s.replace(/\s/g, "").match(/(-?\d+(?:[.,]\d+)*)/);
    if (!m) return null;
    let raw = m[1];
    if (/,\d{1,2}$/.test(raw)) raw = raw.replace(/\./g, "").replace(",", ".");
    else raw = raw.replace(/,/g, "");
    const value = ctx.num(raw);
    const sym = Object.keys(SYMBOL).find((k) => s.includes(k));
    return value === null ? null : { value, currency: sym ? SYMBOL[sym] : "" };
  }

  function parse(d, ctx) {
    const out = { today: ctx.num(d.today), month: ctx.num(d.month), budget: ctx.num(d.budget), currency: "" };
    const cur = ctx.str(d.currency, 8);
    out.currency = ISO.test(cur.toUpperCase()) ? cur.toUpperCase() : SYMBOL[cur] || "";
    const rest = [];
    for (const line of ctx.lines(d.content, 12, 2000)) {
      const p = ctx.pair(line, 32);
      const key = p && Object.keys(KEYS).find((k) => KEYS[k].test(p[1].trim()));
      const m = p && money(p[2], ctx);
      if (key && m && out[key] === null) {
        out[key] = m.value;
        if (!out.currency && m.currency) out.currency = m.currency;
      } else rest.push(line);
    }
    out.models = ctx.arr(d.models, 12).map((m) => (m && typeof m === "object" ? { name: ctx.pick(m, ["name", "model", "id"], 48), cost: ctx.num(m.cost ?? m.spent), tokens: ctx.num(m.tokens) } : null))
      .filter((m) => m && m.name && m.cost !== null && m.cost >= 0).sort((a, b) => b.cost - a.cost).slice(0, 5);
    out.rest = rest;
    return out;
  }

  NuxivaDesk.register("api_costs", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const c = parse(data, ctx);
      const cash = (v) => (v === null ? "—" : ctx.fmt(v, c.currency ? { style: "currency", currency: c.currency, currencyDisplay: "narrowSymbol", maximumFractionDigits: v < 10 ? 2 : 0 } : { maximumFractionDigits: 2 }));
      if (c.month === null && c.today === null && !c.models.length) {
        el.innerHTML = `${ctx.head({ icon: "coin", label: ctx.t("label") })}${ctx.metrics(data.content)}`;
        return;
      }
      const now = new Date();
      const days = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
      const day = now.getDate();
      const projected = c.month !== null && day > 0 ? (c.month / day) * days : null;
      const used = c.budget && c.month !== null ? (c.month / c.budget) * 100 : null;
      const risk = used === null ? "" : used >= 100 || (projected !== null && projected > c.budget * 1.05) ? "bad" : used >= 75 || (projected !== null && projected > c.budget * 0.9) ? "warn" : "ok";
      const total = c.models.reduce((a, m) => a + m.cost, 0) || 1;
      const models = c.models.map((m) => `<li><div class="ac-mrow"><span>${ctx.esc(m.name)}</span><b>${ctx.esc(cash(m.cost))}</b></div>${ctx.bar((m.cost / total) * 100)}${m.tokens !== null ? `<small>${ctx.esc(ctx.t("tokens", { n: ctx.fmt(m.tokens, { notation: "compact" }) }))}</small>` : ""}</li>`).join("");
      el.innerHTML = `${ctx.head({ icon: "coin", label: ctx.t("label"), chip: used === null ? "" : ctx.t(`risk_${risk}`), state: risk === "ok" ? "ok" : risk })}
        <div class="ac-top">
          ${used !== null ? ctx.ring(Math.min(100, used), `${Math.round(used)}%`, ctx.t("of_budget")) : ""}
          <div class="ac-hero">
            <span class="wk-num sm">${ctx.esc(cash(c.month ?? c.today))}</span>
            <span class="wk-sub">${ctx.esc(ctx.t(c.month !== null ? "this_month" : "today"))}</span>
          </div>
        </div>
        <dl class="wk-kv ac-kv">
          ${c.month !== null && c.today !== null ? `<dt>${ctx.esc(ctx.t("today"))}</dt><dd class="mono">${ctx.esc(cash(c.today))}</dd>` : ""}
          ${projected !== null ? `<dt>${ctx.esc(ctx.t("forecast"))}</dt><dd class="mono${risk === "bad" ? " ac-bad" : risk === "warn" ? " ac-warn" : ""}">${ctx.esc(cash(projected))}</dd>` : ""}
          ${c.budget ? `<dt>${ctx.esc(ctx.t("budget"))}</dt><dd class="mono">${ctx.esc(cash(c.budget))}</dd>` : ""}
          ${c.budget && c.month !== null ? `<dt>${ctx.esc(ctx.t("left"))}</dt><dd class="mono">${ctx.esc(cash(Math.max(0, c.budget - c.month)))}</dd>` : ""}
        </dl>
        ${models ? `<ul class="ac-models">${models}</ul>` : ""}
        ${c.rest.length ? `<div class="wk-sub ac-rest">${c.rest.slice(0, 4).map(ctx.esc).join("<br>")}</div>` : ""}`;
    },
  });
})();
