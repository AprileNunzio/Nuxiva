export let currentSelectedProjectId = null;

export async function initProjectsDeck() {
  document.getElementById("btn-war-room-send")?.addEventListener("click", sendWarRoomMessage);
  document.getElementById("war-room-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendWarRoomMessage();
  });
  document.getElementById("btn-recruit-agent")?.addEventListener("click", recruitAgentToCurrentProject);

  await loadProjectsList();
}

export async function loadProjectsList() {
  try {
    const res = await fetch("/api/v1/projects");
    const data = await res.json();
    const container = document.getElementById("projects-list-container");
    if (!container) return;

    container.innerHTML = "";
    if (!data.projects || data.projects.length === 0) {
      container.innerHTML = "<p style='font-size:0.8rem; color:var(--text-muted);'>Nessun progetto aperto.</p>";
      return;
    }

    data.projects.forEach(p => {
      const card = document.createElement("div");
      card.className = "tactical-card";
      card.style.padding = "0.75rem";
      card.style.cursor = "pointer";
      card.style.border = (p.project_id === currentSelectedProjectId) ? "1px solid var(--cyan-glow)" : "1px solid rgba(255,255,255,0.08)";
      card.style.background = (p.project_id === currentSelectedProjectId) ? "rgba(0,240,255,0.08)" : "rgba(15,23,42,0.6)";

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <strong style="color:#fff; font-size:0.9rem;">${p.name}</strong>
          <span style="font-family:var(--font-mono); font-size:0.8rem; color:var(--cyan-glow);">${Math.round(p.completion_percentage || 0)}%</span>
        </div>
        <p style="font-size:0.75rem; color:var(--text-muted); margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${p.goal}</p>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
          <span style="font-size:0.7rem; color:var(--text-dim);">${p.assigned_agents ? p.assigned_agents.length : 0} Agenti</span>
          ${p.autonomous_247 ? "<span class='badge-tag' style='background:rgba(16,185,129,0.2); color:#34d399;'>24/7</span>" : ""}
        </div>
      `;

      card.addEventListener("click", () => {
        currentSelectedProjectId = p.project_id;
        loadProjectsList();
        renderProjectDetails(p);
      });
      container.appendChild(card);
    });

    if (!currentSelectedProjectId && data.projects.length > 0) {
      currentSelectedProjectId = data.projects[0].project_id;
      renderProjectDetails(data.projects[0]);
    }
  } catch (e) {}
}

export async function refreshActiveProject() {
  if (!currentSelectedProjectId) return;
  try {
    const res = await fetch(`/api/v1/projects/${currentSelectedProjectId}`);
    const data = await res.json();
    if (data.project) {
      renderProjectDetails(data.project);
    }
  } catch (e) {}
}

function renderProjectDetails(p) {
  document.getElementById("current-project-title").innerText = p.name;
  document.getElementById("current-project-goal").innerText = p.goal;
  const pct = Math.round(p.completion_percentage || 0);
  document.getElementById("current-project-pct").innerText = `${pct}%`;
  document.getElementById("current-project-progress-bar").style.width = `${pct}%`;

  const autoBadge = document.getElementById("current-project-auto-badge");
  if (autoBadge) autoBadge.style.display = p.autonomous_247 ? "inline-block" : "none";

  const feedContainer = document.getElementById("war-room-feed");
  feedContainer.innerHTML = "";
  (p.war_room_feed || []).forEach(msg => {
    const item = document.createElement("div");
    item.className = `feed-item ${msg.message_type || "action"}`;
    item.innerHTML = `
      <div class="feed-header">
        <span class="feed-sender">${msg.sender_name} (${msg.sender_role})</span>
        <span>${new Date((msg.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()}</span>
      </div>
      <div class="feed-content">${msg.content}</div>
    `;
    feedContainer.appendChild(item);
  });
  feedContainer.scrollTop = feedContainer.scrollHeight;

  const msContainer = document.getElementById("project-milestones-list");
  msContainer.innerHTML = "";
  (p.milestones || []).forEach(m => {
    const box = document.createElement("div");
    box.style.background = "rgba(15,23,42,0.6)";
    box.style.border = "1px solid rgba(255,255,255,0.06)";
    box.style.borderRadius = "8px";
    box.style.padding = "0.6rem";
    box.innerHTML = `
      <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:600;">
        <span>${m.title}</span>
        <span style="color:var(--cyan-glow);">${Math.round(m.progress * 100)}%</span>
      </div>
      <div class="progress-container" style="height:6px; margin-top:6px;">
        <div class="progress-bar-fill" style="width:${Math.round(m.progress * 100)}%;"></div>
      </div>
    `;
    msContainer.appendChild(box);
  });

  const rosterContainer = document.getElementById("project-team-roster");
  rosterContainer.innerHTML = "";
  (p.assigned_agents || []).forEach(ag => {
    const div = document.createElement("div");
    div.style.display = "flex";
    div.style.justifyContent = "space-between";
    div.style.alignItems = "center";
    div.style.padding = "0.4rem 0.6rem";
    div.style.background = "rgba(255,255,255,0.04)";
    div.style.borderRadius = "6px";
    div.style.fontSize = "0.8rem";
    div.innerHTML = `
      <span style="font-family:var(--font-mono); color:#fff;">${ag}</span>
      <span class='pulse-dot' style='color:#34d399;'></span>
    `;
    rosterContainer.appendChild(div);
  });
}

async function sendWarRoomMessage() {
  const input = document.getElementById("war-room-input");
  const content = input.value.trim();
  if (!content || !currentSelectedProjectId) return;

  try {
    await fetch(`/api/v1/projects/${currentSelectedProjectId}/war-room/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender_id: "user_primary",
        sender_name: "Admin (Owner)",
        sender_role: "Human Overseer",
        message_type: "user_input",
        content: content,
      })
    });
    input.value = "";
    refreshActiveProject();
  } catch (e) {}
}

async function recruitAgentToCurrentProject() {
  const select = document.getElementById("select-recruit-agent");
  const agentId = select.value;
  if (!agentId || !currentSelectedProjectId) return;

  try {
    await fetch(`/api/v1/projects/${currentSelectedProjectId}/agents/recruit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requester_agent_id: "chief_supervisor",
        target_agent_id: agentId,
        justification: "Convocazione manuale da plancia di controllo utente."
      })
    });
    refreshActiveProject();
  } catch (e) {}
}
