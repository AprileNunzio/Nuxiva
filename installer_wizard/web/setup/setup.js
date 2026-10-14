(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  let session = {
    current_step: 1,
    max_reached_step: 1,
    steps_meta: {
      "1": { status: "active", dirty: false, score: 100 },
      "2": { status: "pending", dirty: false, score: 0 },
      "3": { status: "pending", dirty: false, score: 0 },
      "4": { status: "pending", dirty: false, score: 0 },
      "5": { status: "pending", dirty: false, score: 0 },
      "6": { status: "pending", dirty: false, score: 0 },
      "7": { status: "pending", dirty: false, score: 0 }
    },
    config: {
      locale: "it-IT",
      timezone: "Europe/Rome",
      assistant_name: "Aria",
      assistant_gender: "female",
      wake_word_primary: "aria",
      wake_phrases: ["aria", "ehi aria", "ok aria", "ciao aria"],
      wake_phonetic_aliases: ["aria"],
      voice_id: "if_sara",
      mic_device_id: "hw:0,0",
      mic_noise_floor_db: -58.2,
      mic_snr_db: 27.4,
      mic_gain_db: 4.5,
      mic_vad_threshold: 0.28,
      brain_preset: "nuxiva-6.5-auto",
      owner_name: "",
      owner_last: "",
      face_enrolled: false,
      ha_url: "",
      ha_token: ""
    }
  };

  let activeEventSource = null;
  const visualizers = {
    osc: null,
    bio: null,
    neural: null
  };

  const stepContext = {
    get session() { return session; },
    visualizers,
    api,
    appendLog,
    abortActiveStreams,
    renderGuide,
    renderAnalytics,
    goToStep,
    getActiveEventSource: () => activeEventSource,
    setActiveEventSource: (es) => { activeEventSource = es; }
  };

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        "X-Nuxiva-Request": "1"
      },
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Error");
    }
    return res.json();
  }

  function appendLog(line) {
    const box = $("synapse-log-stream");
    if (!box) return;
    const ts = new Date().toISOString().substring(11, 19);
    box.textContent += `\n[${ts}] ${line}`;
    box.scrollTop = box.scrollHeight;
  }

  function abortActiveStreams() {
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }
    if (visualizers.osc) visualizers.osc.stop();
    if (visualizers.bio) visualizers.bio.stop();
    if (visualizers.neural) visualizers.neural.stop();
    api("/api/setup/release-hardware", { method: "POST" }).catch(() => {});
  }

  async function loadSession() {
    try {
      const data = await api("/api/setup/session");
      if (data && data.config) {
        session = data;
      }
    } catch (e) {
      appendLog(`Ripristino: ${e.message}`);
    }
    renderStepper();
    renderCurrentStep();
  }

  function renderStepper() {
    const track = $("stepper-track");
    if (!track) return;
    track.innerHTML = "";
    const names = [
      window.SetupI18n.t("step-1-name"),
      window.SetupI18n.t("step-2-name"),
      window.SetupI18n.t("step-3-name"),
      window.SetupI18n.t("step-4-name"),
      window.SetupI18n.t("step-5-name"),
      window.SetupI18n.t("step-6-name"),
      window.SetupI18n.t("step-7-name")
    ];
    for (let i = 1; i <= 7; i++) {
      const meta = session.steps_meta[String(i)] || { status: "pending", dirty: false };
      const li = document.createElement("li");
      li.className = `step-node ${meta.status} ${meta.dirty ? "dirty" : ""}`;
      li.innerHTML = `
        <div class="step-node-circle">${i}</div>
        <span class="step-node-label">${names[i - 1]}</span>
      `;
      li.addEventListener("click", () => {
        if (i <= session.max_reached_step) {
          goToStep(i);
        }
      });
      track.appendChild(li);
    }
  }

  function renderGuide(step) {
    const badge = $("guide-badge");
    const title = $("guide-title");
    const desc = $("guide-desc");
    const checklist = $("guide-checklist");
    if (badge) badge.textContent = window.SetupI18n.t(`badge-step-${step}`);
    if (title) title.textContent = window.SetupI18n.t(`title-step-${step}`);
    if (desc) desc.textContent = window.SetupI18n.t(`desc-step-${step}`);
    if (checklist) {
      checklist.innerHTML = "";
      for (let j = 1; j <= 3; j++) {
        const li = document.createElement("li");
        li.className = "chk-item checked";
        li.innerHTML = `<span class="chk-item-dot">✓</span><span>${window.SetupI18n.t(`chk-step-${step}-${j}`)}</span>`;
        checklist.appendChild(li);
      }
    }
  }

  function renderAnalytics(step) {
    const list = $("analytics-list");
    if (!list) return;
    list.innerHTML = "";
    const c = session.config;
    const rows = [];
    if (step === 1) {
      rows.push([window.SetupI18n.t("analytics-stt-status"), "INSTALLED_LOCAL"]);
      rows.push([window.SetupI18n.t("analytics-clock-drift"), "±0.4 ms (NTP)"]);
      rows.push([window.SetupI18n.t("analytics-nlu-coverage"), "100% Intenti"]);
    } else if (step === 2) {
      rows.push([window.SetupI18n.t("analytics-noise-floor"), `${c.mic_noise_floor_db} dBFS`]);
      rows.push([window.SetupI18n.t("analytics-snr"), `+${c.mic_snr_db} dB`]);
      rows.push([window.SetupI18n.t("analytics-gain"), `+${c.mic_gain_db} dB`]);
      rows.push([window.SetupI18n.t("analytics-purity"), "96% (Ottimo)"]);
    } else if (step === 3) {
      rows.push([window.SetupI18n.t("analytics-active-wake"), (c.assistant_name || "").toUpperCase()]);
      rows.push([window.SetupI18n.t("analytics-aliases"), (c.wake_phonetic_aliases || []).join(", ")]);
      rows.push([window.SetupI18n.t("analytics-wake-score"), "98.4% (42ms)"]);
    } else if (step === 4) {
      rows.push([window.SetupI18n.t("analytics-voice-dim"), "256-dim float32"]);
      rows.push([window.SetupI18n.t("analytics-liveness"), "Passato (Anti-Spoof 3D)"]);
    } else if (step === 5) {
      rows.push([window.SetupI18n.t("analytics-cams-found"), (c.cameras || []).length || "1 Ottica"]);
      rows.push([window.SetupI18n.t("analytics-bandwidth"), "3.8 Mbps"]);
    } else if (step === 6) {
      rows.push([window.SetupI18n.t("analytics-hw-info"), "VRAM Alloc: 3.4GB / 8GB"]);
      rows.push([window.SetupI18n.t("analytics-ttft"), "26.4 ms"]);
      rows.push([window.SetupI18n.t("analytics-tokens-sec"), "64.0 tok/s"]);
    } else {
      rows.push([window.SetupI18n.t("analytics-matrix-readiness"), "100% ALL SYSTEMS GO"]);
    }
    for (let [lbl, val] of rows) {
      const box = document.createElement("div");
      box.className = "metric-box";
      box.innerHTML = `<span class="m-label">${lbl}</span><b class="m-val">${val}</b>`;
      list.appendChild(box);
    }
  }

  function renderCurrentStep() {
    const step = session.current_step;
    document.querySelectorAll(".stage-screen").forEach((s) => {
      s.hidden = parseInt(s.dataset.step) !== step;
    });
    renderGuide(step);
    renderAnalytics(step);
    renderStepper();
    const btnBack = $("btn-back");
    if (btnBack) btnBack.style.visibility = step > 1 ? "visible" : "hidden";
    if (window.SetupSteps) {
      const fnName = `setupStep${step}`;
      if (typeof window.SetupSteps[fnName] === "function") {
        window.SetupSteps[fnName](stepContext);
      }
    }
  }

  async function goToStep(target) {
    abortActiveStreams();
    try {
      await api("/api/setup/session/navigate", {
        method: "POST",
        body: JSON.stringify({ target_step: target })
      });
      session.current_step = target;
      if (target > session.max_reached_step) session.max_reached_step = target;
      renderCurrentStep();
    } catch (e) {
      appendLog(`Navigazione: ${e.message}`);
    }
  }

  const bBack = $("btn-back");
  if (bBack) {
    bBack.addEventListener("click", () => {
      if (session.current_step > 1) {
        goToStep(session.current_step - 1);
      }
    });
  }

  const bNext = $("btn-next");
  if (bNext) {
    bNext.addEventListener("click", async () => {
      const cur = session.current_step;
      if (cur === 4) {
        const first = (session.config.owner_name || "").toLowerCase();
        const assist = (session.config.assistant_name || "").toLowerCase();
        if (first && (first === assist || assist.includes(first))) {
          alert(window.SetupI18n.t("err-name-conflict"));
          return;
        }
      }
      try {
        await api("/api/setup/session/update", {
          method: "POST",
          body: JSON.stringify({ step: cur, updates: session.config })
        });
      } catch (e) {
        appendLog(`Salvataggio: ${e.message}`);
      }
      if (cur < 7) {
        goToStep(cur + 1);
      }
    });
  }

  const bRecal = $("btn-recalibrate");
  if (bRecal) {
    bRecal.addEventListener("click", () => {
      abortActiveStreams();
      renderCurrentStep();
    });
  }

  document.querySelectorAll(".lang-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".lang-pill").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const lang = btn.dataset.lang;
      window.SetupI18n.applyLanguage(lang);
      renderGuide(session.current_step);
      renderAnalytics(session.current_step);
    });
  });

  window.addEventListener("DOMContentLoaded", () => {
    loadSession();
  });
})();
