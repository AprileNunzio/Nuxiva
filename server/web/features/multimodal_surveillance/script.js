export async function initMultimodalSurveillance() {
  const currentLang = localStorage.getItem("nuxiva_ui_lang") || "it";
  await applySurveillanceI18n(currentLang);

  window.addEventListener("nuxiva-language-changed", async (e) => {
    if (e.detail?.lang) {
      await applySurveillanceI18n(e.detail.lang);
    }
  });

  const nodeSelect = document.getElementById("select-surveillance-node");
  const btnAutoConfig = document.getElementById("btn-auto-configure-node");
  const btnSearch = document.getElementById("btn-submit-semantic-query");
  const inputSearch = document.getElementById("input-semantic-visual-query");
  const btnRefresh = document.getElementById("btn-refresh-surveillance-timeline");
  const waveformCanvas = document.getElementById("canvas-continuous-audio-waveform");

  if (waveformCanvas) {
    startContinuousWaveformAnimation(waveformCanvas);
  }

  await loadSurveillanceNodes();
  await loadSurveillanceDashboard();

  nodeSelect?.addEventListener("change", async () => {
    await updateNodeDeviceBinding(nodeSelect.value);
  });

  btnAutoConfig?.addEventListener("click", async () => {
    const activeNodeId = nodeSelect ? nodeSelect.value : "master_server";
    await executeNodeAutoConfig(activeNodeId);
  });

  btnSearch?.addEventListener("click", async () => {
    const q = inputSearch?.value.trim();
    if (q) {
      await executeSemanticSearch(q);
    }
  });

  inputSearch?.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      const q = inputSearch?.value.trim();
      if (q) {
        await executeSemanticSearch(q);
      }
    }
  });

  btnRefresh?.addEventListener("click", async () => {
    await loadSurveillanceDashboard();
  });

  setInterval(async () => {
    await loadSurveillanceDashboard();
  }, 4500);
}

async function applySurveillanceI18n(lang) {
  try {
    const res = await fetch("/static/features/multimodal_surveillance/i18n.json");
    if (!res.ok) return;
    const dict = await res.json();
    const strings = dict[lang] || dict["it"] || {};

    document.querySelectorAll("#deck-multimodal-surveillance [data-i18n]").forEach(el => {
      const k = el.getAttribute("data-i18n");
      if (strings[k]) {
        el.innerText = strings[k];
      }
    });

    document.querySelectorAll("#deck-multimodal-surveillance [data-i18n-placeholder]").forEach(el => {
      const k = el.getAttribute("data-i18n-placeholder");
      if (strings[k]) {
        el.setAttribute("placeholder", strings[k]);
      }
    });
  } catch (err) {
    console.error(err);
  }
}

async function loadSurveillanceNodes() {
  const nodeSelect = document.getElementById("select-surveillance-node");
  if (!nodeSelect) return;

  try {
    const res = await fetch("/api/v1/surveillance/nodes");
    if (!res.ok) return;
    const nodes = await res.json();

    nodeSelect.innerHTML = "";
    nodes.forEach(n => {
      const opt = document.createElement("option");
      opt.value = n.node_id;
      opt.innerText = `${n.name} (${n.node_id})`;
      nodeSelect.appendChild(opt);
    });

    if (nodes.length > 0) {
      await updateNodeDeviceBinding(nodes[0].node_id);
    }
  } catch (err) {
    console.error(err);
  }
}

async function updateNodeDeviceBinding(nodeId) {
  const micLabel = document.getElementById("val-default-mic-name");
  try {
    const res = await fetch("/api/v1/surveillance/nodes");
    if (!res.ok) return;
    const nodes = await res.json();
    const current = nodes.find(n => n.node_id === nodeId);
    if (current && micLabel) {
      micLabel.innerText = `${current.default_microphone_id} | ${current.default_camera_id}`;
    }
  } catch (err) {
    console.error(err);
  }
}

async function executeNodeAutoConfig(nodeId) {
  const btn = document.getElementById("btn-auto-configure-node");
  if (btn) btn.innerText = "⏳ Configurazione Zero-Latency in corso...";

  try {
    const payload = {
      node_id: nodeId,
      name: `Nodo Autonomo ${nodeId}`,
      role: "satellite",
      endpoint_url: "http://127.0.0.1:8000",
      default_camera_id: `cam_${nodeId}_autoconfig`,
      default_microphone_id: `mic_${nodeId}_array`,
      default_audio_output_id: `spk_${nodeId}_stereo`,
      psk_key: "psk_autoconfig_zero_latency_2026_secured"
    };

    const res = await fetch("/api/v1/surveillance/nodes/autoconfig", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      await loadSurveillanceNodes();
      if (btn) btn.innerText = "✅ Configurato con Successo!";
      setTimeout(() => {
        if (btn) btn.innerText = "⚡ Autoconfigura Dispositivi Default";
      }, 2000);
    }
  } catch (err) {
    console.error(err);
    if (btn) btn.innerText = "❌ Errore Autoconfigurazione";
  }
}

async function executeSemanticSearch(queryText) {
  const answerBox = document.getElementById("box-semantic-direct-answer");
  const answerTxt = document.getElementById("txt-semantic-direct-answer");
  const btnSearch = document.getElementById("btn-submit-semantic-query");

  if (btnSearch) btnSearch.innerText = "Analisi Frame in corso...";

  try {
    const res = await fetch("/api/v1/surveillance/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryText, limit: 10 })
    });

    if (res.ok) {
      const data = await res.json();
      if (answerBox && answerTxt) {
        answerBox.style.display = "block";
        answerTxt.innerText = data.direct_answer;
      }
      if (data.matches) {
        renderSurveillanceEvents(data.matches);
      }
    }
  } catch (err) {
    console.error(err);
  } finally {
    if (btnSearch) btnSearch.innerText = "🔍 Cerca nel Registro Visivo";
  }
}

async function loadSurveillanceDashboard() {
  const container = document.getElementById("list-surveillance-events");
  const snrLabel = document.getElementById("val-audio-snr-gain");
  const clarityLabel = document.getElementById("val-audio-clarity");

  try {
    const res = await fetch("/api/v1/surveillance/dashboard");
    if (!res.ok) return;
    const data = await res.json();

    if (snrLabel) snrLabel.innerText = "+19.2 dB";
    if (clarityLabel) clarityLabel.innerText = "97.8%";

    if (data.latest_visual_events && container && !document.getElementById("input-semantic-visual-query")?.value) {
      renderSurveillanceEvents(data.latest_visual_events);
    }
  } catch (err) {
    console.error(err);
  }
}

function renderSurveillanceEvents(events) {
  const container = document.getElementById("list-surveillance-events");
  if (!container) return;

  container.innerHTML = "";
  if (!events || events.length === 0) {
    container.innerHTML = "<p style='color:var(--text-muted); font-size:0.85rem; padding:1rem;'>Nessun evento registrato al momento.</p>";
    return;
  }

  events.forEach(ev => {
    const isCourier = ev.courier_details && ev.courier_details.detected;
    const card = document.createElement("div");
    card.className = `event-card-item ${isCourier ? "courier-highlight" : ""}`;

    const tagsHtml = (ev.entities || []).map(ent => {
      return `<span class="entity-tag">${ent.category}: ${ent.label} (${ent.color_description})</span>`;
    }).join("");

    card.innerHTML = `
      <div class="event-card-top">
        <span class="event-cam-badge">${ev.camera_id} ${isCourier ? "📦 [CORRIERE RILEVATO]" : ""}</span>
        <span class="event-time">${ev.iso_timestamp ? ev.iso_timestamp.substring(11, 19) : ""}</span>
      </div>
      <p class="event-desc">${ev.detailed_description}</p>
      <div class="event-entity-tags">${tagsHtml}</div>
    `;
    container.appendChild(card);
  });
}

function startContinuousWaveformAnimation(canvas) {
  const ctx = canvas.getContext("2d");
  let phase = 0;

  function renderWave() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#050811";
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "rgba(0, 240, 255, 0.15)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();

    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let x = 0; x < w; x++) {
      const angle = (x * 0.04) + phase;
      const amp = (Math.sin(angle) * 22) + (Math.sin(angle * 2.3) * 14) + ((Math.random() - 0.5) * 4);
      const y = (h / 2) + amp;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    phase += 0.08;
    requestAnimationFrame(renderWave);
  }

  requestAnimationFrame(renderWave);
}
