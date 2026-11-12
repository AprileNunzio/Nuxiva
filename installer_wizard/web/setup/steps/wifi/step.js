(() => {
  "use strict";

  class StepWifi {
    constructor() {
      this.status = {
        has_wifi: true,
        is_cable_connected: false,
        cable: {},
        is_optional: false,
        wifi_connected: false,
        current_ssid: null,
        networks: [],
        can_proceed: true
      };
      this.selectedSsid = null;
      this.isScanning = false;
      this.initialized = false;
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepWifiI18n && window.SetupStepWifiI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    applyTranslations() {
      this.render();
    }

    canProceed() {
      if (this.status.is_cable_connected) return true;
      if (this.status.wifi_connected) return true;
      if (!this.status.has_wifi && this.status.is_cable_connected) return true;
      return false;
    }

    async fetchStatus() {
      try {
        const res = await fetch(`/api/setup/wifi/status?t=${Date.now()}`);
        if (!res.ok) return;
        this.status = await res.json();
        if (this.status.current_ssid) {
          window.SetupStorage.set("wifiSsid", this.status.current_ssid);
        }
        if (this.status.is_cable_connected) {
          window.SetupStorage.set("cableIp", this.status.cable?.ip || "");
        }
        this.render();
      } catch (e) {
      }
    }

    async triggerScan() {
      const btn = document.getElementById("btn-wifi-refresh");
      if (btn) btn.classList.add("is-spinning");
      this.isScanning = true;
      try {
        const res = await fetch("/api/setup/wifi/scan", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Nuxiva-Request": "1"
          }
        });
        if (res.ok) {
          const data = await res.json();
          this.status.networks = data.networks || [];
          if (data.current_ssid) this.status.current_ssid = data.current_ssid;
          this.render();
        }
      } catch (e) {
      } finally {
        this.isScanning = false;
        if (btn) setTimeout(() => btn.classList.remove("is-spinning"), 300);
      }
    }

    async connectNetwork(ssid, password, feedbackEl, btnEl) {
      if (!password && !confirm("Connettersi senza password?")) return;
      if (btnEl) {
        btnEl.disabled = true;
        btnEl.textContent = this.t("btn_connecting");
      }
      if (feedbackEl) {
        feedbackEl.textContent = "";
        feedbackEl.className = "os-wifi-feedback";
      }

      try {
        const res = await fetch("/api/setup/wifi/connect", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Nuxiva-Request": "1"
          },
          body: JSON.stringify({ ssid, password })
        });
        const data = await res.json();
        if (data.success) {
          this.status.wifi_connected = true;
          this.status.current_ssid = ssid;
          window.SetupStorage.set("wifiSsid", ssid);
          if (feedbackEl) {
            feedbackEl.textContent = `✓ ${this.t("connected")}: ${ssid}`;
            feedbackEl.classList.add("is-success");
          }
          setTimeout(() => this.fetchStatus(), 1200);
        } else {
          if (feedbackEl) {
            feedbackEl.textContent = data.error || this.t("err_failed");
          }
        }
      } catch (err) {
        if (feedbackEl) {
          feedbackEl.textContent = this.t("err_failed");
        }
      } finally {
        if (btnEl) {
          btnEl.disabled = false;
          btnEl.textContent = this.t("btn_connect");
        }
      }
    }

    getSignalIcon(sig) {
      const bars = sig >= 75 ? 4 : sig >= 50 ? 3 : sig >= 25 ? 2 : 1;
      return `
        <svg class="os-wifi-sig-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12.55a11 11 0 0 1 14.08 0" stroke-opacity="${bars >= 4 ? '1' : '0.25'}"></path>
          <path d="M1.42 9a16 16 0 0 1 21.16 0" stroke-opacity="${bars >= 3 ? '1' : '0.25'}"></path>
          <path d="M8.53 16.11a6 6 0 0 1 6.95 0" stroke-opacity="${bars >= 2 ? '1' : '0.25'}"></path>
          <line x1="12" y1="20" x2="12.01" y2="20" stroke-width="3"></line>
        </svg>
      `;
    }

    render() {
      const cableBanner = document.getElementById("wifi-cable-banner");
      const warnBanner = document.getElementById("wifi-warn-banner");
      const listBox = document.getElementById("wifi-networks-list");
      const cableIpSpan = document.getElementById("wifi-cable-ip");

      if (this.status.is_cable_connected) {
        if (cableBanner) cableBanner.style.display = "flex";
        if (warnBanner) warnBanner.style.display = "none";
        if (cableIpSpan) cableIpSpan.textContent = this.status.cable?.ip || "";
      } else {
        if (cableBanner) cableBanner.style.display = "none";
        if (warnBanner) warnBanner.style.display = "flex";
      }

      if (!listBox) return;
      listBox.innerHTML = "";

      if (!this.status.has_wifi) {
        const empty = document.createElement("div");
        empty.className = "os-wifi-empty-state";
        if (this.status.is_cable_connected) {
          empty.innerHTML = `<strong>${this.t("cable_only_title")}</strong><p style="margin-top:6px;opacity:0.8;">${this.t("cable_only_sub").replace("{ip}", this.status.cable?.ip || "")}</p>`;
        } else {
          empty.innerHTML = `<strong>${this.t("no_net_title")}</strong><p style="margin-top:6px;opacity:0.8;">${this.t("no_net_sub")}</p>`;
        }
        listBox.appendChild(empty);
        return;
      }

      const nets = this.status.networks || [];
      if (nets.length === 0) {
        const empty = document.createElement("div");
        empty.className = "os-wifi-empty-state";
        empty.textContent = this.isScanning ? this.t("scanning") : this.t("empty_networks");
        listBox.appendChild(empty);
        return;
      }

      nets.forEach((net) => {
        const isConn = Boolean(net.is_connected || (this.status.current_ssid && this.status.current_ssid === net.ssid));
        const isSel = this.selectedSsid === net.ssid;

        const card = document.createElement("div");
        card.className = `os-wifi-item-card ${isSel ? "is-selected" : ""}`;

        const row = document.createElement("div");
        row.className = "os-wifi-item-row";
        row.innerHTML = `
          <div class="os-wifi-item-left">
            ${this.getSignalIcon(net.signal || 70)}
            <div class="os-wifi-item-info">
              <span class="os-wifi-item-ssid">${escapeHtml(net.ssid)}</span>
              <span class="os-wifi-item-meta">${net.security || "WPA2"} • ${net.frequency || "2.4 GHz"} • ${net.signal}%</span>
            </div>
          </div>
          <div class="os-wifi-item-right">
            ${isConn ? `<span class="os-wifi-badge-conn">✓ ${this.t("connected")}</span>` : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity:0.5;"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>`}
          </div>
        `;

        row.addEventListener("click", () => {
          this.selectedSsid = this.selectedSsid === net.ssid ? null : net.ssid;
          this.render();
        });

        card.appendChild(row);

        if (isSel) {
          const panel = document.createElement("div");
          panel.className = "os-wifi-conn-panel";
          panel.innerHTML = `
            <div class="os-wifi-input-row">
              <input type="password" class="os-wifi-pwd-input" placeholder="${this.t("pwd_placeholder")}" value="" />
              <button type="button" class="os-btn-wifi-connect">${this.t("btn_connect")}</button>
            </div>
            <div class="os-wifi-feedback"></div>
          `;

          const pwdInput = panel.querySelector(".os-wifi-pwd-input");
          const btnConn = panel.querySelector(".os-btn-wifi-connect");
          const fbEl = panel.querySelector(".os-wifi-feedback");

          if (btnConn && pwdInput) {
            btnConn.addEventListener("click", () => {
              this.connectNetwork(net.ssid, pwdInput.value, fbEl, btnConn);
            });
            pwdInput.addEventListener("keydown", (e) => {
              if (e.key === "Enter") {
                this.connectNetwork(net.ssid, pwdInput.value, fbEl, btnConn);
              }
            });
          }

          card.appendChild(panel);
        }

        listBox.appendChild(card);
      });
    }

    init() {
      if (!this.initialized) {
        this.initialized = true;
        const btnRef = document.getElementById("btn-wifi-refresh");
        if (btnRef) btnRef.addEventListener("click", () => this.triggerScan());
      }
      this.fetchStatus();
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

  window.SetupStepWifi = new StepWifi();
})();