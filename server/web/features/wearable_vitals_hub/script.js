export async function initWearableVitalsHub() {
  const currentLang = localStorage.getItem("nuxiva_ui_lang") || "it";
  await applyWearableI18n(currentLang);

  window.addEventListener("nuxiva-language-changed", async (e) => {
    if (e.detail?.lang) {
      await applyWearableI18n(e.detail.lang);
    }
  });

  const canvasEcg = document.getElementById("canvas-wearable-ecg");
  if (canvasEcg) {
    startWearableEcgAnimation(canvasEcg);
  }

  const btnSync = document.getElementById("btn-sync-wearables");
  btnSync?.addEventListener("click", async () => {
    await refreshWearableState();
  });

  await refreshWearableState();

  setInterval(async () => {
    await refreshWearableState();
  }, 3000);
}

async function applyWearableI18n(lang) {
  try {
    const res = await fetch("/static/features/wearable_vitals_hub/i18n.json");
    if (!res.ok) return;
    const dict = await res.json();
    const strings = dict[lang] || dict["it"] || {};

    document.querySelectorAll("#deck-wearables-vitals [data-i18n]").forEach(el => {
      const k = el.getAttribute("data-i18n");
      if (strings[k]) {
        el.innerText = strings[k];
      }
    });
  } catch (err) {
    console.error(err);
  }
}

async function refreshWearableState() {
  const btn = document.getElementById("btn-sync-wearables");
  if (btn) btn.innerText = "⏳ Sincronizzazione BLE / Cloud...";

  try {
    const res = await fetch("/api/v1/wearables/state");
    if (!res.ok) return;
    const data = await res.json();

    renderWearablesData(data);
  } catch (err) {
    console.error(err);
  } finally {
    if (btn) btn.innerText = "⚡ Sincronizza Dispositivi Indossabili";
  }
}

function renderWearablesData(state) {
  const bpm = document.getElementById("val-wearable-bpm");
  const spo2 = document.getElementById("val-wearable-spo2");
  const hrv = document.getElementById("val-wearable-hrv");
  const temp = document.getElementById("val-wearable-temp");
  const steps = document.getElementById("val-wearable-steps");
  const cals = document.getElementById("val-wearable-calories");
  const resp = document.getElementById("val-wearable-resp");
  const batt = document.getElementById("val-wearable-battery");

  const v = state.latest_vitals;
  if (v) {
    if (bpm && v.heart_rate_bpm) bpm.innerText = `${Math.round(v.heart_rate_bpm)} BPM`;
    if (spo2 && v.spo2_percentage) spo2.innerText = `${v.spo2_percentage}%`;
    if (hrv && v.hrv_rmssd_ms) hrv.innerText = `${v.hrv_rmssd_ms.toFixed(1)} ms`;
    if (temp && v.skin_temperature_celsius) temp.innerText = `${v.skin_temperature_celsius.toFixed(1)}°C`;
    if (steps && v.steps_today) steps.innerText = v.steps_today.toLocaleString();
    if (cals && v.calories_burned_kcal) cals.innerText = `${Math.round(v.calories_burned_kcal)} kcal`;
    if (resp && v.respiratory_rate_rpm) resp.innerText = `${v.respiratory_rate_rpm.toFixed(1)} rpm`;
    if (batt && v.battery_level_percentage) batt.innerText = `${v.battery_level_percentage}%`;
  }

  const weight = document.getElementById("val-scale-weight");
  const bmi = document.getElementById("val-scale-bmi");
  const fat = document.getElementById("val-scale-fat");
  const barFat = document.getElementById("bar-scale-fat");
  const muscle = document.getElementById("val-scale-muscle");
  const barMuscle = document.getElementById("bar-scale-muscle");
  const water = document.getElementById("val-scale-water");
  const barWater = document.getElementById("bar-scale-water");
  const metaAge = document.getElementById("val-scale-meta-age");

  const b = state.latest_body_metrics;
  if (b) {
    if (weight) weight.innerText = b.weight_kg.toFixed(1);
    if (bmi) bmi.innerText = b.bmi.toFixed(1);
    if (fat && b.body_fat_percentage) {
      fat.innerText = `${b.body_fat_percentage.toFixed(1)}%`;
      if (barFat) barFat.style.width = `${b.body_fat_percentage}%`;
    }
    if (muscle && b.muscle_mass_kg) {
      muscle.innerText = `${b.muscle_mass_kg.toFixed(1)} kg`;
      if (barMuscle) barMuscle.style.width = `${(b.muscle_mass_kg / b.weight_kg) * 100}%`;
    }
    if (water && b.water_percentage) {
      water.innerText = `${b.water_percentage.toFixed(1)}%`;
      if (barWater) barWater.style.width = `${b.water_percentage}%`;
    }
    if (metaAge && b.metabolic_age_years) {
      metaAge.innerText = `${b.metabolic_age_years} Anni`;
    }
  }

  const devList = document.getElementById("list-wearable-devices");
  if (devList && state.devices) {
    devList.innerHTML = "";
    state.devices.forEach(d => {
      const pill = document.createElement("div");
      pill.className = `hardware-pill ${d.status === "connected" ? "online" : ""}`;
      pill.innerHTML = `<span>●</span> <span>${d.name} (${d.protocol})</span>`;
      devList.appendChild(pill);
    });
  }
}
BPM`;
  }
  if (hrvLabel) {
    const nextHrv = (47.5 + (Math.random() * 2)).toFixed(1);
    hrvLabel.innerText = `${nextHrv} ms`;
  }
}

function startWearableEcgAnimation(canvas) {
  const ctx = canvas.getContext("2d");
  let t = 0;

  function draw() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#050811";
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "rgba(56, 189, 248, 0.15)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();

    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let x = 0; x < w; x++) {
      const p = (x * 0.05) - t;
      const mod = (p % (Math.PI * 2)) - Math.PI;
      let wave = 0;

      if (Math.abs(mod) < 0.25) {
        wave = -Math.sin(mod * 12.5) * 28;
      } else if (Math.abs(mod - 0.45) < 0.4) {
        wave = Math.sin((mod - 0.45) * 7.8) * 8;
      }

      const y = (h / 2) + wave;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    t += 0.065;
    requestAnimationFrame(draw);
  }

  requestAnimationFrame(draw);
}
