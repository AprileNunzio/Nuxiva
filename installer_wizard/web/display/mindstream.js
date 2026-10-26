(() => {
  const D = window.NuxivaDisplay, { $, fmt } = D;
  const esc = fmt.esc;
  let snap = null, seen = -1, open = false, timer = null;
  let currentBrainConfig = null;

  async function fetchBrainConfig() {
    try {
      const r = await fetch("/api/v2/brain/config", { cache: "no-store" });
      if (r.ok) {
        currentBrainConfig = await r.json();
      }
    } catch (_) {}
  }

  const seconds = (ms) => `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`;
  const modelLine = (model) => {
    if (!model) {
      if (currentBrainConfig && currentBrainConfig.active) {
        return modelLine(currentBrainConfig.active);
      }
      if (currentBrainConfig && currentBrainConfig.active_model) {
        const srv = currentBrainConfig.ollama_url ? currentBrainConfig.ollama_url.replace(/^https?:\/\//, "") : "Questo server";
        return `${esc(currentBrainConfig.active_model)} · ${esc(srv)}`;
      }
      return "";
    }
    // Provider reale dichiarato dal backend per questa chiamata (cloud o Ollama con il suo host effettivo):
    // non va sostituito con l'URL configurato, altrimenti un modello cloud sembrerebbe girare su Ollama.
    return `${esc(model.model)} \u00b7 ${esc(model.provider || "Questo server")}`;
  };
  function focus() {
    if (!snap) return null;
    return snap.active[snap.active.length - 1] || snap.recent[0] || null;
  }

  function steps(entry) {
    return entry.steps.map((s) => `<div class="mind-step"><b>${s.t.toFixed(1)}</b><span>${esc(s.text)}</span></div>`).join("")
      + (entry.snippet ? `<div class="mind-snippet">${esc(entry.snippet)}</div>` : "");
  }

  function recent() {
    const rows = snap.recent.filter((e) => e !== focus()).slice(0, 5).map((e) =>
      `<div><span>${esc(e.label)} → ${e.model ? esc(e.model.model) : "agente"}</span><span class="ms">${e.state === "failed" ? "errore" : seconds(e.ms)}</span></div>`);
    return rows.length ? `<div class="mind-recent">${rows.join("")}</div>` : "";
  }

  function render() {
    const box = $("mind"), entry = focus();
    if (!entry) { box.classList.add("empty"); return; }
    const live = entry.state === "thinking";
    box.className = `mind ${live ? "live" : entry.state} ${open ? "open" : ""}`;
    const kind = live ? (entry.model ? "mind_thinking" : "mind_listening") : entry.state === "failed" ? "mind_failed" : "mind_answered";
    const last = entry.steps[entry.steps.length - 1];
    $("mind-who").innerHTML = `${PageText.html(kind, {}, "small")}${esc(entry.label)}`;
    $("mind-time").textContent = live ? seconds(entry.elapsed_ms || 0) : seconds(entry.ms || 0);
    $("mind-model").innerHTML = modelLine(entry.model) || "&nbsp;";
    $("mind-line").textContent = live ? (last ? last.text : "") : (entry.snippet || (last ? last.text : ""));
    $("mind-more").innerHTML = steps(entry) + recent();
  }

  async function poll() {
    if (document.hidden) return;
    try {
      await fetchBrainConfig();
      const r = await fetch("/api/brain/trace", { cache: "no-store" });
      if (!r.ok) return;
      const data = await r.json();
      const changed = data.seq !== seen;
      snap = data; seen = data.seq;
      if (changed || data.active.length) render();
    } catch (e) { return; }
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(async () => { await poll(); schedule(); }, snap && snap.active.length ? 500 : 1000);
  }

  D.startMindStream = () => {
    $("mind").addEventListener("click", () => { open = !open; render(); });
    document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
    fetchBrainConfig().then(render);
    poll().then(schedule);
  };
})();
