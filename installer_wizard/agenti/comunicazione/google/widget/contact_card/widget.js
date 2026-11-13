(() => {
  const PHOTO = /^(https:\/\/[^\s"'<>\\]+|\/(?!\/)[^\s"'<>\\]*)$/i;
  const EMAIL = /^[^\s@<>"']{1,64}@[^\s@<>"']{1,190}\.[a-z]{2,24}$/i;
  const hue = (s) => [...s].reduce((h, c) => (h * 31 + c.codePointAt(0)) >>> 0, 7) % 360;
  const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => [...w][0].toUpperCase()).join("");
  const phoneText = (p) => {
    const s = p.replace(/[^\d+]/g, "");
    if (/[\s.\-/()]/.test(p.trim()) || !/^\+\d{8,15}$/.test(s)) return p.trim();
    const m = s.match(/^(\+\d{2})(\d+)$/);
    const body = m ? m[2] : s;
    const grouped = body.replace(/(\d{3})(?=\d{3,})/g, "$1 ").trim();
    return m ? `${m[1]} ${grouped}` : grouped;
  };

  function list(raw, single, ctx, max) {
    const items = Array.isArray(raw) ? raw : single ? [single] : [];
    return items.slice(0, max).map((x) => (x && typeof x === "object" ? { value: ctx.pick(x, ["value", "number", "email", "address"], 200), label: ctx.pick(x, ["label", "type", "kind"], 20) } : { value: ctx.str(x, 200), label: "" })).filter((x) => x.value);
  }

  NuxivaDesk.register("contact_card", {
    render(el, d, ctx) {
      clearTimeout(el._ccT);
      const data = d && typeof d === "object" ? d : {};
      const name = ctx.str(data.name ?? data.full_name, 80);
      const company = [ctx.str(data.role ?? data.title, 60), ctx.str(data.company ?? data.org, 60)].filter(Boolean).join(" · ");
      const phones = list(data.phones, data.phone, ctx, 4);
      const emails = list(data.emails, data.email, ctx, 3).filter((e) => EMAIL.test(e.value));
      const address = ctx.str(data.address, 200);
      const note = ctx.str(data.note, 240);
      const photo = typeof data.photo === "string" && PHOTO.test(data.photo.trim()) ? data.photo.trim() : "";
      const bday = ctx.stamp(data.birthday);
      let bdayText = "";
      if (bday) {
        const b = new Date(bday * 1000), now = new Date();
        const next = new Date(now.getFullYear(), b.getMonth(), b.getDate());
        if (next < new Date(now.getFullYear(), now.getMonth(), now.getDate())) next.setFullYear(now.getFullYear() + 1);
        const days = Math.round((next - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 864e5);
        bdayText = `${ctx.when(next.getTime() / 1000, { day: "numeric", month: "long" })}${days === 0 ? ` · ${ctx.t("today")}` : days <= 30 ? ` · ${ctx.t("in_days", { n: days })}` : ""}`;
      }
      const h = hue(name || "?");
      const row = (icon, label, value, copyable, cls = "") => `<li class="cc-row${cls}">${ctx.icon(icon)}<span><small>${ctx.esc(label)}</small><b>${ctx.esc(value)}</b></span>${copyable ? `<button type="button" class="wk-btn icon cc-copy" data-copy="${ctx.esc(copyable)}" title="${ctx.esc(ctx.t("copy"))}" aria-label="${ctx.esc(ctx.t("copy"))}">${ctx.icon("copy")}</button>` : ""}</li>`;
      const rows = [
        ...phones.map((p) => row("phone", p.label || ctx.t("phone"), phoneText(p.value), p.value, " cc-main")),
        ...emails.map((e) => row("mail", e.label || ctx.t("email"), e.value, e.value)),
        address ? row("pin", ctx.t("address"), address, "") : "",
        bdayText ? row("gift", ctx.t("birthday"), bdayText, "") : "",
      ].join("");
      el.innerHTML = `${ctx.head({ icon: "contact", label: ctx.t("label") })}
        <div class="wk-hero cc-hero">
          <span class="cc-ini" style="--h:${h}">${photo ? `<img alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" src="${ctx.esc(photo)}">` : ""}<span>${name ? ctx.esc(initials(name)) : ctx.icon("user")}</span></span>
          <span class="cc-id"><div class="wk-title">${ctx.esc(name || ctx.t("unknown"))}</div>${company ? `<div class="wk-sub">${ctx.esc(company)}</div>` : ""}</span>
        </div>
        ${rows ? `<ul class="cc-list">${rows}</ul>` : `<div class="wk-empty">${ctx.esc(ctx.t("no_number"))}</div>`}
        ${note ? `<p class="wk-sub cc-note">${ctx.esc(note)}</p>` : ""}`;
      const img = el.querySelector(".cc-ini img");
      if (img) {
        img.addEventListener("load", () => img.parentElement.classList.add("has-photo"), { once: true });
        img.addEventListener("error", () => img.remove(), { once: true });
      }
      el.querySelectorAll(".cc-copy").forEach((b) => b.addEventListener("click", async (e) => {
        e.stopPropagation();
        const ok = await ctx.copy(b.dataset.copy);
        b.classList.add(ok ? "ok" : "ko");
        clearTimeout(el._ccT);
        el._ccT = setTimeout(() => b.classList.remove("ok", "ko"), 1400);
      }));
    },
    destroy(el) { clearTimeout(el._ccT); },
  });
})();
