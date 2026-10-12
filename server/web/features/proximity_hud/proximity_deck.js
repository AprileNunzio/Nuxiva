import { setActiveChatbotUser } from "../chatbot_mesh/chatbot_deck.js";

export function initProximityHudDeck() {
  document.getElementById("btn-toggle-presence-near")?.addEventListener("click", () => {
    fetch("/api/v1/presence/toggle-mock?approaching=true&verified=true", { method: "POST" })
      .then(() => refreshProximityHud());
  });
  document.getElementById("btn-toggle-presence-away")?.addEventListener("click", () => {
    fetch("/api/v1/presence/toggle-mock?approaching=false&verified=false", { method: "POST" })
      .then(() => refreshProximityHud());
  });
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
      if (nameText) nameText.innerText = `${data.detected_user} (Autenticato)`;
      if (detailsText) detailsText.innerText = `Confidenza: ${Math.round((data.confidence || 0.95) * 100)}% | Sblocco Progetti Attivo`;
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
      if (detailsText) detailsText.innerText = "Avvicinati alla webcam per sbloccare i tuoi progetti.";
      if (badge) { badge.innerText = "Oscurato"; badge.style.color = "var(--rose-glow)"; }
      if (list) list.innerHTML = "<p style='color:var(--text-muted); font-size:0.85rem;'>Dati sensibili oscurati per privacy.</p>";
    }
  } catch (e) {}
}
