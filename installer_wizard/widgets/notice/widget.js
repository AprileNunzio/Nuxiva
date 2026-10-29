(() => {
  const EMOJI = [
    [/🎂|🎁|🎉|🎈/u, "gift"], [/⚠|❗|‼/u, "alert"], [/🚨|🔥/u, "fire"], [/📱|☎|📞/u, "phone"], [/✉|📧|📨/u, "mail"],
    [/💬/u, "chat"], [/📅|🗓/u, "calendar"], [/⏰|⏱|🕐/u, "clock"], [/💡/u, "light"], [/🔒|🔐|🔑/u, "lock"], [/🛡/u, "shield"],
    [/📶|🛜|📡/u, "wifi"], [/🖥|💻|🖧/u, "server"], [/🚗|🚙/u, "car"], [/⚡|🔋/u, "bolt"], [/✅|✔/u, "check"], [/ℹ/u, "info"],
    [/👤|🧑|👩|👨/u, "user"], [/🏠|🏡/u, "home"], [/⭐|🌟/u, "star"], [/🎵|🎶|🎧|🎤/u, "music"], [/🏃|👀|👁/u, "eye"],
    [/🧪|🔬|🧬/u, "sparkle"], [/🗒|📝|📄/u, "doc"], [/🤖/u, "brain"], [/📷|📸/u, "camera"], [/🖨/u, "printer"], [/⬇|📥/u, "download"],
  ];
  const LEVEL = { warn: "warn", warning: "warn", error: "bad", critical: "bad", ok: "ok", success: "ok" };
  const pick = (v) => {
    const s = typeof v === "string" ? v.slice(0, 32) : "";
    if (window.NuxivaIcons && window.NuxivaIcons.names.includes(s)) return s;
    const hit = EMOJI.find(([re]) => re.test(s));
    return hit ? hit[1] : "bell";
  };

  NuxivaDesk.register("notice", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const level = LEVEL[ctx.str(data.level, 12).toLowerCase()] || "";
      const title = ctx.str(data.title, 120), text = ctx.str(data.text, 400);
      const at = ctx.stamp(data.at ?? data.time);
      const label = ctx.t(level === "warn" ? "warning" : level === "bad" ? "error" : level === "ok" ? "done" : "notice");
      el.innerHTML = `${ctx.head({ label, chip: at ? ctx.ago(at) : "", state: level })}
        <div class="no-row${level ? ` ${level}` : ""}"><span class="no-ic">${ctx.icon(pick(data.icon))}</span><div class="no-txt">
          ${title ? `<div class="wk-title">${ctx.esc(title)}</div>` : ""}
          ${text ? `<div class="wk-sub no-text">${ctx.esc(text)}</div>` : ""}
          ${!title && !text ? `<div class="wk-sub">${ctx.esc(ctx.tc("waiting"))}</div>` : ""}</div></div>`;
      const card = el.closest(".widget") || el.parentNode;
      if (card && card.classList) {
        card.classList.toggle("no-warn", level === "warn" || level === "bad");
        card.classList.toggle("tone-amber", level === "warn");
        card.classList.toggle("tone-red", level === "bad");
      }
    },
  });
})();
