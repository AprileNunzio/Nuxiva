function getActiveVaultUserId() {
  const input = document.getElementById("vault-user-id");
  return (input?.value || "user_primary").trim() || "user_primary";
}

function setVaultFeedback(msg, isError = false) {
  const el = document.getElementById("vault-feedback");
  if (!el) return;
  el.style.color = isError ? "#fda4af" : "var(--cyan-glow)";
  el.textContent = msg;
}

function setProvisionerLog(result) {
  const el = document.getElementById("provisioner-log-output");
  if (!el) return;
  if (typeof result === "string") {
    el.textContent = result;
    return;
  }
  const lines = [
    `[${result.success ? "SUCCESSO" : "ERRORE"}] ${result.summary}`,
    `Target: ${result.target} (${result.device_type})`,
    "--- Passaggi eseguiti ---",
    ...(result.steps || []).map(
      (s) => `[${s.status.toUpperCase()}] ${s.step} (${s.duration_ms}ms): ${s.detail}`
    ),
  ];
  el.textContent = lines.join("\n");
}

export async function refreshVaultStatusAndEntries() {
  const userId = getActiveVaultUserId();
  try {
    const statusRes = await fetch(`/api/v1/vault/${encodeURIComponent(userId)}/status`);
    if (!statusRes.ok) return;
    const status = await statusRes.json();

    const badge = document.getElementById("vault-status-badge");
    if (badge) {
      if (status.unlocked) {
        badge.textContent = `SBLOCCATO (${status.entry_count})`;
        badge.style.background = "rgba(16,185,129,0.2)";
        badge.style.color = "#34d399";
      } else {
        badge.textContent = status.initialized ? `BLOCCATO (${status.entry_count})` : "NUOVO VAULT";
        badge.style.background = "rgba(244,63,94,0.2)";
        badge.style.color = "#fda4af";
      }
    }

    const listRes = await fetch(`/api/v1/vault/${encodeURIComponent(userId)}/entries`);
    const entries = listRes.ok ? await listRes.json() : [];
    renderVaultEntries(entries, status.unlocked);
    populateProvisionerVaultSelectors(entries);
  } catch (err) {
    setVaultFeedback("Impossibile contattare il servizio Password Vault.", true);
  }
}

function populateProvisionerVaultSelectors(entries) {
  const wifiSelect = document.getElementById("esp32-wifi-vault-select");
  const sshSelect = document.getElementById("debian-ssh-vault-select");

  if (wifiSelect) {
    const prev = wifiSelect.value;
    wifiSelect.innerHTML = `<option value="">Wi-Fi dal Vault (opzionale)</option>`;
    entries
      .filter((e) => e.category === "wifi")
      .forEach((e) => {
        const opt = document.createElement("option");
        opt.value = e.entry_id;
        opt.textContent = `📶 ${e.label} (${e.username || e.host_or_url || "Wi-Fi"})`;
        wifiSelect.appendChild(opt);
      });
    wifiSelect.value = prev;
  }

  if (sshSelect) {
    const prev = sshSelect.value;
    sshSelect.innerHTML = `<option value="">Credenziale SSH dal Vault (opzionale)</option>`;
    entries
      .filter((e) => e.category === "ssh" || e.category === "device")
      .forEach((e) => {
        const opt = document.createElement("option");
        opt.value = e.entry_id;
        opt.textContent = `🖥️ ${e.label} (${e.username}@${e.host_or_url || "host"})`;
        sshSelect.appendChild(opt);
      });
    sshSelect.value = prev;
  }
}

function renderVaultEntries(entries, isUnlocked) {
  const container = document.getElementById("vault-entries-list");
  if (!container) return;

  if (!entries || entries.length === 0) {
    container.innerHTML = `<div style="text-align:center; color:var(--text-muted); font-size:0.78rem; padding:1rem;">Nessuna credenziale salvata per questo utente.</div>`;
    return;
  }

  container.innerHTML = "";
  entries.forEach((entry) => {
    const row = document.createElement("div");
    row.style.padding = "0.55rem 0.7rem";
    row.style.borderRadius = "6px";
    row.style.background = "rgba(255,255,255,0.03)";
    row.style.border = "1px solid rgba(255,255,255,0.08)";
    row.style.display = "flex";
    row.style.justifyContent = "space-between";
    row.style.alignItems = "center";
    row.style.gap = "0.5rem";

    const info = document.createElement("div");
    info.innerHTML = `
      <div style="font-weight:600; font-size:0.82rem; color:#fff;">${escapeHtml(entry.label)} <span class="badge-tag" style="font-size:0.65rem;">${escapeHtml(entry.category.toUpperCase())}</span></div>
      <div style="font-size:0.72rem; color:var(--text-muted); font-family:var(--font-mono);">${escapeHtml(entry.username || "-")} @ ${escapeHtml(entry.host_or_url || "-")} · ${escapeHtml(entry.masked_preview || "••••")}</div>
    `;

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "0.3rem";

    const revealBtn = document.createElement("button");
    revealBtn.className = "tactical-btn secondary";
    revealBtn.type = "button";
    revealBtn.style.padding = "0.25rem 0.55rem";
    revealBtn.style.fontSize = "0.72rem";
    revealBtn.textContent = isUnlocked ? "👁 Copia" : "🔒";
    revealBtn.disabled = !isUnlocked;
    revealBtn.addEventListener("click", async () => {
      const userId = getActiveVaultUserId();
      const res = await fetch(`/api/v1/vault/${encodeURIComponent(userId)}/entries/${entry.entry_id}/reveal`, {
        method: "POST",
      });
      if (!res.ok) {
        setVaultFeedback("Vault bloccato: sbloccalo prima di copiare.", true);
        return;
      }
      const data = await res.json();
      if (navigator.clipboard && data.secret) {
        await navigator.clipboard.writeText(data.secret).catch(() => {});
        setVaultFeedback(`Segreto per "${entry.label}" copiato negli appunti.`);
      } else {
        setVaultFeedback(`Segreto rivelato per "${entry.label}".`);
      }
    });

    const delBtn = document.createElement("button");
    delBtn.className = "tactical-btn secondary";
    delBtn.type = "button";
    delBtn.style.padding = "0.25rem 0.5rem";
    delBtn.style.fontSize = "0.72rem";
    delBtn.textContent = "🗑";
    delBtn.disabled = !isUnlocked;
    delBtn.addEventListener("click", async () => {
      const userId = getActiveVaultUserId();
      const res = await fetch(`/api/v1/vault/${encodeURIComponent(userId)}/entries/${entry.entry_id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setVaultFeedback(`Voce "${entry.label}" eliminata.`);
        refreshVaultStatusAndEntries();
      }
    });

    actions.appendChild(revealBtn);
    actions.appendChild(delBtn);
    row.appendChild(info);
    row.appendChild(actions);
    container.appendChild(row);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

async function scanEsp32Ports() {
  setProvisionerLog("Scansione porte USB/COM ESP32 in corso...");
  try {
    const res = await fetch("/api/v1/provisioner/esp32/ports");
    const ports = await res.json();
    const sel = document.getElementById("esp32-port-select");
    if (sel) {
      sel.innerHTML = `<option value="">Auto-rileva ESP32</option>`;
      ports.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.port;
        opt.textContent = `${p.is_esp32_likely ? "⚡" : "🔌"} ${p.port} — ${p.chip_hint}`;
        sel.appendChild(opt);
      });
    }
    setProvisionerLog(
      ports.length > 0
        ? `Trovate ${ports.length} porte seriali:\n` +
          ports.map((p) => `- ${p.port} (${p.chip_hint}, ESP32=${p.is_esp32_likely})`).join("\n")
        : "Nessuna porta seriale/USB rilevata al momento."
    );
  } catch (err) {
    setProvisionerLog("Errore durante la scansione porte seriali.");
  }
}

async function runEsp32Provision(dryRun) {
  setProvisionerLog(dryRun ? "Validazione piano ESP32 (dry-run)..." : "Avvio auto-installazione ESP32...");
  const payload = {
    user_id: getActiveVaultUserId(),
    port: document.getElementById("esp32-port-select")?.value || null,
    wifi_vault_entry_id: document.getElementById("esp32-wifi-vault-select")?.value || null,
    nuxiva_server_url: document.getElementById("esp32-server-url")?.value || "http://nuxiva.local:80",
    dry_run: dryRun,
  };
  const res = await fetch("/api/v1/provisioner/esp32/install", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setProvisionerLog(await res.json());
}

async function runDebianAction(mode) {
  const host = (document.getElementById("debian-host")?.value || "").trim();
  if (!host) {
    setProvisionerLog("Inserisci un IP o hostname Debian (es. 192.168.1.50).");
    return;
  }
  const payload = {
    user_id: getActiveVaultUserId(),
    host: host,
    port: parseInt(document.getElementById("debian-port")?.value || "22", 10),
    username: (document.getElementById("debian-user")?.value || "root").trim(),
    ssh_vault_entry_id: document.getElementById("debian-ssh-vault-select")?.value || null,
    install_mode: document.getElementById("debian-install-mode")?.value || "satellite",
    dry_run: mode === "dryrun",
  };
  const endpoint = mode === "probe" ? "/api/v1/provisioner/debian/probe" : "/api/v1/provisioner/debian/install";
  setProvisionerLog(`Esecuzione ${mode} verso ${payload.username}@${payload.host}:${payload.port}...`);
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setProvisionerLog(await res.json());
}

export function initPasswordVaultDeck() {
  document.getElementById("vault-user-id")?.addEventListener("change", refreshVaultStatusAndEntries);

  document.getElementById("btn-vault-unlock")?.addEventListener("click", async () => {
    const userId = getActiveVaultUserId();
    const pwd = document.getElementById("vault-master-password")?.value || "";
    if (pwd.length < 4) {
      setVaultFeedback("Inserisci una master password di almeno 4 caratteri.", true);
      return;
    }
    const res = await fetch(`/api/v1/vault/${encodeURIComponent(userId)}/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ master_password: pwd }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setVaultFeedback(err.detail || "Master password errata.", true);
      return;
    }
    document.getElementById("vault-master-password").value = "";
    setVaultFeedback(`Vault dell'utente '${userId}' sbloccato.`);
    refreshVaultStatusAndEntries();
  });

  document.getElementById("btn-vault-lock")?.addEventListener("click", async () => {
    const userId = getActiveVaultUserId();
    await fetch(`/api/v1/vault/${encodeURIComponent(userId)}/lock`, { method: "POST" });
    setVaultFeedback(`Vault bloccato in sicurezza.`);
    refreshVaultStatusAndEntries();
  });

  document.getElementById("btn-vault-gen-pwd")?.addEventListener("click", async () => {
    const res = await fetch("/api/v1/vault/generate-password?length=20&symbols=true");
    if (res.ok) {
      const data = await res.json();
      const input = document.getElementById("vault-entry-secret");
      if (input) {
        input.value = data.password;
        input.type = "text";
      }
      setVaultFeedback("Password forte generata (20 caratteri CSPRNG).");
    }
  });

  document.getElementById("btn-vault-save-entry")?.addEventListener("click", async () => {
    const userId = getActiveVaultUserId();
    const label = (document.getElementById("vault-entry-label")?.value || "").trim();
    if (!label) {
      setVaultFeedback("Inserisci il nome della voce da salvare.", true);
      return;
    }
    const payload = {
      label,
      category: document.getElementById("vault-entry-category")?.value || "web",
      host_or_url: (document.getElementById("vault-entry-host")?.value || "").trim(),
      username: (document.getElementById("vault-entry-username")?.value || "").trim(),
      secret: document.getElementById("vault-entry-secret")?.value || "",
    };
    const res = await fetch(`/api/v1/vault/${encodeURIComponent(userId)}/entries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setVaultFeedback(err.detail || "Errore salvataggio (sblocca prima il vault).", true);
      return;
    }
    ["vault-entry-label", "vault-entry-host", "vault-entry-username", "vault-entry-secret"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    const secInput = document.getElementById("vault-entry-secret");
    if (secInput) secInput.type = "password";
    setVaultFeedback(`Credenziale "${label}" cifrata e salvata nel vault.`);
    refreshVaultStatusAndEntries();
  });

  document.getElementById("btn-esp32-scan")?.addEventListener("click", scanEsp32Ports);
  document.getElementById("btn-esp32-dryrun")?.addEventListener("click", () => runEsp32Provision(true));
  document.getElementById("btn-esp32-flash")?.addEventListener("click", () => runEsp32Provision(false));
  document.getElementById("btn-debian-probe")?.addEventListener("click", () => runDebianAction("probe"));
  document.getElementById("btn-debian-dryrun")?.addEventListener("click", () => runDebianAction("dryrun"));
  document.getElementById("btn-debian-install")?.addEventListener("click", () => runDebianAction("install"));

  refreshVaultStatusAndEntries();
}
