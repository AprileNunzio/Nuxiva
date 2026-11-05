(() => {
  "use strict";

  const bus = window.NuxivaOSEventBus;

  class WindowManager {
    constructor() {
      this.windows = new Map();
      this.activeId = null;
      this.highestZ = 100;
      this.container = null;
      this._init();
    }

    _init() {
      this.container = document.getElementById("nux-window-layer");
      if (!this.container) {
        this.container = document.createElement("div");
        this.container.id = "nux-window-layer";
        this.container.className = "nux-window-layer";
        document.body.appendChild(this.container);
      }

      bus.on("os:window:request-focus", (data) => {
        if (data && data.id) this.focus(data.id);
      });

      bus.on("os:window:request-toggle", (data) => {
        if (data && data.id) this.toggle(data.id);
      });

      bus.on("os:window:request-close", (data) => {
        if (data && data.id) this.close(data.id);
      });

      window.addEventListener("resize", () => this._handleResize());
    }

    create(options = {}) {
      const id = options.id || `win_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
      if (this.windows.has(id)) {
        this.focus(id);
        return this.windows.get(id);
      }

      const title = options.title || "Window";
      const appId = options.app_id || "app";
      const width = Math.min(window.innerWidth - 40, options.width || 800);
      const height = Math.min(window.innerHeight - 100, options.height || 540);
      const x = options.x !== undefined ? options.x : Math.max(20, (window.innerWidth - width) / 2 + (this.windows.size * 24) % 120);
      const y = options.y !== undefined ? options.y : Math.max(30, (window.innerHeight - height) / 2 + (this.windows.size * 24) % 100);

      const winEl = document.createElement("section");
      winEl.id = id;
      winEl.className = "nux-window";
      winEl.style.width = `${width}px`;
      winEl.style.height = `${height}px`;
      winEl.style.left = `${x}px`;
      winEl.style.top = `${y}px`;
      winEl.style.zIndex = `${++this.highestZ}`;

      const header = document.createElement("header");
      header.className = "nux-win-header";

      const titleEl = document.createElement("span");
      titleEl.className = "nux-win-title";
      titleEl.textContent = title;

      const controls = document.createElement("div");
      controls.className = "nux-win-controls";

      const btnMin = document.createElement("button");
      btnMin.className = "nux-win-btn min";
      btnMin.setAttribute("aria-label", "Minimize");
      btnMin.innerHTML = "&minus;";
      btnMin.onclick = (e) => {
        e.stopPropagation();
        this.minimize(id);
      };

      const btnMax = document.createElement("button");
      btnMax.className = "nux-win-btn max";
      btnMax.setAttribute("aria-label", "Maximize");
      btnMax.innerHTML = "&#9633;";
      btnMax.onclick = (e) => {
        e.stopPropagation();
        this.toggleMaximize(id);
      };

      const btnClose = document.createElement("button");
      btnClose.className = "nux-win-btn close";
      btnClose.setAttribute("aria-label", "Close");
      btnClose.innerHTML = "&times;";
      btnClose.onclick = (e) => {
        e.stopPropagation();
        this.close(id);
      };

      controls.append(btnMin, btnMax, btnClose);
      header.append(titleEl, controls);

      const body = document.createElement("div");
      body.className = "nux-win-body";
      if (options.content instanceof HTMLElement) {
        body.appendChild(options.content);
      } else if (typeof options.content === "string") {
        body.innerHTML = options.content;
      }

      winEl.append(header, body);
      this.container.appendChild(winEl);

      const record = {
        id,
        title,
        appId,
        el: winEl,
        header,
        body,
        state: "normal",
        restoreBounds: { x, y, width, height },
      };

      this.windows.set(id, record);
      this._bindEvents(record);
      this.focus(id);

      bus.emit("os:window:open", { id, title, appId });
      return record;
    }

    _bindEvents(record) {
      const { id, el, header } = record;

      el.addEventListener("pointerdown", () => this.focus(id));

      let startX = 0, startY = 0, initX = 0, initY = 0, isDragging = false;
      header.addEventListener("pointerdown", (e) => {
        if (record.state === "maximized" || e.target.closest("button")) return;
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        initX = el.offsetLeft;
        initY = el.offsetTop;
        el.classList.add("dragging");
        header.setPointerCapture(e.pointerId);
      });

      header.addEventListener("pointermove", (e) => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        const newX = Math.max(0, Math.min(window.innerWidth - 80, initX + dx));
        const newY = Math.max(0, Math.min(window.innerHeight - 80, initY + dy));
        el.style.left = `${newX}px`;
        el.style.top = `${newY}px`;
        record.restoreBounds.x = newX;
        record.restoreBounds.y = newY;
      });

      const stopDrag = () => {
        if (!isDragging) return;
        isDragging = false;
        el.classList.remove("dragging");
      };
      header.addEventListener("pointerup", stopDrag);
      header.addEventListener("pointercancel", stopDrag);

      header.addEventListener("dblclick", (e) => {
        if (!e.target.closest("button")) this.toggleMaximize(id);
      });
    }

    focus(id) {
      const record = this.windows.get(id);
      if (!record) return;

      if (record.state === "minimized") {
        record.state = "normal";
        record.el.classList.remove("minimized");
      }

      this.highestZ += 1;
      record.el.style.zIndex = `${this.highestZ}`;
      this.windows.forEach((w) => w.el.classList.remove("active"));
      record.el.classList.add("active");
      this.activeId = id;

      bus.emit("os:window:focused", { id, title: record.title, appId: record.appId });
    }

    minimize(id) {
      const record = this.windows.get(id);
      if (!record) return;

      record.state = "minimized";
      record.el.classList.add("minimized");
      record.el.classList.remove("active");

      if (this.activeId === id) {
        this.activeId = null;
        const visible = [...this.windows.values()].filter((w) => w.state !== "minimized");
        if (visible.length > 0) {
          visible.sort((a, b) => (parseInt(a.el.style.zIndex, 10) || 0) - (parseInt(b.el.style.zIndex, 10) || 0));
          this.focus(visible[visible.length - 1].id);
        }
      }

      bus.emit("os:window:minimized", { id });
    }

    toggleMaximize(id) {
      const record = this.windows.get(id);
      if (!record) return;

      if (record.state === "maximized") {
        record.state = "normal";
        record.el.classList.remove("maximized");
        const b = record.restoreBounds;
        record.el.style.left = `${b.x}px`;
        record.el.style.top = `${b.y}px`;
        record.el.style.width = `${b.width}px`;
        record.el.style.height = `${b.height}px`;
        bus.emit("os:window:restored", { id });
      } else {
        record.restoreBounds = {
          x: record.el.offsetLeft,
          y: record.el.offsetTop,
          width: record.el.offsetWidth,
          height: record.el.offsetHeight,
        };
        record.state = "maximized";
        record.el.classList.add("maximized");
        bus.emit("os:window:maximized", { id });
      }
      this.focus(id);
    }

    toggle(id) {
      const record = this.windows.get(id);
      if (!record) return;

      if (this.activeId === id && record.state !== "minimized") {
        this.minimize(id);
      } else {
        this.focus(id);
      }
    }

    close(id) {
      const record = this.windows.get(id);
      if (!record) return;

      record.el.remove();
      this.windows.delete(id);
      if (this.activeId === id) this.activeId = null;

      bus.emit("os:window:closed", { id });
    }

    _handleResize() {
      this.windows.forEach((record) => {
        if (record.state === "normal") {
          const maxW = window.innerWidth - 20;
          const maxH = window.innerHeight - 60;
          if (record.el.offsetLeft > maxW) record.el.style.left = "20px";
          if (record.el.offsetTop > maxH) record.el.style.top = "30px";
        }
      });
    }
  }

  window.NuxivaWindowManager = new WindowManager();
})();
