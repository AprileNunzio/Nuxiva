export async function initUserPresenceVitals() {
  const currentLang = localStorage.getItem("nuxiva_ui_lang") || "it";
  await applyEmergencyI18n(currentLang);

  window.addEventListener("nuxiva-language-changed", async (e) => {
    if (e.detail?.lang) {
      await applyEmergencyI18n(e.detail.lang);
    }
  });

  const btnSimulate = document.getElementById("btn-simulate-cardiac-arrest");
  const btnRestore = document.getElementById("btn-restore-normal-vitals");

  btnSimulate?.addEventListener("click", async () => {
    await simulateVitalsState(0.0, 70.0, "CARDIAC_ARREST");
  });

  btnRestore?.addEventListener("click", async () => {
    await simulateVitalsState(72.0, 98.0, "NORMAL");
  });

  await fetchEmergencyStatus();
  setInterval(async () => {
    await fetchEmergencyStatus();
  }, 4000);
}

async function applyEmergencyI18n(lang) {
  try {
    const res = await fetch("/static/features/user_presence_vitals/i18n.json");
    if (!res.ok) return;
    const dict = await res.json();
    const strings = dict[lang] || dict["it"] || {};

    document.querySelectorAll("#deck-emergency-vitals [data-i18n]").forEach(el => {
      const k = el.getAttribute("data-i18n");
      if (strings[k]) {
        el.innerText = strings[k];
      }
    });
  } catch (err) {
    console.error(err);
  }
}

async function fetchEmergencyStatus() {
  try {
    const res = await fetch("/api/v1/emergency-presence/status");
    if (!res.ok) return;
    const data = await res.json();
    renderEmergencyUi(data);
  } catch (err) {
    console.error(err);
  }
}

async function simulateVitalsState(bpm, spo2, stateName) {
  try {
    const payload = {
      user_id: "owner",
      vitals: {
        device_id: "fitbit_edge_primary",
        user_id: "owner",
        heart_rate_bpm: bpm,
        spo2_percentage: spo2,
        stress_level: 12.0,
        body_temperature_celsius: 36.6,
        source_protocol: "fitbit_os_rest"
      }
    };

    const res = await fetch("/api/v1/emergency-presence/report-vitals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      await fetchEmergencyStatus();
    }
  } catch (err) {
    console.error(err);
  }
}

function renderEmergencyUi(data) {
  const profile = data.user_profile;
  const banner = document.getElementById("banner-critical-alarm");
  const bannerReason = document.getElementById("txt-alarm-banner-reason");
  const statusTxt = document.getElementById("txt-current-physiological-status");
  const contactsContainer = document.getElementById("list-emergency-contacts");

  if (profile) {
    const nameEl = document.getElementById("txt-emergency-user-name");
    const idEl = document.getElementById("txt-emergency-user-id");
    if (nameEl) nameEl.innerText = `${profile.full_name} (${profile.role || "Admin"})`;
    if (idEl) idEl.innerText = profile.user_id;

    if (contactsContainer && profile.emergency_contacts) {
      contactsContainer.innerHTML = profile.emergency_contacts.map(c => `
        <div class="contact-item-row">
          <div class="contact-item-left">
            <span class="contact-item-name">${c.name}</span>
            <span class="contact-item-role">${c.relationship} &bull; ${c.phone_number}</span>
          </div>
          <span class="contact-item-channels">${c.notification_channels.join(" + ")}</span>
        </div>
      `).join("");
    }
  }

  const recentAlerts = data.recent_alerts || [];
  const activeCriticalAlert = recentAlerts.find(a => a.severity === "CRITICAL");

  if (activeCriticalAlert && banner) {
    banner.style.display = "flex";
    if (bannerReason) {
      bannerReason.innerText = `${activeCriticalAlert.condition_type}: ${activeCriticalAlert.description}`;
    }
    if (statusTxt) {
      statusTxt.innerText = "ALLARME CRITICO IN CORSO";
      statusTxt.style.color = "#ef4444";
    }
  } else {
    if (banner) banner.style.display = "none";
    if (statusTxt) {
      statusTxt.innerText = "NORMALE & MONITORATO IN TEMPO REALE";
      statusTxt.style.color = "#34d399";
    }
  }
}
