(() => {
  const IPV4 = /^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$/;
  const MAC = /^[0-9a-f]{2}([:-])(?:[0-9a-f]{2}\1){4}[0-9a-f]{2}$/i;
  const KIND = [
    [/iphone|android|pixel|galaxy|xiaomi|redmi|oneplus|huawei|oppo|phone|mobile/i, "phone", "k_phone"],
    [/printer|epson|canon|brother|hp ?inc|laserjet|stampante/i, "printer", "k_printer"],
    [/cam|hikvision|dahua|reolink|ezviz|ring|arlo|axis/i, "camera", "k_camera"],
    [/tv|chromecast|roku|fire ?stick|sonos|lg ?elec|bravia|apple ?tv|shield/i, "video", "k_media"],
    [/raspberry|server|nas|synology|qnap|proxmox|ubuntu|debian|truenas/i, "server", "k_server"],
    [/router|gateway|fritz|tp-?link|ubiquiti|unifi|mikrotik|netgear|asus ?rt|zyxel|switch|access ?point/i, "network", "k_network"],
    [/espressif|esp32|esp8266|tuya|shelly|sonoff|tasmota|zigbee|hue|nest|tado|meross|iot/i, "chip", "k_iot"],
    [/macbook|imac|laptop|desktop|pc|thinkpad|dell|lenovo|intel|surface|windows/i, "cpu", "k_computer"],
  ];

  function kindOf(text) { return KIND.find(([re]) => re.test(text)) || [null, "lan", "k_unknown"]; }
  const randomMac = (mac) => MAC.test(mac) && (parseInt(mac.slice(0, 2), 16) & 2) === 2;

  NuxivaDesk.register("lan_device", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const ip = ctx.str(data.ip, 45), mac = ctx.str(data.mac, 17).toLowerCase();
      const host = ctx.pick(data, ["hostname", "name"], 60), vendor = ctx.str(data.vendor, 60);
      const ipOk = IPV4.test(ip) || (ip.includes(":") && /^[0-9a-f:]{2,45}$/i.test(ip));
      const macOk = MAC.test(mac);
      const [, ic, kk] = kindOf(`${host} ${vendor} ${ctx.str(data.type, 30)}`);
      const seen = ctx.stamp(data.first_seen ?? data.seen ?? data.at);
      const known = data.known === true || data.trusted === true;
      const ports = ctx.arr(data.ports, 12).map((p) => ctx.num(typeof p === "object" && p ? p.port : p)).filter((p) => Number.isInteger(p) && p > 0 && p < 65536);
      if (!ipOk && !macOk && !host) { el.innerHTML = `${ctx.head({ icon: "lan", label: ctx.t("label") })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const priv = randomMac(mac);
      el.innerHTML = `${ctx.head({ icon: "lan", label: ctx.t("label"), chip: ctx.t(known ? "chip_known" : "chip"), live: !known, state: known ? "" : "warn" })}
        <div class="ld-hero"><span class="ld-ic${known ? "" : " new"}">${ctx.icon(ic)}</span>
          <span class="ld-main"><span class="wk-title">${ctx.esc(host || vendor || ip || mac)}</span><span class="wk-sub">${ctx.esc([ctx.t(kk), seen ? ctx.ago(seen) : ""].filter(Boolean).join(" · "))}</span></span></div>
        <dl class="wk-kv ld-kv">
          <dt>IP</dt><dd class="mono">${ipOk ? ctx.esc(ip) : "—"}</dd>
          <dt>MAC</dt><dd class="mono wk-faint">${macOk ? ctx.esc(mac) : "—"}${priv ? ` <span class="ld-tag" title="${ctx.esc(ctx.t("random_mac_hint"))}">${ctx.esc(ctx.t("random_mac"))}</span>` : ""}</dd>
          <dt>${ctx.esc(ctx.t("vendor"))}</dt><dd>${ctx.esc(vendor || (priv ? ctx.t("vendor_hidden") : "—"))}</dd>
          ${ports.length ? `<dt>${ctx.esc(ctx.t("ports"))}</dt><dd class="mono ld-ports">${ports.map((p) => `<span>${p}</span>`).join("")}</dd>` : ""}
        </dl>
        ${known ? "" : `<div class="ld-hint">${ctx.icon("shield")}<span>${ctx.esc(ctx.t("hint"))}</span></div>`}`;
    },
  });
})();
