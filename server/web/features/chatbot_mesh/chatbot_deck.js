export let activeChatbotUserId = "user_primary";
export let activeChatbotAgentId = "chief_supervisor";
export let chatbotAvailableWidgetsList = [];

export async function initChatbotMeshDeck() {
  const userSelector = document.getElementById("chatbot-user-selector");
  if (userSelector) {
    userSelector.value = activeChatbotUserId;
    userSelector.addEventListener("change", (e) => {
      activeChatbotUserId = e.target.value;
      const titleSpan = document.getElementById("chatbot-active-user-title");
      if (titleSpan) {
        titleSpan.textContent = userSelector.options[userSelector.selectedIndex].text.split("(")[0].trim() || activeChatbotUserId;
      }
      loadUserAgentPersonalization();
      loadChatbotHistory();
    });
  }

  document.getElementById("btn-save-chatbot-persona")?.addEventListener("click", saveUserAgentPersonalization);
  document.getElementById("btn-chatbot-send")?.addEventListener("click", sendChatbotMessage);
  document.getElementById("chatbot-message-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChatbotMessage();
  });
  document.getElementById("btn-clear-chat-history")?.addEventListener("click", () => {
    const stream = document.getElementById("chatbot-messages-stream");
    if (stream) stream.innerHTML = `<div style="text-align:center; color:var(--text-muted); font-size:0.75rem; padding:1rem;">Cronologia locale ripulita.</div>`;
    const wBox = document.getElementById("chatbot-rendered-widgets");
    if (wBox) wBox.innerHTML = "";
  });

  await loadChatbotWidgetsCatalog();
  await loadChatbotAgentsList();
  await loadUserAgentPersonalization();
  await loadChatbotHistory();
}

export function setActiveChatbotUser(userId) {
  activeChatbotUserId = userId;
  const userSelector = document.getElementById("chatbot-user-selector");
  if (userSelector) {
    let exists = Array.from(userSelector.options).some(opt => opt.value === userId);
    if (!exists) {
      const newOpt = document.createElement("option");
      newOpt.value = userId;
      newOpt.textContent = `👤 ${userId}`;
      userSelector.appendChild(newOpt);
    }
    userSelector.value = userId;
    const titleSpan = document.getElementById("chatbot-active-user-title");
    if (titleSpan) {
      titleSpan.textContent = userSelector.options[userSelector.selectedIndex]?.text?.split("(")[0]?.trim() || userId;
    }
  }
  loadUserAgentPersonalization();
  loadChatbotHistory();
}

async function loadChatbotWidgetsCatalog() {
  try {
    const res = await fetch("/api/v1/chatbot/widgets/catalog");
    const data = await res.json();
    chatbotAvailableWidgetsList = data.widgets || [];
  } catch (e) {}
}

async function loadChatbotAgentsList() {
  try {
    const res = await fetch("/api/v1/chatbot/agents");
    const data = await res.json();
    const container = document.getElementById("chatbot-agents-list");
    if (!container || !data.agents) return;

    container.innerHTML = "";
    data.agents.forEach((agent, index) => {
      const card = document.createElement("div");
      card.className = "agent-item-card" + (agent.agent_id === activeChatbotAgentId ? " active" : "");
      card.style.padding = "0.5rem 0.75rem";
      card.style.display = "flex";
      card.style.justifyContent = "space-between";
      card.style.alignItems = "center";
      card.style.cursor = "pointer";

      card.innerHTML = `
        <div>
          <strong style="color:var(--cyan-glow); font-size:0.85rem;">${agent.name}</strong>
          <span style="display:block; font-size:0.7rem; color:var(--text-muted);">${agent.role_category}</span>
        </div>
        <span class="badge-tag" style="font-size:0.65rem;">Chatbot</span>
      `;

      card.addEventListener("click", () => {
        container.querySelectorAll(".agent-item-card").forEach(c => c.classList.remove("active"));
        card.classList.add("active");
        activeChatbotAgentId = agent.agent_id;
        const nameHeader = document.getElementById("chatbot-active-agent-name");
        if (nameHeader) nameHeader.textContent = agent.name;
        loadUserAgentPersonalization();
        loadChatbotHistory();
      });

      container.appendChild(card);

      if (index === 0 && !activeChatbotAgentId) {
        activeChatbotAgentId = agent.agent_id;
      }
    });

    const activeObj = data.agents.find(a => a.agent_id === activeChatbotAgentId);
    if (activeObj) {
      const nameHeader = document.getElementById("chatbot-active-agent-name");
      if (nameHeader) nameHeader.textContent = activeObj.name;
    }
  } catch (e) {}
}

export async function loadUserAgentPersonalization() {
  try {
    const res = await fetch(`/api/v1/chatbot/users/${activeChatbotUserId}/agents/${activeChatbotAgentId}/config`);
    const data = await res.json();
    const c = data.config || {};

    const nickInput = document.getElementById("chatbot-input-nickname");
    if (nickInput) nickInput.value = c.custom_nickname || "";

    const toneSelect = document.getElementById("chatbot-select-tone");
    if (toneSelect && c.preferred_tone) {
      toneSelect.value = c.preferred_tone;
    }
    updateToneLivePreview(toneSelect?.value || "friendly", nickInput?.value || "Assistente");

    toneSelect?.addEventListener("change", (e) => {
      updateToneLivePreview(e.target.value, nickInput?.value || "Assistente");
    });
    nickInput?.addEventListener("input", (e) => {
      updateToneLivePreview(toneSelect?.value || "friendly", e.target.value || "Assistente");
    });

    const promptArea = document.getElementById("chatbot-user-prompt");
    if (promptArea) promptArea.value = c.custom_persona_prompt || "";

    const knowArea = document.getElementById("chatbot-user-knowledge");
    if (knowArea) knowArea.value = c.custom_knowledge_notes || "";

    const wContainer = document.getElementById("chatbot-widgets-checkboxes");
    if (wContainer) {
      wContainer.innerHTML = "";
      const enabledWidgets = new Set(c.enabled_widgets || []);
      chatbotAvailableWidgetsList.forEach(w => {
        const isChecked = enabledWidgets.has(w.id);
        const div = document.createElement("label");
        div.style.display = "flex";
        div.style.alignItems = "center";
        div.style.gap = "0.3rem";
        div.style.fontSize = "0.72rem";
        div.style.cursor = "pointer";
        div.innerHTML = `
          <input type="checkbox" value="${w.id}" ${isChecked ? "checked" : ""} class="chatbot-widget-chk">
          <span>${w.icon} ${w.name}</span>
        `;
        wContainer.appendChild(div);
      });
    }

    const tContainer = document.getElementById("chatbot-tools-checkboxes");
    if (tContainer) {
      tContainer.innerHTML = "";
      let availableTools = [];
      try {
        const toolsRes = await fetch("/api/v1/chatbot/tools/catalog");
        const toolsData = await toolsRes.json();
        availableTools = toolsData.tools || [];
      } catch (e) {}

      const allowedTools = new Set(c.allowed_tools || []);
      availableTools.forEach(tool => {
        const isChecked = allowedTools.has(tool.id);
        const div = document.createElement("label");
        div.style.display = "flex";
        div.style.alignItems = "center";
        div.style.gap = "0.4rem";
        div.style.fontSize = "0.75rem";
        div.style.cursor = "pointer";
        div.innerHTML = `
          <input type="checkbox" value="${tool.id}" ${isChecked ? "checked" : ""} class="chatbot-tool-chk">
          <span>${tool.icon || '🛠️'} ${tool.name}</span>
        `;
        tContainer.appendChild(div);
      });
    }
  } catch (e) {}
}

async function saveUserAgentPersonalization() {
  const btn = document.getElementById("btn-save-chatbot-persona");
  const originalText = btn ? btn.textContent : "Salva";
  if (btn) btn.textContent = "⏳ Salvataggio...";

  const nickInput = document.getElementById("chatbot-input-nickname");
  const toneSelect = document.getElementById("chatbot-select-tone");
  const promptArea = document.getElementById("chatbot-user-prompt");
  const knowArea = document.getElementById("chatbot-user-knowledge");

  const selectedWidgets = [];
  document.querySelectorAll(".chatbot-widget-chk:checked").forEach(chk => {
    selectedWidgets.push(chk.value);
  });

  const selectedTools = [];
  document.querySelectorAll(".chatbot-tool-chk:checked").forEach(chk => {
    selectedTools.push(chk.value);
  });

  const payload = {
    user_id: activeChatbotUserId,
    agent_id: activeChatbotAgentId,
    custom_nickname: nickInput?.value.trim() || "",
    preferred_tone: toneSelect?.value || "friendly",
    custom_persona_prompt: promptArea?.value.trim() || "",
    custom_knowledge_notes: knowArea?.value.trim() || "",
    allowed_tools: selectedTools,
    enabled_widgets: selectedWidgets,
    preferred_language: localStorage.getItem("nuxiva_ui_lang") || "it",
  };

  try {
    await fetch(`/api/v1/chatbot/users/${activeChatbotUserId}/agents/${activeChatbotAgentId}/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (btn) {
      btn.textContent = "✅ Salvato!";
      btn.style.background = "linear-gradient(90deg, #10b981, #059669)";
      setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = "";
      }, 2000);
    }
  } catch (e) {
    if (btn) btn.textContent = "❌ Errore";
  }
}

export async function loadChatbotHistory() {
  try {
    const res = await fetch(`/api/v1/chatbot/users/${activeChatbotUserId}/agents/${activeChatbotAgentId}/history`);
    const data = await res.json();
    const stream = document.getElementById("chatbot-messages-stream");
    if (!stream) return;

    stream.innerHTML = "";
    const history = data.history || [];
    if (history.length === 0) {
      stream.innerHTML = `<div style="text-align:center; color:var(--text-muted); font-size:0.75rem; padding:1.5rem;">Nessun messaggio precedente. Avvia la conversazione con questo chatbot!</div>`;
      return;
    }

    history.forEach(item => {
      appendChatMessageBubble(item.sender, item.text, item.tools_used);
    });
    stream.scrollTop = stream.scrollHeight;
  } catch (e) {}
}

function appendChatMessageBubble(sender, text, toolsUsed = []) {
  const stream = document.getElementById("chatbot-messages-stream");
  if (!stream) return;

  const isUser = sender.startsWith("user:");
  const bubble = document.createElement("div");
  bubble.style.maxWidth = "80%";
  bubble.style.alignSelf = isUser ? "flex-end" : "flex-start";
  bubble.style.padding = "0.6rem 0.8rem";
  bubble.style.borderRadius = isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px";
  bubble.style.background = isUser ? "rgba(0, 240, 255, 0.12)" : "rgba(255, 255, 255, 0.05)";
  bubble.style.border = isUser ? "1px solid rgba(0, 240, 255, 0.4)" : "1px solid var(--border-glow)";
  bubble.style.fontSize = "0.82rem";
  bubble.style.lineHeight = "1.4";

  let toolsBadge = "";
  if (toolsUsed && toolsUsed.length > 0) {
    toolsBadge = `<div style="margin-top:4px; font-size:0.68rem; color:var(--amber-glow); font-family:var(--font-mono);">🛠️ Tool: ${toolsUsed.join(", ")}</div>`;
  }

  bubble.innerHTML = `
    <div style="font-size:0.68rem; color:var(--text-muted); margin-bottom:2px; font-family:var(--font-mono);">${sender}</div>
    <div style="white-space:pre-wrap;">${escapeHtml(text)}</div>
    ${toolsBadge}
  `;

  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
}

async function sendChatbotMessage() {
  const input = document.getElementById("chatbot-message-input");
  const text = input?.value.trim();
  if (!text) return;

  input.value = "";
  appendChatMessageBubble(`user:${activeChatbotUserId}`, text);

  try {
    const res = await fetch("/api/v1/chatbot/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: activeChatbotUserId,
        agent_id: activeChatbotAgentId,
        text: text,
      }),
    });
    const data = await res.json();
    const resp = data.response;
    if (!resp) return;

    appendChatMessageBubble(`agent:${activeChatbotAgentId}`, resp.reply_text, resp.tools_invoked?.map(t => t.tool));
    renderChatbotWidgets(resp.active_widgets || []);
  } catch (e) {
    appendChatMessageBubble(`system:error`, "Errore durante la comunicazione con il chatbot.");
  }
}

function renderChatbotWidgets(widgets) {
  const container = document.getElementById("chatbot-rendered-widgets");
  if (!container) return;

  container.innerHTML = "";
  widgets.forEach(w => {
    const card = document.createElement("div");
    card.className = "tactical-card";
    card.style.padding = "0.6rem 0.8rem";
    card.style.background = "rgba(0, 240, 255, 0.04)";
    card.style.borderColor = "var(--border-glow)";

    if (w.widget_type === "cad_viewer") {
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:var(--cyan-glow); font-size:0.82rem;">📐 ${w.title}</strong>
          <span class="badge-tag">DXF 3D</span>
        </div>
        <p style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">File: <code>${w.data.filename || 'cad.dxf'}</code> | Larghezza: ${w.data.width_mm || 180}mm x ${w.data.height_mm || 120}mm</p>
        <div style="margin-top:6px; display:flex; gap:0.5rem;">
          <button class="tactical-btn" style="padding:0.25rem 0.6rem; font-size:0.75rem;">Download .DXF</button>
          <button class="tactical-btn secondary" style="padding:0.25rem 0.6rem; font-size:0.75rem;">Visualizza Quote</button>
        </div>
      `;
    } else if (w.widget_type === "smart_switch") {
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:var(--cyan-glow); font-size:0.82rem;">💡 ${w.title}</strong>
          <span class="badge-tag" style="background:rgba(16,185,129,0.2); color:#34d399;">ATTIVO</span>
        </div>
        <p style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">Entita: <code>${w.data.entity_id}</code> (Utente: ${w.data.user})</p>
        <div style="margin-top:6px;">
          <button class="tactical-btn" style="padding:0.25rem 0.6rem; font-size:0.75rem;">Commuta Stato</button>
        </div>
      `;
    } else if (w.widget_type === "social_post_preview") {
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:var(--cyan-glow); font-size:0.82rem;">📱 ${w.title}</strong>
          <span class="badge-tag" style="background:rgba(236,72,153,0.2); color:#f472b6;">INSTAGRAM</span>
        </div>
        <p style="font-size:0.75rem; color:#fff; margin-top:4px; white-space:pre-wrap;">${w.data.post_content || w.data.caption || 'Bozza pronta'}</p>
        <div style="margin-top:6px; display:flex; gap:0.5rem;">
          <button class="tactical-btn" style="padding:0.25rem 0.6rem; font-size:0.75rem;">Copia Testo</button>
          <button class="tactical-btn secondary" style="padding:0.25rem 0.6rem; font-size:0.75rem;">Pianifica</button>
        </div>
      `;
    } else {
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:var(--cyan-glow); font-size:0.82rem;">⚡ ${w.title}</strong>
          <span class="badge-tag">${w.widget_type}</span>
        </div>
        <pre style="font-size:0.7rem; color:var(--text-muted); margin-top:4px; font-family:var(--font-mono);">${JSON.stringify(w.data, null, 2)}</pre>
      `;
    }

    container.appendChild(card);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function updateToneLivePreview(tone, nickname) {
  const previewBox = document.getElementById("chatbot-tone-live-preview");
  if (!previewBox) return;

  const nick = nickname || "Assistente";
  let previewText = "";

  switch (tone) {
    case "friendly":
      previewText = `"${nick}: Ciao! Che piacere rivederti. Ho preparato tutto per te, cosa facciamo di bello oggi?"`;
      break;
    case "formal":
      previewText = `"${nick}: Buon giorno. Tutti i moduli operativi sono allineati secondo le Sue direttive. Rimango a completa disposizione."`;
      break;
    case "concise":
      previewText = `"${nick}: Sistemi pronti. Task sincronizzati. Invia input."`;
      break;
    case "technical":
      previewText = `"${nick}: [Kernel OK | Latency <1ms | gRPC active]. Specificare parametri operativi o payload di esecuzione."`;
      break;
    case "kid_safe":
      previewText = `"${nick}: Ciao ciao! ✨ Sei pronto a scoprire una magia o imparare qualcosa di super divertente insieme?"`;
      break;
    case "poetic":
      previewText = `"${nick}: Come costellazioni nel silenzio digitale, i tuoi progetti attendono un soffio per prendere vita..."`;
      break;
    default:
      previewText = `"${nick}: Ciao! Sono a tua disposizione. Come posso aiutarti oggi?"`;
      break;
  }

  previewBox.textContent = previewText;
  previewBox.style.animation = "none";
  void previewBox.offsetWidth;
  previewBox.style.animation = "slideInUp 0.3s ease-out";
}
