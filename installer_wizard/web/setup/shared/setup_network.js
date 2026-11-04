(() => {
  "use strict";

  const modal = document.getElementById("os-network-modal");
  const fab = document.getElementById("btn-network-fab");
  const btnClose = document.getElementById("btn-network-close");
  const btnRefresh = document.getElementById("btn-network-refresh");

  async function fetchDiagnostics() {
    if (btnRefresh) {
      btnRefresh.classList.add("is-spinning");
    }
    try {
      const res = await fetch(`/api/setup/network?t=${Date.now()}`);
      if (!res.ok) return;
      const data = await res.json();
      renderDiagnostics(data);
    } catch (e) {
    } finally {
      if (btnRefresh) {
        setTimeout(() => btnRefresh.classList.remove("is-spinning"), 300);
      }
    }
  }

  function copyText(val, btn) {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(val).then(() => {
      const orig = btn.textContent;
      btn.textContent = "✓";
      setTimeout(() => {
        btn.textContent = orig;
      }, 1200);
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
    if (!modal) return;
    modal.classList.add("is-open");
    fetchDiagnostics();
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove("is-open");
  }

  function init() {
    const fabBtn = document.getElementById("btn-network-fab");
    const closeBtn = document.getElementById("btn-network-close");
    const refreshBtn = document.getElementById("btn-network-refresh");
    const netModal = document.getElementById("os-network-modal");

    if (fabBtn) fabBtn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (refreshBtn) refreshBtn.addEventListener("click", fetchDiagnostics);

    if (netModal) {
      netModal.addEventListener("click", (e) => {
        if (e.target === netModal) closeModal();
      });
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && netModal && netModal.classList.contains("is-open")) {
        closeModal();
      }
    });

    document.querySelectorAll(".os-net-copy-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-copy-target");
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          copyText(targetEl.textContent.trim(), btn);
        }
      });
    });
  }

  window.SetupNetwork = {
    open: openModal,
    close: closeModal,
    refresh: fetchDiagnostics
  };

  document.addEventListener("DOMContentLoaded", init);
})();
