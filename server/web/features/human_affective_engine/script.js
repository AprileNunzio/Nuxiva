export async function initHumanAffectiveEngine() {
  const currentLang = localStorage.getItem("nuxiva_ui_lang") || "it";
  await applyAffectiveI18n(currentLang);

  window.addEventListener("nuxiva-language-changed", async (e) => {
    if (e.detail?.lang) {
      await applyAffectiveI18n(e.detail.lang);
    }
  });

  const canvasPulse = document.getElementById("canvas-rppg-pulse-wave");
  if (canvasPulse) {
    startRppgPulseWaveAnimation(canvasPulse);
  }

  const btnRun = document.getElementById("btn-run-affective-assessment");
  btnRun?.addEventListener("click", async () => {
    await triggerMockAffectiveEvaluation();
  });

  setInterval(async () => {
    await updateLiveBiometricPill();
  }, 3500);
}

async function applyAffectiveI18n(lang) {
  try {
    const res = await fetch("/static/features/human_affective_engine/i18n.json");
    if (!res.ok) return;
    const dict = await res.json();
    const strings = dict[lang] || dict["it"] || {};

    document.querySelectorAll("#deck-affective-engine [data-i18n]").forEach(el => {
      const k = el.getAttribute("data-i18n");
      if (strings[k]) {
        el.innerText = strings[k];
      }
    });
  } catch (err) {
    console.error(err);
  }
}

async function triggerMockAffectiveEvaluation() {
  const btn = document.getElementById("btn-run-affective-assessment");
  if (btn) btn.innerText = "⏳ Inferenza Multimodale in corso...";

  try {
    const payload = {
      user_id: "user_primary",
      timestamp: Date.now() / 1000,
      heart_metrics: {
        bpm: 74.0,
        hrv_rmssd_ms: 38.0,
        signal_quality: 0.95,
        pulse_confidence: 0.92
      },
      vocal_metrics: {
        pitch_f0_mean_hz: 135.0,
        pitch_variability_st: 18.0,
        jitter_percent: 0.8,
        shimmer_percent: 2.1,
        monotone_score: 0.22,
        vocal_energy_rms: 0.18,
        speech_pause_ratio: 0.16,
        depressive_vocal_indicator: 0.18
      },
      ocular_metrics: {
        gaze_direction: "center",
        downward_gaze_ratio: 0.12,
        blink_rate_per_min: 17.0,
        eye_aspect_ratio_mean: 0.29,
        fixation_stagnation_score: 0.45,
        blunted_affect_indicator: 0.16
      }
    };

    const res = await fetch("/api/v1/affective/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      renderAffectiveState(data);
    }
  } catch (err) {
    console.error(err);
  } finally {
    if (btn) btn.innerText = "⚡ Esegui Valutazione Multimodale";
  }
}

function renderAffectiveState(data) {
  const badgeMood = document.getElementById("badge-current-mood-state");
  const barDep = document.getElementById("bar-depression-risk");
  const valDep = document.getElementById("val-depression-risk-pct");
  const barAnx = document.getElementById("bar-anxiety-risk");
  const valAnx = document.getElementById("val-anxiety-risk-pct");
  const barFat = document.getElementById("bar-fatigue-risk");
  const valFat = document.getElementById("val-fatigue-risk-pct");
  const stratName = document.getElementById("val-intervention-strategy-name");
  const promptBody = document.getElementById("txt-adaptive-system-prompt-body");
  const toneWarmth = document.getElementById("val-tone-warmth");
  const toneSpeed = document.getElementById("val-tone-speed");

  const depPct = Math.round(data.depression_risk_score * 100);
  const anxPct = Math.round(data.anxiety_stress_score * 100);
  const fatPct = Math.round(data.fatigue_burnout_score * 100);

  if (barDep) barDep.style.width = `${depPct}%`;
  if (valDep) valDep.innerText = `${depPct}%`;
  if (barAnx) barAnx.style.width = `${anxPct}%`;
  if (valAnx) valAnx.innerText = `${anxPct}%`;
  if (barFat) barFat.style.width = `${fatPct}%`;
  if (valFat) valFat.innerText = `${fatPct}%`;

  if (badgeMood) {
    badgeMood.innerText = data.detected_mood.toUpperCase();
    badgeMood.className = `badge-tag mood-badge ${data.detected_mood}`;
  }

  if (stratName) stratName.innerText = data.intervention_strategy_id;
  if (promptBody) promptBody.innerText = data.system_prompt_adaptation;
  if (toneWarmth) toneWarmth.innerText = data.voice_tone_guidance?.warmth_level || "Standard";
  if (toneSpeed) toneSpeed.innerText = `${data.voice_tone_guidance?.speed || 1.0}x`;
}

async function updateLiveBiometricPill() {
  const bpmLabel = document.getElementById("val-affective-bpm");
  const hrvLabel = document.getElementById("val-affective-hrv");
  try {
    const res = await fetch("/api/v1/wearables/state");
    if (res.ok) {
      const data = await res.json();
      const v = data?.latest_vitals;
      if (bpmLabel) bpmLabel.innerText = v?.heart_rate_bpm ? `${Math.round(v.heart_rate_bpm)} BPM` : "— BPM";
      if (hrvLabel) hrvLabel.innerText = v?.hrv_rmssd_ms ? `${v.hrv_rmssd_ms.toFixed(1)} ms` : "— ms";
      return;
    }
  } catch (_) {}
  if (bpmLabel) bpmLabel.innerText = "— BPM";
  if (hrvLabel) hrvLabel.innerText = "— ms";
} BPM`;
  }
  if (hrvLabel) {
    const jitterHrv = (41.0 + (Math.random() * 3)).toFixed(1);
    hrvLabel.innerText = `${jitterHrv} ms`;
  }
}

function startRppgPulseWaveAnimation(canvas) {
  const ctx = canvas.getContext("2d");
  let t = 0;

  function draw() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#050811";
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "rgba(239, 68, 68, 0.15)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();

    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let x = 0; x < w; x++) {
      const phase = (x * 0.05) - t;
      const beat = Math.exp(-Math.pow((phase % (Math.PI * 2)) - Math.PI, 2) * 4) * 35;
      const dicrotic = Math.exp(-Math.pow((phase % (Math.PI * 2)) - (Math.PI * 1.35), 2) * 8) * 14;
      const y = (h / 2) + beat - dicrotic;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    t += 0.07;
    requestAnimationFrame(draw);
  }

  requestAnimationFrame(draw);
}
