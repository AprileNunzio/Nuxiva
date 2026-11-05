(() => {
  "use strict";

  const bus = window.NuxivaOSEventBus;

  class TaskbarManager {
    constructor() {
      this.el = null;
      this.startBtn = null;
      this.tasksContainer = null;
      this.trayContainer = null;
      this.clockEl = null;
      this.activeTasks = new Map();
      this.clockTimer = null;
      this._init();
    }

    _init() {
      this.el = document.getElementById("nux-taskbar");
      if (!this.el) {
        this.el = document.createElement("nav");
        this.el.id = "nux-taskbar";
        this.el.className = "nux-taskbar";
        this.el.setAttribute("role", "navigation");
        this.el.setAttribute("aria-label", "Taskbar");
        document.body.appendChild(this.el);
      }

      this._buildLayout();
      this._bindBusEvents();
      this._startClock();
    }

    _buildLayout() {
      this.el.replaceChildren();

      this.startBtn = document.createElement("button");
      this.startBtn.id = "nux-start-btn";
      this.startBtn.className = "nux-start-btn";
      this.startBtn.setAttribute("aria-label", "Start Menu");
      this.startBtn.innerHTML = `<span class="nux-logo-icon">❖</span><span class="nux-start-text">Nuxiva</span>`;
      this.startBtn.onclick = () => bus.emit("os:taskbar:launcher-toggle");

      this.tasksContainer = document.createElement("div");
      this.tasksContainer.className = "nux-taskbar-tasks";

      this.trayContainer = document.createElement("div");
      this.trayContainer.className = "nux-taskbar-tray";

      const notifBtn = document.createElement("button");
      notifBtn.id = "nux-tray-notif";
      notifBtn.className = "nux-tray-item";
      notifBtn.setAttribute("aria-label", "Notifications");
      notifBtn.innerHTML = `🔔<span id="nux-notif-badge" class="nux-badge" hidden>0</span>`;
      notifBtn.onclick = () => bus.emit("os:tray:notifications-toggle");

      const sysInfo = document.createElement("div");
      sysInfo.id = "nux-tray-sys";
      sysInfo.className = "nux-tray-item mono";
      sysInfo.innerHTML = `<span id="nux-sys-mem">--%</span>`;

      this.clockEl = document.createElement("div");
      this.clockEl.className = "nux-tray-clock";

      this.trayContainer.append(notifBtn, sysInfo, this.clockEl);
      this.el.append(this.startBtn, this.tasksContainer, this.trayContainer);
    }

    _bindBusEvents() {
      bus.on("os:window:open", (data) => {
        if (!data || !data.id) return;
        this._addTask(data.id, data.title, data.appId);
      });

      bus.on("os:window:focused", (data) => {
        if (!data || !data.id) return;
        this._setActive(data.id);
      });

      bus.on("os:window:minimized", (data) => {
        if (!data || !data.id) return;
        const task = this.activeTasks.get(data.id);
        if (task) task.classList.remove("active");
      });

      bus.on("os:window:closed", (data) => {
        if (!data || !data.id) return;
        this._removeTask(data.id);
      });

      bus.on("os:service:update", (data) => {
        if (!data) return;
        const memEl = document.getElementById("nux-sys-mem");
        if (memEl && data.memory_percent !== undefined) {
          memEl.textContent = `${Math.round(data.memory_percent)}%`;
        }
        const badge = document.getElementById("nux-notif-badge");
        if (badge && data.notifications_count !== undefined) {
          badge.textContent = `${data.notifications_count}`;
          badge.hidden = data.notifications_count <= 0;
        }
      });
    }

    _addTask(id, title, appId) {
      if (this.activeTasks.has(id)) return;

      const btn = document.createElement("button");
      btn.id = `task_${id}`;
      btn.className = "nux-task-item active";
      btn.setAttribute("aria-label", title);
      btn.innerHTML = `<span class="nux-task-icon">${this._appIcon(appId)}</span><span class="nux-task-title">${this._escape(title)}</span>`;
      btn.onclick = () => bus.emit("os:window:request-toggle", { id });

      this.tasksContainer.appendChild(btn);
      this.activeTasks.set(id, btn);
    }

    _setActive(id) {
      this.activeTasks.forEach((btn, taskId) => {
        btn.classList.toggle("active", taskId === id);
      });
    }

    _removeTask(id) {
      const btn = this.activeTasks.get(id);
      if (btn) {
        btn.remove();
        this.activeTasks.delete(id);
      }
    }

    _startClock() {
      const update = () => {
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        const dateStr = now.toLocaleDateString([], { month: "short", day: "numeric" });
        if (this.clockEl) {
          this.clockEl.innerHTML = `<b>${timeStr}</b><small>${dateStr}</small>`;
        }
      };
      update();
      this.clockTimer = setInterval(update, 1000);
    }

    _appIcon(appId) {
      const icons = {
        chat: "💬",
        brain: "🧠",
        agency: "⚡",
        settings: "⚙",
        weather: "⛅",
        camera: "📷",
      };
      return icons[appId] || "🗔";
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

  window.NuxivaTaskbarManager = new TaskbarManager();
})();
