(() => {
  const A = window.NuxivaAdmin, { $, fmt } = A;
  const PHASE_DOT = { READY: "ok", DEGRADED: "warn", ERROR: "down", INSTALLING: "warn", BOOTING: "warn", UPDATING: "warn" };
  const RESTARTABLE = { core: 1, qdrant: 1, ollama: 1, docker: 1, kiosk: 1 };
  const BG_BADGE = { done: "ok", running: "warn", failed: "down", waiting_disk: "down" };
  let bgPaused = false;

  function renderPhase(s) {
    $("phase-dot").className = `dot ${PHASE_DOT[s.phase] || "idle"}`;
    $("phase-lbl").textContent = s.phase_label;
    $("progress-lbl").textContent = s.phase === "READY" ? `v${s.supervisor_version}` : `${Math.floor(s.progress)}%`;
    $("cur-msg").textContent = s.message;
    $("cur-detail").textContent = s.detail || "";
    $("cur-err").textContent = s.last_error || "";
    $("b-progress").style.width = `${s.progress}%`;
    const b = s.brains || {};
    const lastPart = b.last ? ` · ${b.last}` : "";
    $("boot-info").textContent = A.t("overview.boot_info", {
      boot: s.boot_count,
      duration: fmt.duration(Date.now() / 1000 - s.phase_since),
      chat: b.chat || "—",
      deep: b.deep || s.llm_model || "—",
      last: lastPart
    });
  }

  function renderSystem(sys) {
    if (!sys.mem_total) return;
    $("s-cpu").textContent = `${sys.cpu_percent.toFixed(0)}%`;
    $("b-cpu").style.width = `${sys.cpu_percent}%`;
    $("s-load").textContent = A.t("overview.cpu_load", { cores: sys.cpu_count, load: sys.load.join(" / ") }) + (sys.temperature ? ` · ${sys.temperature} °C` : "");
    $("s-mem").textContent = `${sys.mem_percent.toFixed(0)}%`;
    $("b-mem").style.width = `${sys.mem_percent}%`;
    $("s-mem2").textContent = A.t("overview.mem_usage", { used: fmt.bytes(sys.mem_used), total: fmt.bytes(sys.mem_total) });
    $("s-disk").textContent = `${sys.disk_percent.toFixed(0)}%`;
    $("b-disk").style.width = `${sys.disk_percent}%`;
    $("s-disk2").textContent = A.t("overview.disk_usage", { used: fmt.bytes(sys.disk_used), total: fmt.bytes(sys.disk_total) });
    $("s-up").textContent = fmt.duration(sys.uptime);
    $("s-host").textContent = `${sys.hostname} · ${sys.ip} · ↓${fmt.rate(sys.net_rx_rate)} ↑${fmt.rate(sys.net_tx_rate)}`;
  }

  function compStatusLabel(c) {
    if (c.on_demand) return A.t("overview.status_on_demand");
    if (c.status === "ok") return A.t("overview.status_ok");
    if (c.status === "warn") return A.t("overview.status_warn");
    return A.t("overview.status_fail");
  }

  function renderComponents(s) {
    const list = Object.entries(s.components || {});
    if (!list.length) {
      $("comp-body").innerHTML = `<tr><td colspan="4" class="faint">${fmt.esc(A.t("overview.diag_available"))}</td></tr>`;
      return;
    }
    $("comp-body").innerHTML = list.map(([k, c]) => {
      const confirmMsg = A.t("overview.confirm_restart_comp", { name: c.label });
      const restartBtn = RESTARTABLE[k] ? `<button class="btn sm" data-action="restart-component" data-body='{"component":"${k}"}' data-confirm="${fmt.esc(confirmMsg)}">${fmt.esc(A.t("overview.restart"))}</button>` : "";
      return `<tr><td><span class="dot ${c.on_demand ? "idle" : c.status}"></span></td><td>${fmt.esc(c.label)}<div class="faint mono">${fmt.esc(c.detail)}</div></td>
        <td><span class="badge ${c.on_demand ? "" : c.status}">${fmt.esc(compStatusLabel(c))}</span></td>
        <td style="text-align:right">${restartBtn}</td></tr>`;
    }).join("");
  }

  function renderSteps(s) {
    $("steps-body").innerHTML = s.catalog.map((c) => {
      const r = s.steps[c.id] || { status: "pending" };
      const prog = r.status === "running" ? ` ${r.progress}%` : "";
      const statusText = (A.t("steps.status_" + r.status) || r.status) + prog;
      const opt = c.critical ? "" : ` · ${A.t("steps.optional")}`;
      const confirmMsg = A.t("steps.confirm_rerun", { title: c.title });
      return `<tr><td>${fmt.esc(c.title)}<div class="faint" style="font-size:12px">${fmt.esc(c.description)}${fmt.esc(opt)}</div></td>
        <td><span class="badge ${r.status}">${fmt.esc(statusText)}</span></td>
        <td class="mono">${r.attempts || 0}</td><td class="mono">${r.duration ? fmt.duration(r.duration) : "—"}</td>
        <td style="max-width:320px; font-size:12px" class="${r.error ? "" : "dim"}">${fmt.esc(r.error || r.message || "")}</td>
        <td style="text-align:right"><button class="btn sm" data-action="rerun-step" data-body='{"step":"${c.id}"}' data-confirm="${fmt.esc(confirmMsg)}" ${s.busy ? "disabled" : ""}>${fmt.esc(A.t("steps.rerun"))}</button></td></tr>`;
    }).join("");
  }

  function renderBackground(bg) {
    if (!bg || !bg.items) return;
    bgPaused = !!bg.paused;
    $("bg-state").className = `badge ${bg.finished ? "ok" : bg.paused ? "down" : "warn"}`;
    $("bg-state").textContent = bg.finished ? A.t("steps.bg_finished") : bg.paused ? A.t("steps.bg_paused") : bg.conversation ? A.t("steps.bg_waiting_conv") : A.t("steps.status_running");
    $("bg-summary").textContent = A.t("steps.bg_summary", { done: bg.done, total: bg.total, progress: bg.progress });
    $("bg-progress").style.width = `${bg.progress}%`;
    $("bg-toggle").textContent = bg.paused ? A.t("steps.bg_resume") : A.t("steps.bg_pause");
    $("bg-toggle").hidden = !!bg.finished;
    $("bg-body").innerHTML = bg.items.map((i, n) => {
      const statusLabel = (A.t("steps.bg_" + i.status) || i.status) + (i.status === "running" ? ` ${i.progress}%` : "");
      const firstBtn = i.status !== "done" && n > 0 ? `<button class="btn sm" type="button" data-bg-first="${fmt.esc(i.id)}">${fmt.esc(A.t("steps.first"))}</button>` : "";
      return `<tr><td>${fmt.esc(i.title)}<div class="faint" style="font-size:12px">${fmt.esc(i.description)}</div></td>
        <td class="mono">${Number(i.size_gb).toFixed(1)} GB</td>
        <td><span class="badge ${BG_BADGE[i.status] || ""}">${fmt.esc(statusLabel)}</span>${i.speed ? `<div class="mono">${`↓ ${fmt.esc(i.speed)}`}</div>` : ""}</td>
        <td style="max-width:320px; font-size:12px" class="${i.status === "running" ? "text-cyan" : "dim"}">${fmt.esc(i.detail || i.message || "")}</td>
        <td style="text-align:right">${firstBtn}</td></tr>`;
    }).join("");
  }

  function renderEvents(s) {
    const loc = window.i18n && window.i18n.currentLang ? window.i18n.currentLang : undefined;
    $("events-body").innerHTML = (s.events || []).slice().reverse().map((e) => `
      <tr><td class="mono">${new Date(e.ts).toLocaleString(loc)}</td><td><span class="badge ${e.level === "ERROR" ? "down" : e.level === "WARN" ? "warn" : "ok"}">${fmt.esc(e.level)}</span></td>
      <td class="mono">${fmt.esc(e.component)}</td><td>${fmt.esc(e.msg)}</td></tr>`).join("");
  }

  function renderUpdate(u) {
    const loc = window.i18n && window.i18n.currentLang ? window.i18n.currentLang : undefined;
    const statusHtml = u.available ? `<span class="badge warn">${fmt.esc(A.t("overview.update_available"))}</span>` : u.remote_rev && u.remote_rev !== u.local_rev ? `<span class="badge">${fmt.esc(u.ci_note || A.t("steps.status_pending"))}</span>` : `<span class="badge ok">${fmt.esc(A.t("overview.up_to_date"))}</span>`;
    $("upd-body").innerHTML = `
      <tr><td class="dim">${fmt.esc(A.t("updates.local_ver"))}</td><td class="mono">${fmt.esc((u.local_rev || "—").slice(0, 10))}</td></tr>
      <tr><td class="dim">${fmt.esc(A.t("updates.remote_ver"))}</td><td class="mono">${fmt.esc((u.remote_rev || "—").slice(0, 10))}</td></tr>
      <tr><td class="dim">${fmt.esc(A.t("updates.target_ver"))}</td><td class="mono">${fmt.esc((u.target_rev || "—").slice(0, 10))}</td></tr>
      <tr><td class="dim">${fmt.esc(A.t("updates.status"))}</td><td>${statusHtml}</td></tr>
      <tr><td class="dim">${fmt.esc(A.t("updates.last_check"))}</td><td class="mono">${u.last_check ? new Date(u.last_check).toLocaleString(loc) : "—"}</td></tr>
      <tr><td class="dim">${fmt.esc(A.t("updates.last_result"))}</td><td>${fmt.esc(u.last_result || "—")}</td></tr>`;
    $("upd-log").textContent = (u.changelog && u.changelog.length) ? u.changelog.join("\n") : A.t("updates.no_news");
  }

  async function loadConfig() {
    const d = await A.api("GET", "/api/config");
    $("config-fields").innerHTML = d.editable.map((f) => `<div><label for="cfg-${f.key}">${fmt.esc(f.label)}</label>
      <input id="cfg-${f.key}" name="${f.key}" value="${fmt.esc(f.value)}" ${f.secret ? 'type="password"' : ""} autocomplete="off"></div>`).join("");
    $("config-system").innerHTML = Object.entries(d.system).map(([k, v]) => `<tr><td class="mono dim">${fmt.esc(k)}</td><td class="mono">${fmt.esc(v || "—")}</td></tr>`).join("");
  }

  async function loadLogs() {
    try {
      const d = await A.api("GET", `/api/logs/${$("log-src").value}?lines=400`);
      const el = $("log-text");
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 30;
      el.textContent = d.text || "";
      if (atBottom) el.scrollTop = el.scrollHeight;
    } catch (e) {
      $("log-text").textContent = e.message;
    }
  }

  function init() {
    document.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-action]");
      if (!b) return;
      const confirmMsg = b.dataset.confirmI18n ? A.t(b.dataset.confirmI18n) : b.dataset.confirm;
      if (confirmMsg && !confirm(confirmMsg)) return;
      const body = b.dataset.body ? JSON.parse(b.dataset.body) : undefined;
      b.disabled = true;
      try {
        const r = await A.api("POST", `/api/actions/${b.dataset.action}`, body);
        if (b.dataset.action === "update-check") {
          renderUpdate(r);
          A.toast(r.available ? A.t("overview.update_available") : A.t("overview.up_to_date"));
        } else {
          A.toast(r.message || (r.ok === false ? A.t("overview.op_failed") : A.t("overview.op_started")), r.ok === false);
        }
      } catch (err) {
        A.toast(err.message, true);
      } finally {
        setTimeout(() => (b.disabled = false), 1500);
      }
    });

    $("config-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {};
      new FormData(e.target).forEach((v, k) => (body[k] = v));
      try {
        const r = await A.api("PUT", "/api/config", body);
        A.toast(r.changed && r.changed.length ? `OK: ${r.changed.join(", ")}` : "OK");
        loadConfig();
      } catch (err) {
        A.toast(err.message, true);
      }
    });

    $("bg-toggle").addEventListener("click", async () => {
      const b = $("bg-toggle");
      b.disabled = true;
      try {
        renderBackground(await A.api("POST", `/api/background/${bgPaused ? "resume" : "pause"}`));
      } catch (err) {
        A.toast(err.message, true);
      } finally {
        b.disabled = false;
      }
    });

    $("bg-body").addEventListener("click", async (e) => {
      const b = e.target.closest("[data-bg-first]");
      if (!b) return;
      b.disabled = true;
      try {
        renderBackground(await A.api("POST", `/api/background/prioritize?step=${encodeURIComponent(b.dataset.bgFirst)}`));
      } catch (err) {
        A.toast(err.message, true);
        b.disabled = false;
      }
    });

    $("wake-file").addEventListener("change", async (e) => {
      const f = e.target.files[0];
      e.target.value = "";
      if (!f) return;
      try {
        if (!/\.onnx$/i.test(f.name)) throw new Error(A.t("steps.wake_error"));
        const r = await fetch("/api/setup/wakeword", {
          method: "POST",
          body: f,
          credentials: "same-origin",
          headers: { "X-Nuxiva-Request": "1", "Content-Type": "application/octet-stream" }
        });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
        $("wake-note").textContent = `OK: ${f.name}`;
        A.toast(A.t("steps.wake_success"));
      } catch (err) {
        A.toast(err.message, true);
      }
    });

    $("log-src").addEventListener("change", loadLogs);
    $("log-refresh").addEventListener("click", loadLogs);
    setInterval(() => { if (A.isOn("logs") && $("log-auto").checked) loadLogs(); }, 4000);
  }

  A.tab("overview", { init, onState(s) {
    renderPhase(s);
    renderSystem(s.system || {});
    renderComponents(s);
    renderSteps(s);
    renderBackground(s.background);
    renderEvents(s);
    if (s.update) renderUpdate(s.update);
  } });
  A.tab("config", { load: loadConfig });
  A.tab("logs", { load: loadLogs });
  A.tab("updates", { load: () => A.api("POST", "/api/actions/update-check").then(renderUpdate).catch((e) => A.toast(e.message, true)) });
})();
