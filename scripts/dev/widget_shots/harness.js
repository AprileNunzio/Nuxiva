(async () => {
  const q = new URLSearchParams(location.search);
  const lang = q.get("lang") || "it";
  document.documentElement.lang = lang;
  window.NUXIVA_UI_LANG = lang;
  const list = await (await fetch(`/instances.json?ids=${q.get("ids") || ""}`)).json();
  const host = document.getElementById("desk");
  const W = window.innerWidth;
  const mobile = W < 720;
  const gap = 28, margin = mobile ? 16 : 40;
  const colW = mobile ? W - 2 * margin : 520;
  const cols = Math.max(1, Math.floor((W - 2 * margin + gap) / (colW + gap)));
  window.NuxivaDesk.mount(host, {
    quiet: true,
    layout({ cards, place, measure }) {
      const heights = Array(cols).fill(margin);
      for (const c of cards) {
        const span = c.inst.size === "l" || c.inst.size === "full" ? Math.min(2, cols) : 1;
        const w = colW * span + gap * (span - 1);
        let col = 0, top = Infinity;
        for (let i = 0; i + span <= cols; i++) {
          const t = Math.max(...heights.slice(i, i + span));
          if (t < top) { top = t; col = i; }
        }
        const h = measure(c, w);
        place(c, margin + col * (colW + gap), top, w);
        c.el.classList.remove("hidden");
        for (let i = col; i < col + span; i++) heights[i] = top + h + gap;
      }
      host.style.height = `${Math.max(...heights)}px`;
      document.body.dataset.ready = "1";
    },
  });
  await window.NuxivaDesk.render(list);
  setTimeout(() => window.NuxivaDesk.relayout(), 600);
})();
