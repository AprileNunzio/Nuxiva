import { initProjectsDeck, refreshActiveProject, loadProjectsList } from "./features/war_room/war_room_deck.js";
import { initChatbotMeshDeck } from "./features/chatbot_mesh/chatbot_deck.js";
import { initProximityHudDeck, refreshProximityHud } from "./features/proximity_hud/proximity_deck.js";
import { initAdminWizard } from "./features/onboarding/wizard.js";
import { initMultimodalSurveillance } from "./features/multimodal_surveillance/script.js";
import { initHumanAffectiveEngine } from "./features/human_affective_engine/script.js";
import { initWearableVitalsHub } from "./features/wearable_vitals_hub/script.js";
import { initUserPresenceVitals } from "./features/user_presence_vitals/script.js";
import { applyDomTranslations } from "./shared/i18n/dom_translator.js";

let currentSelectedAgentId = "windows_system_agent";

document.addEventListener("DOMContentLoaded", () => {
  initI18n();
  initDeckNavigation();
  initProjectsDeck();
  initCognitiveFlowDeck();
  initAgentVaultDeck();
  initRbacDeck();
  initProximityHudDeck();
  initCadMediaDeck();
  initTelemetryDeck();
  initChatbotMeshDeck();
  initMultimodalSurveillance();
  initHumanAffectiveEngine();
  initWearableVitalsHub();
  initUserPresenceVitals();
  initAdminWizard();
  initGlobalCommandBar();

  setInterval(() => {
    refreshActiveProject();
    refreshProximityHud();
  }, 4000);
});

function initDeckNavigation() {
  const tabs = document.querySelectorAll(".plancia-tab-btn");
  const decks = document.querySelectorAll(".plancia-section");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      decks.forEach(d => d.classList.remove("active"));

      tab.classList.add("active");
      const targetDeckId = tab.getAttribute("data-deck");
      const targetDeck = document.getElementById(targetDeckId);
      if (targetDeck) {
        targetDeck.classList.add("active");
        if (targetDeckId === "deck-cognitive-flow" && window.mermaid) {
          try { window.mermaid.init(undefined, "#mermaid-render-target"); } catch (e) {}
        }
      }
    });
  });
}

async function initCognitiveFlowDeck() {
  try {
    const res = await fetch("/api/v1/cognitive/flow");
    const data = await res.json();
    const container = document.getElementById("cognitive-flow-nodes-list");
    if (!container || !data || !data.nodes) return;

    container.innerHTML = "";
    data.nodes.forEach(n => {
      const card = document.createElement("div");
      card.className = "flow-node-item";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="font-size:0.9rem; color:#fff;">${n.n}</strong>
          <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">${n.k}</span>
        </div>
        <p style="font-size:0.8rem; color:var(--text-main); margin-top:4px;">${n.d || ""}</p>
        <div class="node-meta-badges">
          ${n.agent ? `<span class="badge-tag agent">🤖 Agente: ${n.agent}</span>` : ""}
          ${n.tool ? `<span class="badge-tag tool">🔧 Tool: ${n.tool}</span>` : ""}
          ${n.widget ? `<span class="badge-tag widget">🖥️ Widget: ${n.widget}</span>` : ""}
        </div>
      `;
      container.appendChild(card);
    });
  } catch (e) {}
}

async function initAgentVaultDeck() {
  document.getElementById("btn-save-agent-instructions")?.addEventListener("click", saveAgentInstructions);
  document.getElementById("btn-add-knowledge-modal")?.addEventListener("click", addKnowledgePrompt);

  try {
    const res = await fetch("/api/v1/agents/catalog");
    const data = await res.json();
    const listContainer = document.getElementById("agent-vault-selector-list");
    const recruitSelect = document.getElementById("select-recruit-agent");
    if (!listContainer) return;

    listContainer.innerHTML = "";
    if (recruitSelect) recruitSelect.innerHTML = "";

    (data.catalog || []).forEach(ag => {
      const div = document.createElement("div");
      div.style.padding = "0.6rem 0.8rem";
      div.style.borderRadius = "8px";
      div.style.cursor = "pointer";
      div.style.background = (ag.id === currentSelectedAgentId) ? "rgba(0,240,255,0.12)" : "rgba(255,255,255,0.03)";
      div.style.border = (ag.id === currentSelectedAgentId) ? "1px solid var(--cyan-glow)" : "1px solid rgba(255,255,255,0.06)";
      div.innerHTML = `
        <div style="font-weight:600; font-size:0.85rem; color:#fff;">${ag.name}</div>
        <div style="font-size:0.75rem; color:var(--text-dim);">${ag.role_category}</div>
      `;

      div.addEventListener("click", () => {
        currentSelectedAgentId = ag.id;
        initAgentVaultDeck();
        loadAgentWorkspace(ag.id);
      });
      listContainer.appendChild(div);

      if (recruitSelect) {
        const opt = document.createElement("option");
        opt.value = ag.id;
        opt.innerText = ag.name;
        recruitSelect.appendChild(opt);
      }
    });

    loadAgentWorkspace(currentSelectedAgentId);
  } catch (e) {}
}

async function loadAgentWorkspace(agentId) {
  try {
    const res = await fetch(`/api/v1/agents/${agentId}/workspace`);
    const data = await res.json();
    const ws = data.workspace;
    if (!ws) return;

    document.getElementById("vault-selected-agent-name").innerText = ws.profile.name;
    document.getElementById("vault-selected-agent-path").innerText = `Directory protetta: ${ws.workspace_dir}`;
    document.getElementById("vault-agent-instructions").value = ws.instructions || "";
    document.getElementById("vault-agent-model").value = ws.profile.preferred_model || "default";
    document.getElementById("vault-agent-temp").value = ws.profile.temperature || 0.7;
    document.getElementById("vault-agent-widget").value = ws.profile.primary_widget || "";

    const kList = document.getElementById("vault-knowledge-docs-list");
    kList.innerHTML = "";
    if (ws.knowledge_docs && ws.knowledge_docs.length > 0) {
      ws.knowledge_docs.forEach(k => {
        const item = document.createElement("div");
        item.style.padding = "0.4rem 0.6rem";
        item.style.background = "rgba(16,185,129,0.08)";
        item.style.border = "1px solid rgba(16,185,129,0.2)";
        item.style.borderRadius = "6px";
        item.style.fontSize = "0.8rem";
        item.innerHTML = `<strong>${k.filename}</strong> (${k.size_bytes} bytes) - Regola attiva`;
        kList.appendChild(item);
      });
    } else {
      kList.innerHTML = "<span style='font-size:0.75rem; color:var(--text-muted);'>Nessun documento caricato.</span>";
    }

    const tList = document.getElementById("vault-custom-tools-list");
    tList.innerHTML = "";
    const tools = ws.profile.custom_tools || [];
    if (tools.length > 0) {
      tools.forEach(t => {
        const item = document.createElement("div");
        item.style.padding = "0.4rem 0.6rem";
        item.style.background = "rgba(139,92,246,0.08)";
        item.style.border = "1px solid rgba(139,92,246,0.2)";
        item.style.borderRadius = "6px";
        item.style.fontSize = "0.8rem";
        item.innerHTML = `<strong>${t}</strong> (Script Python personalizzato)`;
        tList.appendChild(item);
      });
    } else {
      tList.innerHTML = "<span style='font-size:0.75rem; color:var(--text-muted);'>Nessun tool custom aggiunto.</span>";
    }
  } catch (e) {}
}

async function saveAgentInstructions() {
  const instructions = document.getElementById("vault-agent-instructions").value;
  try {
    await fetch(`/api/v1/agents/${currentSelectedAgentId}/workspace/instructions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instructions })
    });
    alert("Istruzioni salvate con successo.");
  } catch (e) {}
}

async function addKnowledgePrompt() {
  const filename = prompt("Nome del file:");
  if (!filename) return;
  const content = prompt("Contenuto della regola:");
  if (!content) return;

  try {
    await fetch(`/api/v1/agents/${currentSelectedAgentId}/workspace/knowledge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, content })
    });
    loadAgentWorkspace(currentSelectedAgentId);
  } catch (e) {}
}

async function initRbacDeck() {
  try {
    const [uRes, rRes] = await Promise.all([
      fetch("/api/v1/rbac/users"),
      fetch("/api/v1/rbac/roles")
    ]);
    const uData = await uRes.json();
    const rData = await rRes.json();

    const usersContainer = document.getElementById("rbac-users-list");
    usersContainer.innerHTML = "";
    (uData.users || []).forEach(u => {
      const row = document.createElement("div");
      row.style.padding = "0.75rem";
      row.style.background = "rgba(15,23,42,0.6)";
      row.style.border = "1px solid rgba(255,255,255,0.06)";
      row.style.borderRadius = "8px";
      row.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#fff;">${u.display_name} (@${u.username})</strong>
          <span class="badge-tag" style="background:rgba(0,240,255,0.15); color:var(--cyan-glow);">${u.role.toUpperCase()}</span>
        </div>
        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">
          Profilo: <b>${u.profile}</b> | Progetti assegnati: ${u.assigned_projects ? u.assigned_projects.length : 0}
        </div>
      `;
      usersContainer.appendChild(row);
    });

    const matrixContainer = document.getElementById("rbac-matrix-display");
    matrixContainer.innerHTML = "";
    for (const [role, perms] of Object.entries(rData.matrix || {})) {
      const item = document.createElement("div");
      item.style.padding = "0.6rem";
      item.style.background = "rgba(255,255,255,0.02)";
      item.style.borderRadius = "6px";
      item.style.border = "1px solid rgba(255,255,255,0.05)";
      item.innerHTML = `
        <strong style="color:var(--cyan-glow); font-size:0.85rem;">Ruolo: ${role}</strong>
        <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;">
          ${perms.map(p => `<span class="badge-tag" style="font-size:0.65rem;">${p}</span>`).join("")}
        </div>
      `;
      matrixContainer.appendChild(item);
    }
  } catch (e) {}
}

function initCadMediaDeck() {
  document.getElementById("btn-test-gen-dxf")?.addEventListener("click", async () => {
    try {
      await fetch("/api/v1/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "Genera disegno CAD flangia in DXF" })
      });
      loadCadFilesList();
    } catch (e) {}
  });

  document.getElementById("btn-gen-instagram-copy")?.addEventListener("click", async () => {
    const topic = document.getElementById("social-topic-input").value;
    const preview = document.getElementById("social-output-preview");
    preview.innerText = `Generazione copy per '${topic}'...`;
    try {
      const res = await fetch("/api/v1/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: `Scrivi un post Instagram su ${topic}` })
      });
      const data = await res.json();
      preview.innerText = data.speech_output || "Deliverable generato con successo.";
    } catch (e) {
      preview.innerText = "Errore nella generazione del post.";
    }
  });

  loadCadFilesList();
}

function loadCadFilesList() {
  const container = document.getElementById("cad-files-list");
  if (!container) return;
  container.innerHTML = `
    <div class="tactical-card" style="padding:0.75rem; border-left:3px solid var(--cyan-glow);">
      <strong>ingegneria_meccanica_flangia.dxf</strong>
      <p style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">Contorno 250x120mm con 3 forature d=12mm</p>
      <span class="badge-tag" style="background:rgba(0,240,255,0.15); color:var(--cyan-glow); margin-top:4px;">Disponibile in data/cad_exports/</span>
    </div>
  `;
}

async function initTelemetryDeck() {
  try {
    const res = await fetch("/api/v1/system/metrics");
    const data = await res.json();
    if (data) {
      document.getElementById("telem-cpu-val").innerText = `${Math.round(data.cpu_percent || 14)}%`;
      document.getElementById("telem-cpu-bar").style.width = `${Math.round(data.cpu_percent || 14)}%`;
      document.getElementById("telem-ram-val").innerText = `${Math.round(data.memory_percent || 38)}%`;
      document.getElementById("telem-ram-bar").style.width = `${Math.round(data.memory_percent || 38)}%`;
    }
  } catch (e) {}
}

function initGlobalCommandBar() {
  const input = document.getElementById("global-command-input");
  const btn = document.getElementById("btn-global-dispatch");

  const sendCommand = async () => {
    const query = input.value.trim();
    if (!query) return;

    input.value = "";
    try {
      await fetch("/api/v1/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      });
      loadProjectsList();
      refreshActiveProject();
    } catch (e) {}
  };

  btn?.addEventListener("click", sendCommand);
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendCommand();
  });
}

let currentUiLang = localStorage.getItem("nuxiva_ui_lang") || "it";

async function initI18n() {
  const selector = document.getElementById("lang-selector");
  if (selector) {
    selector.value = currentUiLang;
    selector.addEventListener("change", (e) => {
      applyLanguage(e.target.value);
    });
  }
  await applyLanguage(currentUiLang);
}

async function applyLanguage(lang) {
  currentUiLang = lang;
  localStorage.setItem("nuxiva_ui_lang", lang);

  try {
    const res = await fetch(`/static/features/dashboard/language/${lang}.json`);
    if (!res.ok) return;
    const data = await res.json();
    const c = data.cockpit;
    if (!c) return;

    const tabMap = {
      "tab-nav-projects": c.deck_projects,
      "tab-nav-flow": c.deck_cognitive_flow,
      "tab-nav-vault": c.deck_agent_vault,
      "tab-nav-rbac": c.deck_rbac,
      "tab-nav-hud": c.deck_proximity_hud,
      "tab-nav-cad": c.deck_cad_media,
      "tab-nav-telemetry": c.deck_telemetry,
      "tab-nav-chatbot": c.deck_chatbot_mesh,
      "tab-nav-multimodal-surveillance": c.deck_multimodal_surveillance,
      "tab-nav-affective-engine": c.deck_affective_engine,
      "tab-nav-wearables": c.deck_wearables_vitals,
      "tab-nav-emergency": c.deck_emergency_vitals,
    };

    for (const [id, text] of Object.entries(tabMap)) {
      const tabEl = document.getElementById(id);
      if (tabEl) {
        const span = tabEl.querySelector(".tab-label");
        if (span && text) span.textContent = text;
      }
    }

    applyDomTranslations(c);
    applyDomTranslations(data);

    window.dispatchEvent(new CustomEvent("nuxiva-language-changed", { detail: { lang } }));

    const inputCmd = document.getElementById("global-command-input");
    if (inputCmd && c.input_command_placeholder) {
      inputCmd.placeholder = c.input_command_placeholder;
    }
    const btnDispatch = document.getElementById("btn-global-dispatch");
    if (btnDispatch && c.btn_execute) {
      btnDispatch.textContent = c.btn_execute;
    }
    const btnSaveAgent = document.getElementById("btn-save-agent-instructions");
    if (btnSaveAgent && c.btn_save) {
      btnSaveAgent.textContent = c.btn_save;
    }
    const btnRecruit = document.getElementById("btn-recruit-agent");
    if (btnRecruit && c.btn_recruit) {
      btnRecruit.textContent = c.btn_recruit;
    }

    const hudUserName = document.getElementById("hud-detected-user-name");
    if (hudUserName && c.hud_user_default) {
      hudUserName.textContent = c.hud_user_default;
    }

    const uSel = document.getElementById("chatbot-user-selector");
    if (uSel && c.user_role_admin) {
      const optAdmin = uSel.querySelector("option[value='user_primary']");
      if (optAdmin) optAdmin.textContent = `👑 ${c.user_role_admin}`;
      const optFamily = uSel.querySelector("option[value='user_family']");
      if (optFamily) optFamily.textContent = `🏡 ${c.user_role_family}`;
      const optGuest = uSel.querySelector("option[value='user_guest']");
      if (optGuest) optGuest.textContent = `🌟 ${c.user_role_guest}`;
      const optStaff = uSel.querySelector("option[value='user_staff']");
      if (optStaff) optStaff.textContent = `💼 ${c.user_role_staff}`;
    }

    const wizTitle = document.getElementById("wizard-title-label");
    if (wizTitle && c.admin_wizard_title) {
      wizTitle.textContent = c.admin_wizard_title;
    }
    const wizAutoBtn = document.getElementById("btn-wizard-instant-autoconfig");
    if (wizAutoBtn && c.admin_wizard_auto_btn) {
      wizAutoBtn.textContent = c.admin_wizard_auto_btn;
    }
  } catch (err) {}
}
