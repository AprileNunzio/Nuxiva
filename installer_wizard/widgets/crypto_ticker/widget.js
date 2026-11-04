(() => {
  const ISO = /^[A-Z]{3}$/;
  const SYMBOL = Object.freeze({ "€": "EUR", "$": "USD", "£": "GBP" });
  const LINE = /^([A-Za-z0-9]{2,10})(?:\s*\(([^)]{1,30})\))?\s*:\s*([€$£]?\s*-?\d[\d.,]*\s*[€$£]?)\s*(?:\(?\s*([+\-−]?\d+(?:[.,]\d+)?)\s*%\s*\)?)?/;

  const amount = (s) => {
    let raw = String(s).replace(/[^\d.,-]/g, "");
    if (/,\d{1,8}$/.test(raw) && (raw.match(/,/g) || []).length === 1) raw = raw.replace(/\./g, "").replace(",", ".");
    else raw = raw.replace(/,/g, "");
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  };

  function spark(values, up) {
    const v = values.filter((x) => Number.isFinite(x)).slice(-60);
    if (v.length < 2) return "";
    const min = Math.min(...v), max = Math.max(...v), span = max - min || 1;
    const pts = v.map((x, i) => `${((i / (v.length - 1)) * 100).toFixed(2)},${(28 - ((x - min) / span) * 26).toFixed(2)}`);
    return `<svg class="ct-spark ${up ? "up" : "down"}" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true"><path class="area" d="M0,30 L${pts.join(" L")} L100,30 Z"/><path class="line" d="M${pts.join(" L")}"/></svg>`;
  }

  function parse(d, ctx) {
    const cur = ctx.str(d.currency, 4).toUpperCase();
    let currency = ISO.test(cur) ? cur : SYMBOL[ctx.str(d.currency, 2)] || "";
    const coins = ctx.arr(d.coins ?? d.assets, 8).map((c) => {
      if (!c || typeof c !== "object") return null;
      const symbol = ctx.pick(c, ["symbol", "ticker", "id"], 10).toUpperCase();
      const price = ctx.num(c.price);
      if (!symbol || price === null) return null;
      return { symbol, name: ctx.pick(c, ["name"], 30), price, change: ctx.num(c.change_24h ?? c.change), history: ctx.arr(c.history ?? c.sparkline, 200).map((x) => ctx.num(x)).filter((x) => x !== null) };
    }).filter(Boolean);
    if (coins.length) return { coins, currency };
    const out = [];
    for (const line of ctx.lines(d.content, 10, 2000)) {
      const m = line.match(LINE);
      if (!m) continue;
      const price = amount(m[3]);
      if (price === null) continue;
      const sym = Object.keys(SYMBOL).find((k) => m[3].includes(k));
      if (!currency && sym) currency = SYMBOL[sym];
      out.push({ symbol: m[1].toUpperCase(), name: m[2] ? m[2].trim() : "", price, change: m[4] ? Number(m[4].replace("−", "-").replace(",", ".")) : null, history: [] });
    }
    return { coins: out, currency };
  }

  NuxivaDesk.register("crypto_ticker", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const { coins, currency } = parse(data, ctx);
      if (!coins.length) {
        el.innerHTML = `${ctx.head({ icon: "trend", label: ctx.t("label") })}${ctx.metrics(data.content)}`;
        return;
      }
      const price = (v) => ctx.fmt(v, currency ? { style: "currency", currency, currencyDisplay: "narrowSymbol", maximumFractionDigits: v >= 1000 ? 0 : v >= 1 ? 2 : 6 } : { maximumFractionDigits: v >= 1000 ? 0 : v >= 1 ? 2 : 6 });
      const at = ctx.stamp(data.updated_at ?? data.at);
      const rows = coins.map((c, i) => {
        const up = c.change === null ? null : c.change >= 0;
        const change = c.change === null ? "" : `<span class="ct-chg ${up ? "up" : "down"}">${up ? "▲" : "▼"} ${ctx.esc(ctx.fmt(Math.abs(c.change), { maximumFractionDigits: 2 }))}%</span>`;
        return `<li class="ct-row${i === 0 ? " lead" : ""}">
          <span class="ct-sym"><b>${ctx.esc(c.symbol)}</b>${c.name ? `<small>${ctx.esc(c.name)}</small>` : ""}</span>
          ${spark(c.history, up !== false)}
          <span class="ct-px"><b>${ctx.esc(price(c.price))}</b>${change}</span>
        </li>`;
      }).join("");
      const avg = coins.filter((c) => c.change !== null);
      const mood = avg.length ? avg.reduce((a, c) => a + c.change, 0) / avg.length : null;
      el.innerHTML = `${ctx.head({ icon: "trend", label: ctx.t("label"), chip: mood === null ? "" : ctx.t(mood >= 0 ? "market_up" : "market_down"), state: mood === null ? "" : mood >= 0 ? "ok" : "bad" })}
        <ul class="ct-list">${rows}</ul>
        ${at ? `<div class="ct-meta">${ctx.esc(ctx.t("updated", { when: ctx.ago(at) }))}</div>` : ""}`;
    },
  });
})();
