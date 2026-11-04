(() => {
  "use strict";

  let modal = null;
  const btnClose = () => document.getElementById("btn-network-close");
  const btnRefresh = () => document.getElementById("btn-network-refresh");

  function ensureModal() {
    if (modal) return modal;
    modal = document.getElementById("os-network-modal");
    if (modal) return modal;

    modal = document.createElement("div");
    modal.className = "os-network-modal-backdrop";
    modal.id = "os-network-modal";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.innerHTML = `
      <div class="os-network-window">
        <header class="os-network-header">
          <div class="os-network-titlebar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
            <span class="os-network-title">Diagnostica di Rete</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <button type="button" class="os-network-btn-refresh" id="btn-network-refresh" title="Aggiorna">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
              <span>Aggiorna</span>
            </button>
            <button type="button" class="os-network-btn-close" id="btn-network-close" title="Chiudi">✕</button>
          </div>
        </header>
        <div class="os-network-body">
          <div class="os-net-metric-grid">
            <div class="os-net-card">
              <div class="os-net-card-label"><span>IP Locale</span><button type="button" class="os-net-copy-btn" data-copy-target="net-local-ip">Copia</button></div>
              <div class="os-net-card-val" id="net-local-ip">...</div>
            </div>
            <div class="os-net-card">
              <div class="os-net-card-label"><span>IP Pubblico WAN</span><button type="button" class="os-net-copy-btn" data-copy-target="net-public-ip">Copia</button></div>
              <div class="os-net-card-val" id="net-public-ip">...</div>
            </div>
            <div class="os-net-card">
              <div class="os-net-card-label"><span>Latenza Ping</span></div>
              <div class="os-net-card-val" id="net-ping" style="color:#34d399;">...</div>
            </div>
            <div class="os-net-card">
              <div class="os-net-card-label"><span>Hostname</span></div>
              <div class="os-net-card-val" id="net-hostname">...</div>
            </div>
            <div class="os-net-card">
              <div class="os-net-card-label"><span>Server DNS</span></div>
              <div class="os-net-card-val" id="net-dns" style="font-size:13px;">...</div>
            </div>
            <div class="os-net-card">
              <div class="os-net-card-label"><span>Traffico I/O</span></div>
              <div class="os-net-card-val" style="font-size:13px;">↓ <span id="net-traffic-rx">...</span> &nbsp;|&nbsp; ↑ <span id="net-traffic-tx">...</span></div>
              <div style="font-size:11px;opacity:0.7;margin-top:2px;" id="net-traffic-packets">...</div>
            </div>
          </div>
          <div class="os-net-section-title">Interfacce Fisiche &amp; Virtuali</div>
          <div style="overflow-x:auto;border-radius:var(--os-radius-md);border:1px solid var(--md-sys-color-outline-variant);">
            <table class="os-net-iface-table">
              <thead><tr><th>Interfaccia</th><th>Indirizzo IPv4</th><th>MAC</th><th>Velocità / MTU</th><th>Stato</th></tr></thead>
              <tbody id="net-interfaces-tbody"><tr><td colspan="5" style="text-align:center;opacity:0.6;">Caricamento...</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const closeBtn = document.getElementById("btn-network-close");
    const refBtn = document.getElementById("btn-network-refresh");
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (refBtn) refBtn.addEventListener("click", fetchDiagnostics);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });

    modal.querySelectorAll(".os-net-copy-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-copy-target");
        const targetEl = document.getElementById(targetId);
        if (targetEl) copyText(targetEl.textContent.trim(), btn);
      });
    });

    return modal;
  }

  async function fetchDiagnostics() {
    const refBtn = btnRefresh();
    if (refBtn) refBtn.classList.add("is-spinning");
    try {
      const res = await fetch(`/api/setup/network?t=${Date.now()}`);
      if (!res.ok) return;
      const data = await res.json();
      renderDiagnostics(data);
    } catch (e) {
    } finally {
      if (refBtn) setTimeout(() => refBtn.classList.remove("is-spinning"), 300);
    }
  }

  function copyText(val, btn) {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(val).then(() => {
      const orig = btn.textContent;
      btn.textContent = "✓";
      setTimeout(() => { btn.textContent = orig; }, 1200);
    }).catch(() => {});
  }

  function renderDiagnostics(data) {
    const localIpEl = document.getElementById("net-local-ip");
    const publicIpEl = document.getElementById("net-public-ip");
    const pingEl = document.getElementById("net-ping");
    const hostnameEl = document.getElementById("net-hostname");
    const dnsEl = document.getElementById("net-dns");
    const trafficRxEl = document.getElementById("net-traffic-rx");
    const trafficTxEl = document.getElementById("net-traffic-tx");
    const packetsEl = document.getElementById("net-traffic-packets");
    const ifaceTbody = document.getElementById("net-interfaces-tbody");

    if (localIpEl) localIpEl.textContent = data.local_ip || "127.0.0.1";
    if (publicIpEl) publicIpEl.textContent = data.public_ip || "Offline";
    if (pingEl) pingEl.textContent = data.ping_ms > 0 ? `${data.ping_ms} ms` : "—";
    if (hostnameEl) hostnameEl.textContent = data.hostname || "localhost";
    if (dnsEl) dnsEl.textContent = (data.dns || []).join(" • ");

    if (data.traffic) {
      if (trafficRxEl) trafficRxEl.textContent = data.traffic.bytes_recv_fmt || "0 B";
      if (trafficTxEl) trafficTxEl.textContent = data.traffic.bytes_sent_fmt || "0 B";
      if (packetsEl) {
        packetsEl.textContent = `↓ ${data.traffic.packets_recv.toLocaleString()} pkts  |  ↑ ${data.traffic.packets_sent.toLocaleString()} pkts`;
      }
    }

    if (ifaceTbody) {
      ifaceTbody.innerHTML = "";
      const ifaces = data.interfaces || [];
      if (ifaces.length === 0) {
        const row = document.createElement("tr");
        row.innerHTML = '<td colspan="5" style="text-align: center; opacity: 0.6;">Nessuna interfaccia attiva rilevata</td>';
        ifaceTbody.appendChild(row);
      } else {
        ifaces.forEach((iface) => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td><strong>${escapeHtml(iface.name)}</strong></td>
            <td>${escapeHtml(iface.ip)}</td>
            <td><small style="opacity: 0.7;">${escapeHtml(iface.mac || "—")}</small></td>
            <td>${iface.speed_mbps}M / MTU ${iface.mtu}</td>
            <td><span class="os-net-badge-up">${iface.is_up ? "UP" : "DOWN"}</span></td>
          `;
          ifaceTbody.appendChild(row);
        });
      }
    }
  }

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function openModal() {
    const m = ensureModal();
    m.classList.add("is-open");
    fetchDiagnostics();
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove("is-open");
  }

  function init() {
    const fabBtn = document.getElementById("btn-network-fab");
    if (fabBtn) fabBtn.addEventListener("click", openModal);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal && modal.classList.contains("is-open")) {
        closeModal();
      }
    });
  }

  window.SetupNetwork = {
    open: openModal,
    close: closeModal,
    refresh: fetchDiagnostics
  };

  document.addEventListener("DOMContentLoaded", init);
})();
