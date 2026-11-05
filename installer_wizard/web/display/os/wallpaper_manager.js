(() => {
  "use strict";

  const bus = window.NuxivaOSEventBus;

  class WallpaperManager {
    constructor() {
      this.el = null;
      this.canvas = null;
      this.ctx = null;
      this.mode = "ambient_gradient";
      this.particles = [];
      this.animId = null;
      this._init();
    }

    _init() {
      this.el = document.getElementById("nux-wallpaper-layer");
      if (!this.el) {
        this.el = document.createElement("div");
        this.el.id = "nux-wallpaper-layer";
        this.el.className = "nux-wallpaper-layer";
        document.body.prepend(this.el);
      }

      this.canvas = document.createElement("canvas");
      this.canvas.className = "nux-wallpaper-canvas";
      this.el.appendChild(this.canvas);
      this.ctx = this.canvas.getContext("2d");

      this._resizeCanvas();
      window.addEventListener("resize", () => this._resizeCanvas());

      this.el.addEventListener("pointerdown", (e) => {
        if (e.target === this.el || e.target === this.canvas) {
          bus.emit("os:desktop:clicked");
        }
      });

      bus.on("os:wallpaper:set-mode", (data) => {
        if (data && data.mode) this.setMode(data.mode, data.source, data.blur);
      });

      this.setMode("ambient_gradient");
    }

    _resizeCanvas() {
      if (!this.canvas) return;
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
      this._initParticles();
    }

    _initParticles() {
      this.particles = [];
      const count = Math.floor(window.innerWidth / 30);
      for (let i = 0; i < count; i++) {
        this.particles.push({
          x: Math.random() * this.canvas.width,
          y: Math.random() * this.canvas.height,
          radius: Math.random() * 2 + 0.5,
          speedX: (Math.random() - 0.5) * 0.4,
          speedY: (Math.random() - 0.5) * 0.4,
          alpha: Math.random() * 0.5 + 0.2,
        });
      }
    }

    setMode(mode, source = "", blur = false) {
      this.mode = mode;
      this.el.className = `nux-wallpaper-layer mode-${mode}${blur ? " blurred" : ""}`;

      if (this.animId) {
        cancelAnimationFrame(this.animId);
        this.animId = null;
      }

      if (mode === "custom_image" && source) {
        this.el.style.backgroundImage = `url("${source}")`;
      } else {
        this.el.style.backgroundImage = "";
      }

      if (mode === "hologram_particles" || mode === "ambient_gradient") {
        this.canvas.hidden = false;
        this._renderLoop();
      } else {
        this.canvas.hidden = true;
      }

      bus.emit("os:wallpaper:changed", { mode, source, blur });
    }

    _renderLoop() {
      if (!this.ctx || this.canvas.hidden) return;

      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      if (this.mode === "hologram_particles") {
        this.ctx.fillStyle = "rgba(0, 220, 255, 0.6)";
        this.particles.forEach((p) => {
          p.x += p.speedX;
          p.y += p.speedY;
          if (p.x < 0) p.x = this.canvas.width;
          if (p.x > this.canvas.width) p.x = 0;
          if (p.y < 0) p.y = this.canvas.height;
          if (p.y > this.canvas.height) p.y = 0;

          this.ctx.beginPath();
          this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          this.ctx.fillStyle = `rgba(0, 220, 255, ${p.alpha})`;
          this.ctx.fill();
        });
      }

      this.animId = requestAnimationFrame(() => this._renderLoop());
    }
  }

  window.NuxivaWallpaperManager = new WallpaperManager();
})();
