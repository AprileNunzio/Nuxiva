(() => {
  const LANES = ["todo", "doing", "done"];
  const PRIO = { high: "high", alta: "high", alto: "high", urgent: "high", urgente: "high", critical: "high", p1: "high", medium: "mid", media: "mid", medio: "mid", normal: "mid", p2: "mid", low: "low", bassa: "low", basso: "low", p3: "low" };
  const MAX = 8;

  function card(v, ctx) {
    if (typeof v === "string" || typeof v === "number") { const title = ctx.str(v, 160); return title ? { title } : null; }
    if (!v || typeof v !== "object") return null;
    const title = ctx.pick(v, ["title", "name", "text", "task"], 160);
    if (!title) return null;
    const progress = ctx.num(v.progress);
    return { title, who: ctx.pick(v, ["assignee", "who", "owner", "agent"], 30), prio: PRIO[ctx.str(v.priority, 12).toLowerCase()] || "",
      progress: progress === null ? null : Math.max(0, Math.min(100, progress <= 1 && progress > 0 && !Number.isInteger(progress) ? progress * 100 : progress)),
      due: ctx.stamp(v.due), tags: ctx.arr(v.tags, 3).map((t) => ctx.str(t, 16)).filter(Boolean) };
  }

  function fromText(text) {
    const lanes = { todo: [], doing: [], done: [] };
    let lane = "todo";
    for (const raw of text.split("\n")) {
      const line = raw.trim();
      if (!line) continue;
      const h = line.match(/^#*\s*(da fare|todo|to do|pending|in corso|doing|in progress|wip|fatto|fatti|done|completat[ie]|completed)\s*:?\s*$/i);
      if (h) { const k = h[1].toLowerCase(); lane = /fatt|done|complet/.test(k) ? "done" : /corso|doing|progress|wip/.test(k) ? "doing" : "todo"; continue; }
      const box = line.match(/^[-*•]\s*\[( |x|X|~|>)\]\s*(.+)$/);
      if (box) { lanes[box[1] === " " ? "todo" : /x/i.test(box[1]) ? "done" : "doing"].push(box[2]); continue; }
      lanes[lane].push(line.replace(/^[-*•\d.)\s]+/, ""));
    }
    return lanes;
  }

  const initials = (s) => s.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => Array.from(w)[0]).join("").toUpperCase();

  NuxivaDesk.register("kanban_board", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const has = LANES.some((k) => Array.isArray(data[k]));
      const raw = has ? data : typeof data.content === "string" ? fromText(ctx.plain(data.content, 8000)) : {};
      const lanes = Object.fromEntries(LANES.map((k) => [k, ctx.arr(raw[k], 60).map((v) => card(v, ctx)).filter(Boolean)]));
      const total = LANES.reduce((s, k) => s + lanes[k].length, 0);
      const done = lanes.done.length;
      const title = ctx.str(data.title, 80);
      const head = ctx.head({ icon: "board", label: ctx.t("label"), title, chip: lanes.doing.length ? ctx.count("doing_chip", lanes.doing.length) : total && done === total ? ctx.t("all_done") : "", live: lanes.doing.length > 0 });
      if (!total) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      const now = ctx.now();
      const shown = LANES.filter((k) => k !== "done" || done);
      const col = (k) => {
        const list = lanes[k];
        return `<div class="kb-col ${k}"><h5><span>${ctx.esc(ctx.t(k))}</span><b>${list.length}</b></h5>
          <ul class="kb-cards">${list.slice(0, MAX).map((c, i) => {
            const late = c.due && c.due < now && k !== "done";
            const meta = [
              c.due ? `<span class="kb-due${late ? " late" : ""}">${ctx.icon("calendar")}${ctx.esc(ctx.when(c.due, { day: "numeric", month: "short" }))}</span>` : "",
              ...(c.tags || []).map((t) => `<span class="kb-tag">${ctx.esc(t)}</span>`),
              c.who ? `<span class="kb-who" title="${ctx.esc(c.who)}">${ctx.esc(initials(c.who))}</span>` : "",
            ].join("");
            return `<li class="kb-card${c.prio ? ` p-${c.prio}` : ""}" style="--i:${i}"><span class="kb-title">${k === "done" ? ctx.icon("check") : ""}${ctx.esc(c.title)}</span>
              ${c.progress !== null && c.progress !== undefined && k !== "done" ? ctx.bar(c.progress) : ""}${meta ? `<span class="kb-meta">${meta}</span>` : ""}</li>`;
          }).join("")}</ul>${list.length > MAX ? `<div class="wk-faint kb-more">${ctx.esc(ctx.t("more", { n: list.length - MAX }))}</div>` : ""}</div>`;
      };
      el.innerHTML = `${head}
        <div class="kb-sum"><span class="kb-prog"><i style="width:${(done / total) * 100}%"></i></span><span class="mono">${ctx.esc(`${done}/${total}`)}</span></div>
        <div class="kb-board" style="--cols:${shown.length}">${shown.map(col).join("")}</div>`;
    },
  });
})();
