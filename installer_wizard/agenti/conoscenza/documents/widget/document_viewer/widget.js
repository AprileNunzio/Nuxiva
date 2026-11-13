(() => {
  const ext = (name) => (String(name).split(".").pop() || "").toLowerCase();
  const base = (path) => String(path).split(/[\\/]/).pop();
  const ICON = { docx: "doc", doc: "doc", odt: "doc", rtf: "doc", txt: "text", md: "text", xlsx: "chart", xls: "chart", ods: "chart", csv: "chart", pptx: "image", ppt: "image", odp: "image", pdf: "file", png: "image", jpg: "image", jpeg: "image", zip: "download" };
  const KIND = { docx: "word", doc: "word", odt: "word", xlsx: "sheet", xls: "sheet", ods: "sheet", csv: "sheet", pptx: "slides", ppt: "slides", odp: "slides", pdf: "pdf" };
  const ID = /^[\w-]{1,64}$/;

  function target(raw) {
    const s = typeof raw === "string" ? raw.trim() : "";
    if (!s || s.length > 2048) return null;
    let u;
    try { u = new URL(s, window.location.origin); } catch (_) { return null; }
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    const same = u.origin === window.location.origin;
    if (same && !s.startsWith("/")) return null;
    if (same && /\.\./.test(u.pathname)) return null;
    const pdf = /\.pdf$/i.test(u.pathname);
    return { href: same ? u.pathname + u.search + u.hash : u.href, same, pdf, host: same ? "" : u.hostname };
  }

  function frame(t, ctx, title) {
    const sandbox = t.same && t.pdf ? "" : ` sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox${t.same ? "" : " allow-same-origin"}"`;
    return `<div class="wk-media dv-prev"><div class="dv-loading">${ctx.esc(ctx.t("loading"))}</div><iframe class="dv-frame" src="${ctx.esc(t.href)}" title="${ctx.esc(title || ctx.t("viewer"))}" referrerpolicy="no-referrer" loading="lazy"${sandbox}></iframe></div>`;
  }

  function wire(el) {
    const f = el.querySelector(".dv-frame");
    if (f) f.addEventListener("load", () => f.parentElement.classList.add("ready"), { once: true });
  }

  function office(el, d, ctx) {
    const rawId = String(d.id ?? "");
    const id = ID.test(rawId) ? encodeURIComponent(rawId) : "";
    const names = ctx.arr(d.files, 20).map((f) => ctx.str(f, 260)).filter(Boolean);
    const files = names.map((f, i) => {
      const e = ext(f);
      const inner = `${ctx.icon(ICON[e] || "file")}<span class="dv-name"><b>${ctx.esc(base(f))}</b><small>${ctx.esc(ctx.t(`kind_${KIND[e] || "file"}`))}</small></span><span class="wk-val">${ctx.esc(e)}</span>`;
      return id ? `<li><a class="dv-file" href="/api/documents/${id}/file/${i}" target="_blank" rel="noopener noreferrer" download>${inner}</a></li>` : `<li><span class="dv-file">${inner}</span></li>`;
    }).join("");
    const errs = ctx.arr(d.errors, 6).map((e) => ctx.str(e, 160)).filter(Boolean);
    const errors = errs.length ? `<div class="dv-err">${ctx.icon("alert")}<span><b>${ctx.esc(ctx.t("failed"))}</b> ${errs.map(ctx.esc).join("; ")}</span></div>` : "";
    const preview = d.preview === true && id ? frame({ href: `/api/documents/${id}/preview.pdf#view=FitH&toolbar=0`, same: true, pdf: true }, ctx, d.title) : "";
    const project = ctx.str(d.project, 160);
    el.innerHTML = `${ctx.head({ icon: "doc", label: ctx.t(d.kind === "progetto" ? "project" : "document"), title: ctx.str(d.title, 120) || ctx.t("document"), chip: names.length ? ctx.count("files", names.length) : "", state: errs.length ? "warn" : "" })}
      ${d.summary ? `<div class="wk-sub dv-sum">${ctx.esc(ctx.str(d.summary, 600))}</div>` : ""}
      <div class="dv-body${preview ? " with-preview" : ""}"><div>${files ? `<ul class="dv-files">${files}</ul>` : ""}${errors}
        <div class="wk-faint dv-where">${ctx.icon("file")}<span>${ctx.esc(ctx.t("shared_folder"))}</span> › 01 <span>${ctx.esc(ctx.t("documents"))}</span>${project ? ` › ${ctx.esc(base(project))}` : ""}</div></div>${preview}</div>`;
    wire(el);
  }

  NuxivaDesk.register("document_viewer", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      if (data.type === "office") { office(el, data, ctx); return; }
      const t = target(data.url);
      const type = ctx.str(data.type, 20) || (t && t.pdf ? "pdf" : "web");
      const title = ctx.str(data.title, 120);
      el.innerHTML = `${ctx.head({ icon: "doc", label: ctx.t("viewer"), title: title || (t && t.host) || "", chip: type })}
        ${t ? `${frame(t, ctx, title)}${t.host ? `<div class="dv-host">${ctx.icon(t.href.startsWith("https:") ? "lock" : "unlock")}<span>${ctx.esc(t.host)}</span></div>` : ""}` : `<div class="wk-empty">${ctx.esc(ctx.t("no_preview"))} (${ctx.esc(type)})</div>`}`;
      wire(el);
    },
  });
})();
