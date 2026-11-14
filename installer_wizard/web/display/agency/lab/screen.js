(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const TONE = Object.freeze({
    work: "#29e0ff", idle: "#7aa2c8", error: "#ff4d6d", review: "#ffb547", done: "#5dff8f",
    paused: "#9aa7b8", consult: "#c084fc", wait: "#7aa2c8",
  });
  const GLYPH = Object.freeze({ done: "✓", running: "▶", review: "◔", failed: "!", pending: "○", cancelled: "×", blocked: "■" });
  const FONT = '"Inter","Segoe UI",system-ui,sans-serif';

  const T = (key, params) => {
    try { return (window.PageText && window.PageText.t("web/display", key, params)) || ""; } catch (err) { return ""; }
  };

  function fit(ctx, text, max) {
    let out = String(text || "");
    if (ctx.measureText(out).width <= max) return out;
    while (out.length > 1 && ctx.measureText(`${out}…`).width > max) out = out.slice(0, -1);
    return `${out}…`;
  }

  function wrap(ctx, text, max, lines) {
    const words = String(text || "").split(/\s+/).filter(Boolean);
    const rows = [];
    let row = "";
    for (const word of words) {
      const next = row ? `${row} ${word}` : word;
      if (ctx.measureText(next).width > max && row) { rows.push(row); row = word; } else row = next;
      if (rows.length === lines) break;
    }
    if (row && rows.length < lines) rows.push(row);
    if (rows.length === lines && words.join(" ").length > rows.join(" ").length) rows[lines - 1] = fit(ctx, `${rows[lines - 1]} …`, max);
    return rows;
  }

  function background(ctx, w, h, tone, dim) {
    const g = ctx.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, "#07101d");
    g.addColorStop(1, dim ? "#0c1119" : "#0f2038");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "rgba(120,170,220,0.07)";
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 32) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    const glow = ctx.createRadialGradient(w * 0.15, 0, 0, w * 0.15, 0, w * 0.7);
    glow.addColorStop(0, `${tone}33`);
    glow.addColorStop(1, "transparent");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);
  }

  function monitor(ctx, w, h, d, t) {
    const tone = TONE[d.mode] || TONE.idle;
    background(ctx, w, h, tone, d.mode === "paused");
    ctx.textBaseline = "middle";
    ctx.fillStyle = tone;
    ctx.beginPath();
    ctx.arc(26, 26, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = `600 22px ${FONT}`;
    ctx.fillStyle = "#e8f1fb";
    ctx.fillText(fit(ctx, d.name, w * 0.5), 44, 26);
    ctx.font = `600 16px ${FONT}`;
    const label = d.label || "";
    const lw = ctx.measureText(label).width + 28;
    ctx.fillStyle = `${tone}2a`;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(w - lw - 18, 10, lw, 32, 16) : ctx.rect(w - lw - 18, 10, lw, 32);
    ctx.fill();
    ctx.fillStyle = tone;
    ctx.fillText(label, w - lw - 4, 27);

    const current = d.tasks.find((x) => x.status === "running") || d.tasks.find((x) => x.status === "review")
      || d.tasks.find((x) => x.status === "failed") || d.tasks.find((x) => x.status === "pending") || d.tasks[d.tasks.length - 1];
    const done = d.tasks.filter((x) => x.status === "done").length;
    const total = Math.max(1, d.tasks.length);
    const left = 24;
    const colW = w * 0.5 - 34;

    if (d.mode === "error") {
      ctx.fillStyle = "rgba(255,77,109,0.14)";
      ctx.fillRect(0, 56, w, h - 56);
    }
    ctx.font = `700 26px ${FONT}`;
    ctx.fillStyle = "#f3f8ff";
    if (current) wrap(ctx, current.title, colW, 3).forEach((row, i) => ctx.fillText(row, left, 90 + i * 32));
    ctx.font = `500 16px ${FONT}`;
    ctx.fillStyle = "#8aa4bf";
    if (current && current.attempts > 1) ctx.fillText(T("lab_screen_attempts", { n: current.attempts }), left, 196);

    const barY = h - 46;
    ctx.fillStyle = "rgba(255,255,255,0.1)";
    ctx.fillRect(left, barY, colW, 12);
    ctx.fillStyle = tone;
    ctx.fillRect(left, barY, colW * (done / total), 12);
    ctx.font = `600 15px ${FONT}`;
    ctx.fillStyle = "#cfe3f7";
    ctx.fillText(`${done}/${d.tasks.length}`, left, barY - 14);

    const px = w * 0.5 + 6;
    ctx.fillStyle = "rgba(255,255,255,0.045)";
    ctx.fillRect(px - 10, 58, w - px - 6, h - 70);
    ctx.font = `500 17px ${FONT}`;
    d.tasks.slice(0, 7).forEach((task, i) => {
      const y = 82 + i * 30;
      const active = task.status === "running";
      if (active) {
        ctx.fillStyle = `${tone}22`;
        ctx.fillRect(px - 8, y - 14, w - px - 10, 28);
      }
      ctx.fillStyle = task.status === "failed" ? TONE.error : task.status === "done" ? TONE.done : active ? tone : "#8aa4bf";
      ctx.fillText(GLYPH[task.status] || "·", px, y);
      ctx.fillStyle = active ? "#ffffff" : "#b7cbe0";
      ctx.fillText(fit(ctx, task.title, w - px - 54), px + 24, y);
    });
    if (d.mode === "work") {
      const blink = Math.floor(t * 2) % 2 === 0;
      ctx.fillStyle = blink ? tone : "transparent";
      ctx.fillRect(left, 214, 12, 20);
      for (let i = 0; i < 18; i += 1) {
        const bar = 6 + (Math.sin(t * 5 + i * 0.7) * 0.5 + 0.5) * 22;
        ctx.fillStyle = `${tone}88`;
        ctx.fillRect(left + 28 + i * 9, 234 - bar, 6, bar);
      }
    }
    if (d.mode === "done") {
      ctx.font = `700 120px ${FONT}`;
      ctx.fillStyle = "rgba(93,255,143,0.16)";
      ctx.fillText("✓", w * 0.28, h * 0.62);
    }
    if (d.mode === "paused") {
      ctx.fillStyle = "rgba(255,255,255,0.12)";
      ctx.fillRect(w * 0.2, h * 0.38, 22, 70);
      ctx.fillRect(w * 0.2 + 40, h * 0.38, 22, 70);
    }
  }

  function wall(ctx, w, h, d, t) {
    const tone = d.failed > 0 ? TONE.error : d.status === "paused" ? TONE.paused : d.status === "completed" ? TONE.done : TONE.work;
    background(ctx, w, h, tone, false);
    ctx.textBaseline = "middle";
    ctx.font = `600 22px ${FONT}`;
    ctx.fillStyle = "#7aa2c8";
    ctx.fillText(String(d.kicker || "").toUpperCase(), 48, 54);
    ctx.font = `700 54px ${FONT}`;
    ctx.fillStyle = "#f3f8ff";
    wrap(ctx, d.title, w - 360, 2).forEach((row, i) => ctx.fillText(row, 48, 118 + i * 62));
    ctx.font = `500 24px ${FONT}`;
    ctx.fillStyle = "#9db6cf";
    wrap(ctx, d.goal, w - 360, 3).forEach((row, i) => ctx.fillText(row, 48, 270 + i * 34));
    const cx = w - 150;
    const cy = h / 2;
    ctx.lineWidth = 16;
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.beginPath();
    ctx.arc(cx, cy, 90, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = tone;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.arc(cx, cy, 90, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1, d.percent / 100));
    ctx.stroke();
    ctx.font = `700 52px ${FONT}`;
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.fillText(`${Math.round(d.percent)}%`, cx, cy - 4);
    ctx.font = `500 20px ${FONT}`;
    ctx.fillStyle = tone;
    ctx.fillText(d.statusLabel, cx, cy + 46);
    ctx.textAlign = "left";
    const pulse = (Math.sin(t * 2) * 0.5 + 0.5) * 0.5 + 0.5;
    ctx.fillStyle = tone;
    ctx.globalAlpha = pulse;
    ctx.fillRect(48, h - 44, 120, 4);
    ctx.globalAlpha = 1;
  }

  const COLS = ["pending", "running", "review", "done", "failed"];

  function board(ctx, w, h, tasks) {
    ctx.fillStyle = "#e9eef4";
    ctx.fillRect(0, 0, w, h);
    ctx.textBaseline = "middle";
    const cw = (w - 40) / COLS.length;
    COLS.forEach((col, i) => {
      const x = 20 + i * cw;
      const tone = col === "failed" ? TONE.error : col === "done" ? "#16a34a" : col === "review" ? "#d97706" : col === "running" ? "#0284c7" : "#64748b";
      ctx.fillStyle = tone;
      ctx.fillRect(x + 6, 18, cw - 12, 6);
      ctx.font = `700 26px ${FONT}`;
      ctx.fillText(T(`agency_status_${col}`), x + 8, 54);
      tasks.filter((t) => t.status === col).slice(0, 6).forEach((t, j) => {
        const y = 86 + j * 66;
        ctx.fillStyle = "#fff8c4";
        ctx.fillRect(x + 6, y, cw - 14, 56);
        ctx.fillStyle = `${tone}55`;
        ctx.fillRect(x + 6, y, 6, 56);
        ctx.fillStyle = "#1e293b";
        ctx.font = `600 19px ${FONT}`;
        wrap(ctx, t.title, cw - 44, 2).forEach((row, k) => ctx.fillText(row, x + 20, y + 19 + k * 22));
      });
    });
  }

  function badge(ctx, w, h, tone, text) {
    ctx.clearRect(0, 0, w, h);
    let size = 30;
    ctx.font = `700 ${size}px ${FONT}`;
    while (size > 18 && ctx.measureText(text).width > w - 100) { size -= 2; ctx.font = `700 ${size}px ${FONT}`; }
    const tw = Math.min(w - 20, ctx.measureText(text).width + 48);
    const x = (w - tw) / 2;
    ctx.fillStyle = "rgba(6,12,22,0.82)";
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(x, 8, tw, h - 24, (h - 24) / 2) : ctx.rect(x, 8, tw, h - 24);
    ctx.fill();
    ctx.fillStyle = tone;
    ctx.beginPath();
    ctx.arc(x + 24, h / 2 - 4, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#f3f8ff";
    ctx.textBaseline = "middle";
    ctx.fillText(fit(ctx, text, tw - 56), x + 42, h / 2 - 4);
  }

  LAB.screen = Object.freeze({ monitor, wall, board, badge, TONE, T });
})();
