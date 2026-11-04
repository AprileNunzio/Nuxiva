(() => {
  const MAX_CHARS = 200000, MAX_LINES = 800, HUNK = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@ ?(.*)$/;

  const clean = (p) => p.replace(/^"|"$/g, "").replace(/^[ab]\//, "").replace(/\t.*$/, "").trim();

  function parse(text) {
    const files = [];
    let f = null, h = null, o = 0, n = 0;
    const open = (path = "") => { f = { path, old: "", status: "modified", add: 0, del: 0, hunks: [], binary: false }; files.push(f); h = null; return f; };
    for (const line of text.split("\n")) {
      if (line.startsWith("diff --git ")) { const m = line.match(/^diff --git (?:"?a\/(.+?)"?) (?:"?b\/(.+?)"?)$/); open(m ? m[2] : ""); if (m) f.old = m[1]; continue; }
      if (!f && (line.startsWith("--- ") || line.startsWith("@@") || /^[+-]/.test(line))) open();
      if (!f) continue;
      if (!h || !/^[ +\-\\]/.test(line) || line.startsWith("--- ") && !h.lines.length || line.startsWith("+++ ") && !h.lines.length) {
        if (line.startsWith("new file")) { f.status = "added"; continue; }
        if (line.startsWith("deleted file")) { f.status = "deleted"; continue; }
        if (line.startsWith("rename from ")) { f.status = "renamed"; f.old = line.slice(12); continue; }
        if (line.startsWith("rename to ")) { f.path = line.slice(10); continue; }
        if (line.startsWith("Binary files") || line.startsWith("GIT binary patch")) { f.binary = true; continue; }
        if (line.startsWith("--- ")) { const p = clean(line.slice(4)); if (p !== "/dev/null") f.old = p; else f.status = "added"; continue; }
        if (line.startsWith("+++ ")) { const p = clean(line.slice(4)); if (p !== "/dev/null") f.path = p; else { f.status = "deleted"; f.path = f.path || f.old; } continue; }
      }
      const m = line.match(HUNK);
      if (m) { o = +m[1]; n = +m[2]; h = { head: line.slice(0, line.indexOf("@@", 2) + 2), fn: m[3], lines: [] }; f.hunks.push(h); continue; }
      if (!h) { if (/^[+-]/.test(line)) { h = { head: "", fn: "", lines: [] }; f.hunks.push(h); o = n = 0; } else continue; }
      const t = line[0];
      if (t === "+") { f.add++; h.lines.push(["+", "", n ? n++ : "", line.slice(1)]); }
      else if (t === "-") { f.del++; h.lines.push(["-", o ? o++ : "", "", line.slice(1)]); }
      else if (t === "\\") h.lines.push(["\\", "", "", line.slice(1).trim()]);
      else h.lines.push([" ", o ? o++ : "", n ? n++ : "", line.slice(1)]);
    }
    for (const x of files) if (!x.path) x.path = x.old;
    return files.filter((x) => x.hunks.length || x.binary || x.status !== "modified" || x.path);
  }

  const blocks = (add, del) => {
    const total = add + del;
    const g = total ? Math.round((add / total) * 5) : 0;
    return `<span class="gd-blocks" aria-hidden="true">${Array.from({ length: 5 }, (_, i) => `<i class="${!total ? "" : i < g ? "a" : "d"}"></i>`).join("")}</span>`;
  };

  function stop(el) { clearTimeout(el._gdT); }

  NuxivaDesk.register("git_diff", {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const raw = (typeof data.content === "string" ? data.content : typeof d === "string" ? d : "").replace(/\r\n?/g, "\n").slice(0, MAX_CHARS);
      const files = raw.trim() ? parse(raw) : [];
      const add = files.reduce((s, f) => s + f.add, 0), del = files.reduce((s, f) => s + f.del, 0);
      const title = ctx.str(data.title, 120) || (files.length === 1 ? files[0].path : files.length ? ctx.count("files", files.length) : "");
      const head = ctx.head({ icon: "git", label: ctx.t("label"), title, chip: add || del ? `+${add} −${del}` : "" });
      if (!files.length) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      let budget = MAX_LINES;
      const body = files.map((f, i) => {
        const hunks = f.hunks.map((h) => {
          const rows = h.lines.slice(0, Math.max(0, budget));
          budget -= rows.length;
          return `${h.head ? `<tr class="gd-hunk"><td colspan="3"><span>${ctx.esc(h.head)}</span>${h.fn ? ` <em>${ctx.esc(h.fn.slice(0, 120))}</em>` : ""}</td></tr>` : ""}${rows.map(([t, a, b, s]) => `<tr class="gd-${t === "+" ? "add" : t === "-" ? "del" : t === "\\" ? "nl" : "ctx"}"><td class="gd-n">${a}</td><td class="gd-n">${b}</td><td class="gd-c"><span class="gd-sign">${t === "\\" ? "" : ctx.esc(t)}</span>${ctx.esc(s)}</td></tr>`).join("")}`;
        }).join("");
        const path = f.status === "renamed" && f.old && f.old !== f.path ? `${f.old} → ${f.path}` : f.path || "—";
        return `<section class="gd-file" data-i="${i}"><header class="gd-fhead" role="button" tabindex="0" aria-expanded="true"><span class="gd-st ${f.status}">${ctx.esc(ctx.t(`st_${f.status}`))}</span><b title="${ctx.esc(path)}">${ctx.esc(path)}</b><span class="gd-fnum mono"><i class="a">+${f.add}</i> <i class="d">−${f.del}</i></span>${blocks(f.add, f.del)}</header>
          ${f.binary ? `<div class="wk-faint gd-bin">${ctx.esc(ctx.t("binary"))}</div>` : `<table class="gd-table"><tbody>${hunks}</tbody></table>`}</section>`;
      }).join("");
      const total = files.reduce((s, f) => s + f.hunks.reduce((k, h) => k + h.lines.length, 0), 0);
      el.innerHTML = `${head}
        <div class="gd-bar"><span class="gd-sum">${blocks(add, del)}<span class="mono"><i class="a">+${ctx.esc(ctx.fmt(add))}</i> <i class="d">−${ctx.esc(ctx.fmt(del))}</i></span><span class="wk-faint">${ctx.esc(ctx.count("files", files.length))}</span></span>
          <button type="button" class="wk-btn gd-copy" aria-label="${ctx.esc(ctx.t("copy"))}">${ctx.icon("copy")}<span>${ctx.esc(ctx.t("copy"))}</span></button></div>
        <div class="gd-scroll" tabindex="0">${body}</div>
        ${total > MAX_LINES ? `<div class="wk-faint gd-more">${ctx.esc(ctx.t("truncated", { n: total - MAX_LINES }))}</div>` : ""}`;
      el.querySelectorAll(".gd-fhead").forEach((hd) => {
        const toggle = (e) => { e.stopPropagation(); const sec = hd.parentElement; const shut = sec.classList.toggle("shut"); hd.setAttribute("aria-expanded", String(!shut)); };
        hd.addEventListener("click", toggle);
        hd.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(e); } });
      });
      const btn = el.querySelector(".gd-copy");
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const ok = await ctx.copy(raw);
        btn.querySelector("span").textContent = ctx.t(ok ? "copied" : "copy_failed");
        stop(el);
        el._gdT = setTimeout(() => { if (btn.isConnected) btn.querySelector("span").textContent = ctx.t("copy"); }, 1800);
      });
    },
    destroy: stop,
  });
})();
