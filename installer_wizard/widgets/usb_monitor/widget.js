(() => {
  const LSUSB = /^Bus\s+(\d{3})\s+Device\s+(\d{3}):\s+ID\s+([0-9a-f]{4}):([0-9a-f]{4})\s*(.*)$/i;
  const KIND = [[/keyboard|tastier|teclado|clavier|hid.*kbd/i, "keyboard", "key"], [/mouse|trackpad|pointer/i, "mouse", "pen"], [/camera|webcam|video|uvc/i, "camera", "camera"], [/audio|headset|micro|speaker|dac|cuffie/i, "audio", "music"], [/phone|android|iphone|mtp|ptp/i, "phone", "phone"], [/serial|uart|ftdi|ch34|cp210|arduino|esp32/i, "serial", "port"], [/ethernet|network|wlan|wifi|rtl81|lan/i, "network", "network"], [/bluetooth|\bbt\b/i, "bluetooth", "bt"], [/hub/i, "hub", "usb"], [/storage|disk|flash|sandisk|kingston|ssd|hdd|mass|ultra|cruzer|samsung t\d|toshiba|seagate|wd /i, "storage", "server"]];
  const HUB_ONLY = /root hub/i;

  const one = (o, ctx) => {
    const text = [o.class, o.type, o.kind, o.vendor, o.product, o.name].map((v) => ctx.str(v, 80)).join(" ");
    const k = KIND.find(([re]) => re.test(text));
    const vid = ctx.str(o.vid ?? o.vendor_id, 4), pid = ctx.str(o.pid ?? o.product_id, 4);
    const used = ctx.num(o.used_percent ?? o.percent);
    return { kind: k ? k[1] : "", icon: k ? k[2] : "usb", vendor: ctx.str(o.vendor, 60), product: ctx.pick(o, ["product", "name", "model"], 80), size: ctx.str(o.size, 20),
      mount: ctx.str(o.mount ?? o.mountpoint, 120), serial: ctx.str(o.serial, 64), fs: ctx.str(o.fs ?? o.filesystem, 16), speed: ctx.str(o.speed, 20),
      id: /^[0-9a-f]{4}$/i.test(vid) && /^[0-9a-f]{4}$/i.test(pid) ? `${vid}:${pid}`.toLowerCase() : "", used: used === null ? null : ctx.pct(used), free: ctx.str(o.free, 20) };
  };

  const parse = (d, ctx) => {
    if (Array.isArray(d.devices)) return ctx.arr(d.devices, 16).filter((x) => x && typeof x === "object").map((x) => one(x, ctx));
    const out = [];
    for (const l of ctx.lines(d.content, 40, 6000)) {
      const m = l.match(LSUSB);
      if (m && !HUB_ONLY.test(m[5])) out.push(one({ vid: m[3], pid: m[4], product: m[5], vendor: m[5].split(/\s+/).slice(0, 2).join(" ") }, ctx));
    }
    if (out.length) return out;
    return d.vendor || d.product || d.size || d.mount ? [one(d, ctx)] : [];
  };

  const mask = (s) => s.length > 6 ? `${s.slice(0, 3)}${"•".repeat(Math.min(8, s.length - 6))}${s.slice(-3)}` : s;

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const devs = parse(d, ctx);
      const ui = el._usb || (el._usb = { reveal: false });
      const hid = devs.filter((x) => x.kind === "keyboard").length;
      const head = ctx.head({ icon: "usb", label: ctx.t("label"), chip: devs.length > 1 ? ctx.count("devices", devs.length) : devs.length ? ctx.t("chip") : "", live: devs.length > 0, state: hid ? "warn" : "" });
      if (!devs.length) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const main = devs[0];
      const kv = (k, v, cls = "") => v ? `<dt>${ctx.esc(ctx.t(k))}</dt><dd class="${cls}">${v}</dd>` : "";
      el.innerHTML = `${head}
        ${hid ? `<div class="wk-alert-hint ub-alert">${ctx.icon("shield")}<span>${ctx.esc(ctx.t("hid_warning"))}</span></div>` : ""}
        <div class="ub-hero"><span class="ub-ic${ui.seen ? "" : " in"}">${ctx.icon(main.icon)}</span>
          <span class="ub-main"><b>${ctx.esc(main.product || main.vendor || ctx.t("unknown"))}</b><small>${ctx.esc([main.vendor !== main.product ? main.vendor : "", main.kind ? ctx.t(`k_${main.kind}`) : ""].filter(Boolean).join(" · "))}</small></span>
          ${main.size ? `<span class="wk-num sm ub-size">${ctx.esc(main.size)}</span>` : ""}</div>
        ${main.used !== null ? `<div class="ub-use"><span>${ctx.esc(ctx.t("used", { n: Math.round(main.used) }))}${main.free ? ` · ${ctx.esc(ctx.t("free", { v: main.free }))}` : ""}</span>${ctx.bar(main.used, main.used >= 90 ? "bad" : main.used >= 75 ? "warn" : "")}</div>` : ""}
        <dl class="wk-kv ub-kv">${kv("mounted", main.mount ? ctx.esc(main.mount) : "", "mono")}${kv("filesystem", ctx.esc(main.fs), "mono")}${kv("speed", ctx.esc(main.speed))}${kv("usb_id", ctx.esc(main.id), "mono wk-faint")}
          ${main.serial ? `<dt>${ctx.esc(ctx.t("serial"))}</dt><dd class="mono wk-faint"><button type="button" class="ub-reveal" aria-pressed="${ui.reveal}" title="${ctx.esc(ctx.t(ui.reveal ? "hide" : "show"))}">${ctx.esc(ui.reveal ? main.serial : mask(main.serial))}${ctx.icon(ui.reveal ? "eye" : "lock")}</button></dd>` : ""}</dl>
        ${devs.length > 1 ? `<ul class="ub-list">${devs.slice(1, 8).map((x) => `<li>${ctx.icon(x.icon)}<span>${ctx.esc(x.product || x.vendor || ctx.t("unknown"))}</span><small class="mono">${ctx.esc(x.size || x.id)}</small></li>`).join("")}</ul>` : ""}`;
      ui.seen = true;
      el.onclick = (e) => { if (e.target.closest(".ub-reveal")) { ui.reveal = !ui.reveal; impl.render(el, raw, ctx); } };
    },
    destroy(el) { el.onclick = null; },
  };
  NuxivaDesk.register("usb_monitor", impl);
})();
