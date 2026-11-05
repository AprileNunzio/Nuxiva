(() => {
  "use strict";

  const bus = window.NuxivaOSEventBus;

  class ServicesManager {
    constructor() {
      this.pollTimer = null;
      this.lastNotifId = "";
      this._init();
    }

    _init() {
      this.poll();
      this.pollTimer = setInterval(() => this.poll(), 5000);

      bus.on("os:service:poll-now", () => this.poll());
    }

    async poll() {
      try {
        const resp = await fetch("/api/os/status", {
          headers: { Accept: "application/json" },
        });
        if (!resp.ok) return;
        const data = await resp.json();
        bus.emit("os:service:update", data);
      } catch (err) {
        bus.emit("os:service:offline", { error: String(err) });
      }

      this._checkNotifications();
    }

    async _checkNotifications() {
      try {
        const resp = await fetch("/api/os/notifications", {
          headers: { Accept: "application/json" },
        });
        if (!resp.ok) return;
        const data = await resp.json();
        const items = data.notifications || [];
        if (items.length > 0) {
          const newest = items[0];
          if (newest.id !== this.lastNotifId) {
            this.lastNotifId = newest.id;
            this._showToast(newest);
          }
        }
      } catch (err) {}
    }

    _showToast(item) {
      let toastContainer = document.getElementById("nux-toast-container");
      if (!toastContainer) {
        toastContainer = document.createElement("div");
        toastContainer.id = "nux-toast-container";
        toastContainer.className = "nux-toast-container";
        document.body.appendChild(toastContainer);
      }

      const toast = document.createElement("div");
      toast.className = `nux-toast level-${(item.level || "info").toLowerCase()}`;
      toast.setAttribute("role", "alert");
      toast.innerHTML = `
        <div class="nux-toast-head">
          <b>${item.level === "ERROR" ? "⚠" : "ℹ"} ${this._escape(item.label_key || "Alert")}</b>
          <button class="nux-toast-close">&times;</button>
        </div>
        <div class="nux-toast-body">${this._escape(item.message || "")}</div>
      `;

      toast.querySelector(".nux-toast-close").onclick = () => toast.remove();
      toastContainer.appendChild(toast);

      setTimeout(() => {
        if (toast.isConnected) toast.remove();
      }, 6000);
    }

    _escape(str) {
      return String(str).replace(/[&<>"']/g, (m) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[m]));
    }
  }

  window.NuxivaServicesManager = new ServicesManager();
})();
