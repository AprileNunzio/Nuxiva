(() => {
  const NS = "http://www.w3.org/2000/svg";
  const NODE_W = 168, NODE_H = 44, GAP_X = 64, GAP_Y = 18;

  function el(name, attrs) {
    const node = document.createElementNS(NS, name);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, String(v)));
    return node;
  }

  function layers(tasks) {
    const byId = new Map(tasks.map((t) => [t.id, t]));
    const depth = new Map();
    const visit = (id, trail) => {
      if (depth.has(id)) return depth.get(id);
      if (trail.has(id)) return 0;
      trail.add(id);
      const deps = (byId.get(id).depends_on || []).filter((d) => byId.has(d));
      const value = deps.length ? Math.max(...deps.map((d) => visit(d, trail))) + 1 : 0;
      trail.delete(id);
      depth.set(id, value);
      return value;
    };
    tasks.forEach((t) => visit(t.id, new Set()));
    const columns = [];
    tasks.forEach((t) => { const d = depth.get(t.id); (columns[d] = columns[d] || []).push(t); });
    return columns;
  }

  function shorten(text, max) {
    return text.length > max ? `${text.slice(0, max - 1)}…` : text;
  }

  function render(svg, tasks, statusLabel) {
    svg.replaceChildren();
    const columns = layers(tasks);
    const tall = Math.max(1, ...columns.map((c) => c.length));
    const width = columns.length * (NODE_W + GAP_X) - GAP_X + 20;
    const height = tall * (NODE_H + GAP_Y) - GAP_Y + 20;
    svg.setAttribute("viewBox", `-10 -10 ${Math.max(width, 200)} ${Math.max(height, 80)}`);
    const pos = new Map();
    columns.forEach((column, x) => column.forEach((task, y) => {
      const offset = ((tall - column.length) * (NODE_H + GAP_Y)) / 2;
      pos.set(task.id, { x: x * (NODE_W + GAP_X), y: offset + y * (NODE_H + GAP_Y) });
    }));
    const edges = el("g", { class: "ag-edges" });
    const nodes = el("g", { class: "ag-nodes" });
    tasks.forEach((task) => {
      const to = pos.get(task.id);
      (task.depends_on || []).forEach((dep) => {
        const from = pos.get(dep);
        if (!from) return;
        const x1 = from.x + NODE_W, y1 = from.y + NODE_H / 2, x2 = to.x, y2 = to.y + NODE_H / 2, mid = (x1 + x2) / 2;
        edges.appendChild(el("path", { d: `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`, "data-status": task.status }));
      });
      const group = el("g", { class: "ag-node", "data-status": task.status, transform: `translate(${to.x},${to.y})` });
      group.appendChild(el("rect", { width: NODE_W, height: NODE_H, rx: 10 }));
      const title = el("text", { x: 12, y: 18, class: "ag-node-title" });
      title.textContent = shorten(task.title || task.id, 24);
      const meta = el("text", { x: 12, y: 34, class: "ag-node-meta" });
      meta.textContent = `${task.role} · ${statusLabel(task.status)}`;
      const tip = el("title");
      tip.textContent = task.title || task.id;
      group.append(tip, title, meta);
      nodes.appendChild(group);
    });
    svg.append(edges, nodes);
  }

  window.NuxivaAgencyGraph = { render, layers };
})();
