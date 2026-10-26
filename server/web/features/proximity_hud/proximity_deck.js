import { setActiveChatbotUser } from "../chatbot_mesh/chatbot_deck.js";
import { visionController } from "./vision_controller.js";

export function initProximityHudDeck() {
document.getElementById("btn-toggle-presence-away")?.addEventListener("click", () => {
    fetch("/api/v1/presence/toggle-mock?approaching=false&verified=false", { method: "POST" })
      .then(() => refreshProximityHud());
  });

  // Inizializzazione Vision Controller (Mani & Occhi)
  const videoEl = document.getElementById("vision-webcam-video");
  const canvasEl = document.getElementById("vision-webcam-canvas");
  const btnStartCam = document.getElementById("btn-toggle-vision-camera");
  const camStatusBadge = document.getElementById("vision-camera-status-badge");

  if (videoEl && canvasEl) {
    visionController.init(videoEl, canvasEl);

    // Auto-avvio o avvio su click
    btnStartCam?.addEventListener("click", async () => {
      if (visionController.isRunning) {
        visionController.stopCamera();
        if (btnStartCam) {
          btnStartCam.innerText = "📹 Avvia Telecamera Visione (Mani & Occhi)";
          btnStartCam.classList.remove("danger");
        }
        if (camStatusBadge) {
          camStatusBadge.innerText = "Disattiva";
          camStatusBadge.style.color = "var(--text-muted)";
        }
      } else {
        if (btnStartCam) btnStartCam.innerText = "⏳ Inizializzazione Ottica...";
        const ok = await visionController.startCamera();
        if (btnStartCam) {
          btnStartCam.innerText = "🛑 Arresta Telecamera Visione";
          btnStartCam.classList.add("danger");
        }
        if (camStatusBadge) {
          camStatusBadge.innerText = ok ? "Webcam Attiva (Zero-Latency)" : "Simulazione Cyber Attiva";
          camStatusBadge.style.color = "#34d399";
        }
      }
    });

    // Checkbox opzioni
    document.getElementById("chk-enable-hands-gesture")?.addEventListener("change", (e) => {
      visionController.config.handsEnabled = e.target.checked;
    });
    document.getElementById("chk-enable-eye-gaze")?.addEventListener("change", (e) => {
      visionController.config.gazeEnabled = e.target.checked;
    });
    document.getElementById("chk-audio-feedback")?.addEventListener("change", (e) => {
      visionController.config.audioFeedback = e.target.checked;
    });
    document.getElementById("range-gesture-sensitivity")?.addEventListener("input", (e) => {
      visionController.config.sensitivity = parseFloat(e.target.value);
    });

    // Pulsanti di trigger rapido gesti (Test Banco Interattivo)
    document.getElementById("btn-test-gesture-swipe-l")?.addEventListener("click", () => {
      visionController.triggerGesture("swipe_left");
    });
    document.getElementById("btn-test-gesture-swipe-r")?.addEventListener("click", () => {
      visionController.triggerGesture("swipe_right");
    });
    document.getElementById("btn-test-gesture-fist")?.addEventListener("click", () => {
      visionController.triggerGesture("fist");
    });
    document.getElementById("btn-test-gesture-palm")?.addEventListener("click", () => {
      visionController.triggerGesture("open_palm");
    });
    document.getElementById("btn-test-gesture-thumb")?.addEventListener("click", () => {
      visionController.triggerGesture("thumbs_up");
    });
    document.getElementById("btn-test-gesture-peace")?.addEventListener("click", () => {
      visionController.triggerGesture("peace_v");
    });

    // Ascolto eventi di riconoscimento per aggiornare la UI in tempo reale
    window.addEventListener("nuxiva-vision-gesture", (e) => {
      const g = e.detail?.gesture || "none";
      const gestureBadge = document.getElementById("hud-gesture-current-label");
      if (gestureBadge) {
        gestureBadge.innerText = g.toUpperCase();
        gestureBadge.style.color = "#00f0ff";
        setTimeout(() => {
          if (gestureBadge) gestureBadge.style.color = "#fff";
        }, 1500);
      }
      refreshProximityHud();
    });

    // Monitoraggio periodico stato vista per indicatori dashboard
    setInterval(() => {
      if (visionController.isRunning) {
        const gazeLabel = document.getElementById("hud-gaze-state-label");
        const attentionBar = document.getElementById("hud-attention-bar-fill");
        const attentionVal = document.getElementById("hud-attention-percentage-val");

        if (gazeLabel) {
          const state = visionController.state;
          if (state.isLookingAtScreen) {
            gazeLabel.innerText = "🎯 Schermo (Focalizzato)";
            gazeLabel.style.color = "#34d399";
          } else {
            gazeLabel.innerText = "⚠️ Distolto (" + state.gazeDirection + ")";
            gazeLabel.style.color = "#f43f5e";
          }
        }

        if (attentionBar && attentionVal) {
          const pct = Math.round(visionController.state.attentionScore * 100);
          attentionBar.style.width = `${pct}%`;
          attentionVal.innerText = `${pct}%`;
          if (pct > 70) {
            attentionBar.style.background = "linear-gradient(90deg, #10b981, #00f0ff)";
          } else {
            attentionBar.style.background = "linear-gradient(90deg, #f43f5e, #fbbf24)";
          }
        }
      }
    }, 400);
  }
}

export async function refreshProximityHud() {
  try {
    const res = await fetch("/api/v1/presence/hud/projects");
    const data = await res.json();
    const statusText = document.getElementById("hud-presence-text");
    const nameText = document.getElementById("hud-detected-user-name");
    const detailsText = document.getElementById("hud-detection-details");
    const badge = document.getElementById("hud-biometric-badge");
    const list = document.getElementById("hud-projects-projected-list");

    if (data.unlocked) {
      if (statusText) statusText.innerText = `WEBCAM: ${data.detected_user} (Sbloccato)`;
      if (nameText) nameText.innerText = `${data.detected_user} (Autenticato Biometricamente)`;
      if (detailsText) detailsText.innerText = `Confidenza: ${Math.round((data.confidence || 0.95) * 100)}% | Sblocco Progetti & Controllo Attivo`;
      if (badge) { badge.innerText = "Sbloccato"; badge.style.color = "#34d399"; }

      if (data.detected_user) {
        setActiveChatbotUser(data.detected_user);
      }

      if (list) {
        list.innerHTML = "";
        (data.projects || []).forEach(p => {
          const item = document.createElement("div");
          item.className = "tactical-card";
          item.style.padding = "0.75rem";
          item.innerHTML = `
            <div style="display:flex; justify-content:space-between;">
              <strong style="color:#fff;">${p.name}</strong>
              <span style="color:var(--cyan-glow);">${Math.round(p.completion_percentage || 0)}%</span>
            </div>
            <div class="progress-container" style="height:6px; margin-top:6px;">
              <div class="progress-bar-fill" style="width:${Math.round(p.completion_percentage || 0)}%;"></div>
            </div>
          `;
          list.appendChild(item);
        });
      }
    } else {
      if (statusText) statusText.innerText = "WEBCAM: In attesa utente (Privacy)";
      if (nameText) nameText.innerText = "Schermo Protetto (Utente Non Rilevato)";
      if (detailsText) detailsText.innerText = "Inquadra il volto o avvicinati alla webcam per sbloccare i tuoi progetti.";
      if (badge) { badge.innerText = "Oscurato"; badge.style.color = "var(--rose-glow)"; }
      if (list) list.innerHTML = "<p style='color:var(--text-muted); font-size:0.85rem;'>Dati sensibili oscurati per privacy.</p>";
    }
  } catch (e) {}
}
