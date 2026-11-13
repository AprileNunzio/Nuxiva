(function (global) {
  "use strict";

  const LANGS = Object.freeze(["it", "en", "fr", "es"]);
  const KINDS = Object.freeze(["features", "fixes"]);
  const NOTE_MAX = 320;
  const VERSION = /^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}(?:-[0-9A-Za-z.]{1,24})?$/;
  const DATE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
  const SVG = "http://www.w3.org/2000/svg";
  const ICONS = Object.freeze({
    features: ["M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z", "M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"],
    fixes: ["M14.7 6.3a4 4 0 0 0-5.4 5.4L3.5 17.5a1.8 1.8 0 0 0 2.5 2.5l5.8-5.8a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"],
    calm: ["M12 3l7 3v6c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z", "M8.8 12.2l2.2 2.2 4.4-4.6"],
  });
  const reduced = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const lanes = [];
  let host = null;
  let model = null;
  let key = "";
  let frame = 0;

  function el(tag, cls, parent) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function icon(name, parent) {
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.classList.add("upd-icon");
    ICONS[name].forEach((d) => {
      const path = document.createElementNS(SVG, "path");
      path.setAttribute("d", d);
      svg.appendChild(path);
    });
    parent.appendChild(svg);
    return svg;
  }

  function lang() {
    const code = (document.documentElement.lang || "").slice(0, 2);
    return LANGS.includes(code) ? code : "en";
  }

  function pick(item, code) {
    if (!item || typeof item !== "object") return "";
    const value = [code, "en", "it"].map((k) => item[k]).find((v) => typeof v === "string" && v.trim());
    return value ? value.trim().slice(0, NOTE_MAX) : "";
  }

  function normalize(notes, ready) {
    const code = lang();
    const valid = notes && typeof notes === "object" ? notes : null;
    const groups = KINDS.map((kind) => {
      const items = valid && Array.isArray(valid[kind]) ? valid[kind].map((i) => pick(i, code)).filter(Boolean) : [];
      const raw = valid ? valid[`total_${kind}`] : 0;
      const total = Number.isInteger(raw) ? Math.max(raw, items.length) : items.length;
      return { kind, items, total };
    }).filter((g) => g.items.length);
    const version = valid && typeof valid.version === "string" && VERSION.test(valid.version) ? valid.version : "";
    const date = valid && typeof valid.date === "string" && DATE.test(valid.date) ? valid.date : "";
    return { code, groups, version, date, state: groups.length ? "notes" : ready ? "calm" : "wait" };
  }

  function longDate(iso, code) {
    const [y, m, d] = iso.split("-").map(Number);
    const when = new Date(Date.UTC(y, m - 1, d, 12));
    if (Number.isNaN(when.getTime())) return "";
    return new Intl.DateTimeFormat(code, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(when);
  }

  function hero() {
    const title = host.querySelector(".upd-hero-title");
    const sub = host.querySelector(".upd-hero-sub");
    if (model.version) PageText.bind(title, "upd_hero_version", { version: model.version });
    else if (model.state === "notes" && model.date) PageText.bind(title, "upd_hero_date", { date: longDate(model.date, model.code) });
    else PageText.bind(title, "upd_title");
    if (model.state === "notes") PageText.bind(sub, "upd_notes_title");
    else if (model.state === "calm") PageText.bind(sub, "upd_calm_sub");
    else PageText.bind(sub, "upd_waiting");
  }

  function head(lane, group, more) {
    const top = el("div", "upd-lane-head", lane.page);
    top.dataset.kind = group.kind;
    icon(group.kind, top);
    PageText.bind(el("span", "upd-lane-name", top), `upd_notes_${group.kind}`);
    PageText.plain(el("span", "upd-lane-count", top), String(group.total));
    const tail = el("span", "upd-lane-more", top);
    if (more) PageText.bind(tail, "upd_notes_more", { count: more });
  }

  function item(list, text, index) {
    const row = el("li", "upd-item", list);
    row.style.setProperty("--i", String(index));
    PageText.plain(row, text);
    return row;
  }

  function paginate(lane) {
    lane.pages = [];
    lane.page.replaceChildren();
    lane.root.classList.add("measuring");
    lane.groups.forEach((group) => {
      let chunk = [];
      const start = () => {
        lane.page.replaceChildren();
        head(lane, group);
        return el("ol", "upd-list", lane.page);
      };
      let list = start();
      const limit = lane.page.clientHeight;
      group.items.forEach((text) => {
        const row = item(list, text, chunk.length);
        if (chunk.length && lane.page.scrollHeight > limit) {
          row.remove();
          lane.pages.push({ group, items: chunk });
          chunk = [];
          list = start();
          item(list, text, 0);
        }
        chunk.push(text);
      });
      if (chunk.length) lane.pages.push({ group, items: chunk });
      const shown = group.items.length;
      if (group.total > shown) lane.pages[lane.pages.length - 1].more = group.total - shown;
    });
    lane.page.replaceChildren();
    lane.root.classList.remove("measuring");
  }

  function show(lane, index, animate) {
    const page = lane.pages[index];
    if (!page) return;
    lane.index = index;
    lane.page.replaceChildren();
    head(lane, page.group, page.more);
    const list = el("ol", "upd-list", lane.page);
    page.items.forEach((text, i) => item(list, text, i));
    lane.page.classList.remove("enter");
    if (animate && !reduced.matches) {
      void lane.page.offsetWidth;
      lane.page.classList.add("enter");
    }
    lane.dots.replaceChildren();
    lane.dots.classList.toggle("idle", lane.pages.length < 2);
    lane.pages.forEach((_, i) => el("span", i === index ? "upd-dot on" : "upd-dot", lane.dots));
    schedule(lane);
  }

  function dwell(page) {
    const chars = page.items.reduce((sum, text) => sum + text.length, 0);
    return Math.min(18000, Math.max(7000, 3000 + chars * 45));
  }

  function schedule(lane) {
    clearTimeout(lane.timer);
    if (lane.pages.length < 2) return;
    lane.timer = setTimeout(() => {
      lane.page.classList.add("leave");
      setTimeout(() => {
        lane.page.classList.remove("leave");
        show(lane, (lane.index + 1) % lane.pages.length, true);
      }, reduced.matches ? 0 : 420);
    }, dwell(lane.pages[lane.index]));
  }

  function stop() {
    lanes.forEach((lane) => clearTimeout(lane.timer));
  }

  function wide() {
    return host.clientWidth >= 760 && host.clientWidth > host.clientHeight * 0.9;
  }

  function layout() {
    frame = 0;
    if (!host || !model) return;
    stop();
    const board = host.querySelector(".upd-board");
    board.dataset.state = model.state;
    hero();
    const split = model.groups.length === 2 && wide();
    const plan = model.state !== "notes" ? [] : split ? model.groups.map((g) => [g]) : [model.groups];
    board.classList.toggle("split", split);
    lanes.forEach((lane, i) => {
      lane.groups = plan[i] || [];
      lane.root.classList.toggle("hidden", !lane.groups.length);
    });
    lanes.forEach((lane) => {
      if (!lane.groups.length) return;
      paginate(lane);
      show(lane, Math.min(lane.index || 0, lane.pages.length - 1), true);
    });
  }

  function relayout() {
    if (!frame) frame = requestAnimationFrame(layout);
  }

  function lane(board) {
    const root = el("section", "upd-lane hidden", board);
    const page = el("div", "upd-page", root);
    const dots = el("div", "upd-dots idle", root);
    dots.setAttribute("aria-hidden", "true");
    return { root, page, dots, pages: [], index: 0, groups: [], timer: 0 };
  }

  function mount(parent) {
    host = parent;
    const heroBox = el("div", "upd-hero", parent);
    el("p", "upd-hero-sub", heroBox);
    el("h2", "upd-hero-title", heroBox);
    const board = el("div", "upd-board", parent);
    lanes.push(lane(board), lane(board));
    const calm = el("div", "upd-calm", board);
    icon("calm", calm);
    PageText.bind(el("p", "upd-calm-title", calm), "upd_calm_title");
    PageText.bind(el("p", "upd-calm-text", calm), "upd_calm_text");
    if (global.ResizeObserver) new ResizeObserver(relayout).observe(parent);
    else global.addEventListener("resize", relayout);
    PageText.onChange(() => { key = ""; });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(relayout);
  }

  function update(notes, ready) {
    const next = normalize(notes, ready);
    const nextKey = JSON.stringify(next);
    if (nextKey === key) return;
    key = nextKey;
    model = next;
    lanes.forEach((l) => { l.index = 0; });
    relayout();
  }

  global.NuxivaUpdateNotes = Object.freeze({ mount, update, stop, relayout });
})(window);
