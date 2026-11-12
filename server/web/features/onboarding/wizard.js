let wizardCurrentStep = 1;
const wizardTotalSteps = 4;
let wizardSelectedEnv = "smart_home";
let wizardSelectedAgents = new Set();
let wizardScannedTools = [];
let wizardScannedWidgets = [];

export function initAdminWizard() {
  const btnOpen = document.getElementById("btn-open-admin-wizard");
  const overlay = document.getElementById("admin-wizard-overlay");
  const btnClose = document.getElementById("btn-close-wizard");
  const btnSkip = document.getElementById("btn-wizard-skip");
  const btnNext = document.getElementById("btn-wizard-next");
  const btnPrev = document.getElementById("btn-wizard-prev");
  const btnFinish = document.getElementById("btn-wizard-finish");
  const btnInstantAuto = document.getElementById("btn-wizard-instant-autoconfig");

  const openWizard = () => {
    wizardCurrentStep = 1;
    updateWizardStepView();
    overlay?.classList.add("active");
    loadWizardScannedData();
  };

  const closeWizard = () => {
    overlay?.classList.remove("active");
  };

  btnOpen?.addEventListener("click", openWizard);
  btnClose?.addEventListener("click", closeWizard);
  btnSkip?.addEventListener("click", closeWizard);

  btnNext?.addEventListener("click", () => {
    if (wizardCurrentStep < wizardTotalSteps) {
      wizardCurrentStep++;
      updateWizardStepView();
    }
  });

  btnPrev?.addEventListener("click", () => {
    if (wizardCurrentStep > 1) {
      wizardCurrentStep--;
      updateWizardStepView();
    }
  });

  btnFinish?.addEventListener("click", () => {
    closeWizard();
    const tabProjects = document.getElementById("tab-nav-projects");
    tabProjects?.click();
  });

  btnInstantAuto?.addEventListener("click", async () => {
    btnInstantAuto.innerHTML = `<span>⏳</span> Auto-Configurazione in corso...`;
    btnInstantAuto.style.background = "linear-gradient(90deg, #f59e0b, #ec4899)";

    try {
      await fetch("/api/v1/system/ternary-models/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: "bonsai-27b" })
      });
      wizardCurrentStep = 4;
      updateWizardStepView();
    } catch (e) {
      wizardCurrentStep = 4;
      updateWizardStepView();
    }
  });

  document.querySelectorAll(".selectable-wizard-card[data-env]").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".selectable-wizard-card[data-env]").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      wizardSelectedEnv = card.getAttribute("data-env");
    });
  });

  document.getElementById("btn-wizard-select-all-agents")?.addEventListener("click", () => {
    document.querySelectorAll(".wizard-agent-card").forEach(c => {
      c.classList.add("selected");
      const aId = c.getAttribute("data-agent-id");
      if (aId) wizardSelectedAgents.add(aId);
    });
  });
}

function updateWizardStepView() {
  for (let i = 1; i <= wizardTotalSteps; i++) {
    const node = document.getElementById(`step-node-${i}`);
    const pane = document.getElementById(`wizard-step-${i}`);

    if (node) {
      node.classList.remove("active", "completed");
      if (i === wizardCurrentStep) {
        node.classList.add("active");
      } else if (i < wizardCurrentStep) {
        node.classList.add("completed");
      }
    }

    if (pane) {
      pane.classList.remove("active");
      if (i === wizardCurrentStep) {
        pane.classList.add("active");
      }
    }
  }

  const btnPrev = document.getElementById("btn-wizard-prev");
  const btnNext = document.getElementById("btn-wizard-next");
  const btnFinish = document.getElementById("btn-wizard-finish");

  if (btnPrev) btnPrev.style.display = wizardCurrentStep > 1 ? "inline-block" : "none";
  if (btnNext) btnNext.style.display = wizardCurrentStep < wizardTotalSteps ? "inline-block" : "none";
  if (btnFinish) btnFinish.style.display = wizardCurrentStep === wizardTotalSteps ? "inline-block" : "none";
}

async function loadWizardScannedData() {
  try {
    const resA = await fetch("/api/v1/chatbot/agents");
    const dataA = await resA.json();
    const container = document.getElementById("wizard-agents-scanned-container");
    if (container && dataA.agents) {
      container.innerHTML = "";
      wizardSelectedAgents.clear();
      dataA.agents.forEach(agent => {
        wizardSelectedAgents.add(agent.agent_id);
        const card = document.createElement("div");
        card.className = "selectable-wizard-card selected wizard-agent-card";
        card.setAttribute("data-agent-id", agent.agent_id);
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:var(--cyan-glow); font-size:0.88rem;">${agent.name}</strong>
            <span class="badge-tag" style="font-size:0.65rem;">${agent.role_category}</span>
          </div>
          <p style="font-size:0.73rem; color:var(--text-muted);">${agent.description}</p>
        `;
        card.addEventListener("click", () => {
          if (card.classList.contains("selected")) {
            card.classList.remove("selected");
            wizardSelectedAgents.delete(agent.agent_id);
          } else {
            card.classList.add("selected");
            wizardSelectedAgents.add(agent.agent_id);
          }
        });
        container.appendChild(card);
      });
    }
  } catch (e) {}

  try {
    const resT = await fetch("/api/v1/chatbot/tools/catalog");
    const dataT = await resT.json();
    const tBox = document.getElementById("wizard-tools-scanned-list");
    if (tBox && dataT.tools) {
      tBox.innerHTML = "";
      dataT.tools.forEach(tool => {
        const item = document.createElement("div");
        item.style.padding = "0.4rem 0.6rem";
        item.style.background = "rgba(255,255,255,0.03)";
        item.style.borderRadius = "6px";
        item.style.border = "1px solid var(--border-glow)";
        item.style.display = "flex";
        item.style.alignItems = "center";
        item.style.justifyContent = "space-between";
        item.innerHTML = `
          <span style="font-size:0.75rem; color:#fff;">${tool.icon || '🛠️'} ${tool.name}</span>
          <span class="badge-tag" style="font-size:0.62rem; color:var(--emerald-glow);">Auto-Rilevato</span>
        `;
        tBox.appendChild(item);
      });
    }
  } catch (e) {}

  try {
    const resW = await fetch("/api/v1/chatbot/widgets/catalog");
    const dataW = await resW.json();
    const wBox = document.getElementById("wizard-widgets-scanned-list");
    if (wBox && dataW.widgets) {
      wBox.innerHTML = "";
      dataW.widgets.forEach(widget => {
        const item = document.createElement("div");
        item.style.padding = "0.4rem 0.6rem";
        item.style.background = "rgba(0,240,255,0.03)";
        item.style.borderRadius = "6px";
        item.style.border = "1px solid var(--border-glow)";
        item.style.display = "flex";
        item.style.alignItems = "center";
        item.style.justifyContent = "space-between";
        item.innerHTML = `
          <span style="font-size:0.75rem; color:var(--cyan-glow);">${widget.icon || '📊'} ${widget.name}</span>
          <span class="badge-tag" style="font-size:0.62rem; color:#38bdf8;">Pronto</span>
        `;
        wBox.appendChild(item);
      });
    }
  } catch (e) {}
}
