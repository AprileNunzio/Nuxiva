(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  function setupStep1(ctx) {
    const { session, api, renderGuide, renderAnalytics } = ctx;
    const grid = $("lang-cards");
    if (!grid) return;
    grid.innerHTML = "";
    const langs = [
      { code: "it", name: "Italiano", flag: "🇮🇹" },
      { code: "en", name: "English", flag: "🇬🇧" },
      { code: "es", name: "Español", flag: "🇪🇸" },
      { code: "fr", name: "Français", flag: "🇫🇷" }
    ];
    langs.forEach((l) => {
      const card = document.createElement("div");
      const isAct = session.config.locale.startsWith(l.code);
      card.className = `lang-hud-card ${isAct ? "active" : ""}`;
      card.innerHTML = `<span style="font-size:1.6rem">${l.flag}</span><div><b>${l.name}</b><br><small style="color:#7fa4bf">${l.code.toUpperCase()}</small></div>`;
      card.addEventListener("click", () => {
        session.config.locale = `${l.code}-${l.code.toUpperCase()}`;
        window.SetupI18n.applyLanguage(l.code);
        api("/api/locale/prepare", {
          method: "POST",
          body: JSON.stringify({ locale: session.config.locale })
        }).catch(() => {});
        setupStep1(ctx);
        renderGuide(1);
        renderAnalytics(1);
      });
      grid.appendChild(card);
    });
  }

  function setupStep2(ctx) {
    const { session, abortActiveStreams, renderAnalytics } = ctx;
    const canvas = $("canvas-oscilloscope");
    if (!canvas) return;
    if (!ctx.visualizers.osc && window.SetupCanvas) {
      ctx.visualizers.osc = new window.SetupCanvas.Oscilloscope(canvas);
    }
    if (ctx.visualizers.osc) ctx.visualizers.osc.start();
    const btn = $("btn-start-mic-cal");
    if (!btn) return;
    btn.onclick = () => {
      abortActiveStreams();
      if (ctx.visualizers.osc) ctx.visualizers.osc.start();
      $("mic-phase-msg").textContent = window.SetupI18n.t("mic-phase-silence");
      ctx.setActiveEventSource(new EventSource("/api/ear/calibration-stream"));
      const es = ctx.getActiveEventSource();
      if (es) {
        es.onmessage = (e) => {
          const d = JSON.parse(e.data);
          if (ctx.visualizers.osc) {
            ctx.visualizers.osc.update(d.fft_bins, (d.vad_probability || 0.28));
          }
          $("bottom-status-msg").textContent = `RMS: ${d.rms_db} dB | SNR: +${d.snr_db} dB`;
          if (d.paused) {
            $("mic-phase-msg").textContent = window.SetupI18n.t("mic-paused-alert");
          } else if (d.calibration_phase === "dsp") {
            $("mic-phase-msg").textContent = window.SetupI18n.t("mic-phase-dsp");
          } else if (d.calibration_phase === "voice") {
            $("mic-phase-msg").textContent = window.SetupI18n.t("mic-phase-voice");
          } else if (d.calibration_phase === "calibrated") {
            $("mic-phase-msg").textContent = window.SetupI18n.t("mic-phase-done");
            session.config.mic_noise_floor_db = d.rms_db;
            session.config.mic_snr_db = d.snr_db;
            abortActiveStreams();
            renderAnalytics(2);
          }
        };
      }
    };
  }

  function setupStep3(ctx) {
    const { session, api, abortActiveStreams, appendLog, renderAnalytics } = ctx;
    const input = $("input-assistant-name");
    const orbit = $("orbit-assistant-title");
    const launchLbl = $("launch-btn-label");
    const chipsBox = $("quick-name-chips");
    const suggestions = ["Aria", "Atlas", "Athena", "Orion", "Venerdi"];
    if (chipsBox) {
      chipsBox.innerHTML = "";
      suggestions.forEach((nm) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chip";
        btn.textContent = nm;
        btn.addEventListener("click", () => {
          if (input) input.value = nm;
          updateAssistantName(nm);
        });
        chipsBox.appendChild(btn);
      });
    }
    function updateAssistantName(nm) {
      session.config.assistant_name = nm;
      const clean = nm.toLowerCase().replace("hey ", "").replace("ehi ", "").trim();
      session.config.wake_word_primary = clean;
      session.config.wake_phrases = [clean, `ehi ${clean}`, `ok ${clean}`, `ciao ${clean}`];
      session.config.wake_phonetic_aliases = [clean];
      if (orbit) orbit.textContent = `${window.SetupI18n.t("orbit-badge-label")}: ${nm.toUpperCase()}`;
      if (launchLbl) launchLbl.textContent = window.SetupI18n.t("btn-activate", { name: nm.toUpperCase() });
      const promptEl = $("ring-prompt-txt");
      if (promptEl) {
        promptEl.textContent = `${window.SetupI18n.t("wake-prompt-prefix")} «${nm}» ${window.SetupI18n.t("wake-prompt-suffix")}`;
      }
      renderAnalytics(3);
    }
    if (input) {
      input.oninput = () => updateAssistantName(input.value.trim() || "Aria");
      updateAssistantName(input.value.trim() || "Aria");
    }

    const vcards = $("voice-cards");
    if (vcards) {
      vcards.innerHTML = `
        <div class="voice-card active" data-gender="female">${window.SetupI18n.t("lbl-voice-female")}</div>
        <div class="voice-card" data-gender="male">${window.SetupI18n.t("lbl-voice-male")}</div>
      `;
      vcards.querySelectorAll(".voice-card").forEach((c) => {
        c.addEventListener("click", () => {
          vcards.querySelectorAll(".voice-card").forEach((el) => el.classList.remove("active"));
          c.classList.add("active");
          session.config.assistant_gender = c.dataset.gender;
        });
      });
    }
    const btnPreview = $("btn-voice-preview");
    if (btnPreview) {
      btnPreview.onclick = () => {
        api("/api/setup/voice_preview", {
          method: "POST",
          body: JSON.stringify({
            lang: session.config.locale.split("-")[0],
            gender: session.config.assistant_gender,
            name: session.config.assistant_name
          })
        }).catch(() => {});
        appendLog(`TTS: "${session.config.assistant_name}"`);
      };
    }

    [1, 2, 3].forEach((shot) => {
      const ring = $(`ring-${shot}`);
      if (ring) {
        ring.onclick = () => {
          ring.classList.add("active");
          ctx.setActiveEventSource(new EventSource(`/api/ear/wakeword-training-stream?name=${encodeURIComponent(session.config.assistant_name)}&sample=${shot}`));
          const es = ctx.getActiveEventSource();
          if (es) {
            es.onmessage = (e) => {
              const d = JSON.parse(e.data);
              appendLog(`[TRAIN] Shot ${shot}: ${d.confidence_pct}% (${d.latency_ms}ms)`);
              if (d.step >= 28) {
                ring.classList.remove("active");
                ring.classList.add("passed");
                abortActiveStreams();
              }
            };
          }
        };
      }
    });
  }

  function setupStep4(ctx) {
    const { session, renderAnalytics } = ctx;
    const canvas = $("canvas-voiceprint");
    if (canvas && !ctx.visualizers.bio && window.SetupCanvas) {
      ctx.visualizers.bio = new window.SetupCanvas.BiometricRadar(canvas);
    }
    if (ctx.visualizers.bio) ctx.visualizers.bio.start();
    const btn = $("btn-trigger-face");
    if (btn) {
      btn.onclick = () => {
        btn.textContent = "...";
        setTimeout(() => {
          btn.textContent = "OK ✓";
          session.config.face_enrolled = true;
          renderAnalytics(4);
        }, 1500);
      };
    }
    const oFirst = $("owner-first-input");
    if (oFirst) {
      oFirst.oninput = (e) => {
        session.config.owner_name = e.target.value.trim();
      };
    }
    const oLast = $("owner-last-input");
    if (oLast) {
      oLast.oninput = (e) => {
        session.config.owner_last = e.target.value.trim();
      };
    }
  }

  function setupStep5(ctx) {
    const { session, api, renderAnalytics } = ctx;
    api("/api/cameras/scan", { method: "POST" }).then((data) => {
      session.config.cameras = data.devices;
      const matrix = $("cam-matrix");
      if (!matrix) return;
      matrix.innerHTML = "";
      data.devices.forEach((d) => {
        const card = document.createElement("div");
        card.className = "metric-box";
        card.innerHTML = `
          <div>
            <b>${d.name}</b><br>
            <small style="color:#7fa4bf">${d.type} · ${d.resolution} · ${d.fps}fps</small>
          </div>
          <select class="hud-text-input" style="width:110px; padding:4px 8px; font-size:0.75rem">
            <option>Area 1</option>
            <option>Area 2</option>
            <option>Area 3</option>
          </select>
        `;
        matrix.appendChild(card);
      });
      const cCount = $("cams-count-text");
      if (cCount) cCount.textContent = `${data.count} · ${data.total_bandwidth_mbps} Mbps`;
      renderAnalytics(5);
    }).catch(() => {});
  }

  function setupStep6(ctx) {
    const { session, api, appendLog } = ctx;
    const canvas = $("canvas-neural-graph");
    if (canvas && !ctx.visualizers.neural && window.SetupCanvas) {
      ctx.visualizers.neural = new window.SetupCanvas.NeuralSpike(canvas);
    }
    if (ctx.visualizers.neural) ctx.visualizers.neural.start();
    const presetsBox = $("brain-presets");
    if (!presetsBox) return;
    presetsBox.innerHTML = "";
    const list = [
      { id: "nuxiva-5.0-veloce", name: "5.0 Fast", sub: "3 rami" },
      { id: "nuxiva-5.0-empatico", name: "5.0 Empathetic", sub: "6 rami" },
      { id: "nuxiva-6.0-pro", name: "6.0 Pro", sub: "8 rami" },
      { id: "nuxiva-6.5-ultra", name: "6.5 Ultra", sub: "16 rami" },
      { id: "nuxiva-6.5-auto", name: "6.5 Auto", sub: "Dinamico" }
    ];
    list.forEach((p) => {
      const card = document.createElement("div");
      card.className = `brain-card ${session.config.brain_preset === p.id ? "active" : ""}`;
      card.innerHTML = `<b>${p.name}</b><br><small style="color:#7fa4bf">${p.sub}</small>`;
      card.addEventListener("click", () => {
        session.config.brain_preset = p.id;
        if (ctx.visualizers.neural) ctx.visualizers.neural.setPreset(p.id);
        setupStep6(ctx);
        api("/api/brain/benchmark", {
          method: "POST",
          body: JSON.stringify({ preset: p.id })
        }).then((res) => {
          appendLog(`[BENCH] TTFT: ${res.benchmark.ttft_ms}ms · ${res.benchmark.tok_sec} tok/s`);
        }).catch(() => {});
      });
      presetsBox.appendChild(card);
    });
  }

  function setupStep7(ctx) {
    const { session, api, appendLog, goToStep } = ctx;
    const matrix = $("matrix-summary");
    if (!matrix) return;
    matrix.innerHTML = "";
    const modules = [
      { step: 1, name: "Lingua & Fuso", val: session.config.locale },
      { step: 2, name: "Calibrazione Acustica", val: `${session.config.mic_noise_floor_db} dBFS` },
      { step: 3, name: "Identità & Risveglio", val: session.config.assistant_name },
      { step: 4, name: "Proprietario & Bio", val: session.config.owner_name || "OK" },
      { step: 5, name: "Topologia Camere", val: `${(session.config.cameras || []).length || 1} Cam` },
      { step: 6, name: "Cervello Neurale", val: session.config.brain_preset }
    ];
    modules.forEach((m) => {
      const card = document.createElement("div");
      card.className = "ready-summary-card";
      card.innerHTML = `
        <div>
          <b style="color:#ffffff">${m.name}</b><br>
          <small style="color:var(--cyan)">${m.val}</small>
        </div>
        <button type="button" class="hud-btn-ghost" style="padding:4px 8px; font-size:0.72rem">Step ${m.step}</button>
      `;
      card.querySelector("button").onclick = () => goToStep(m.step);
      matrix.appendChild(card);
    });
    const launchBtn = $("btn-final-launch");
    if (launchBtn) {
      launchBtn.onclick = async () => {
        launchBtn.disabled = true;
        launchBtn.style.opacity = "0.7";
        appendLog("Sigillatura...");
        try {
          const res = await api("/api/setup/finalize", {
            method: "POST",
            body: JSON.stringify(session.config)
          });
          appendLog(`${res.assistant_name} online.`);
          setTimeout(() => {
            window.location.href = "/";
          }, 1200);
        } catch (e) {
          appendLog(`Errore: ${e.message}`);
          launchBtn.disabled = false;
          launchBtn.style.opacity = "1";
        }
      };
    }
  }

  window.SetupSteps = {
    setupStep1,
    setupStep2,
    setupStep3,
    setupStep4,
    setupStep5,
    setupStep6,
    setupStep7
  };
})();
