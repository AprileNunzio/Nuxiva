(() => {
  "use strict";

  const MIN_DB = -100;

  class LiveScope {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.analyser = null;
      this.marks = [];
      this.frame = 0;
    }

    attach(analyser) {
      this.analyser = analyser;
      this.freq = new Uint8Array(analyser.frequencyBinCount);
      this.wave = new Float32Array(analyser.fftSize);
      this.start();
    }

    setMarks(marks) {
      this.marks = marks;
    }

    start() {
      if (this.frame) return;
      const loop = () => {
        this.draw();
        this.frame = requestAnimationFrame(loop);
      };
      this.frame = requestAnimationFrame(loop);
    }

    stop() {
      if (this.frame) cancelAnimationFrame(this.frame);
      this.frame = 0;
      this.analyser = null;
      this.draw();
    }

    yOf(db, h) {
      return h - ((Math.max(MIN_DB, Math.min(0, db)) - MIN_DB) / -MIN_DB) * h;
    }

    draw() {
      const { width: w, height: h } = this.canvas;
      const ctx = this.ctx;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "rgba(3,12,24,0.85)";
      ctx.fillRect(0, 0, w, h);
      if (!this.analyser) return;
      this.analyser.getByteFrequencyData(this.freq);
      const bars = 96;
      const step = Math.floor(this.freq.length / 2 / bars) || 1;
      const width = w / bars;
      for (let i = 0; i < bars; i++) {
        const value = this.freq[i * step] / 255;
        ctx.fillStyle = `rgba(0,240,255,${0.25 + value * 0.6})`;
        ctx.fillRect(i * width, h - value * h * 0.9, width - 1.5, value * h * 0.9);
      }
      this.analyser.getFloatTimeDomainData(this.wave);
      ctx.beginPath();
      ctx.strokeStyle = "#b464ff";
      ctx.lineWidth = 1.6;
      const stride = this.wave.length / w;
      for (let x = 0; x < w; x++) {
        const y = h / 2 - this.wave[Math.floor(x * stride)] * h * 0.45;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.font = "11px monospace";
      this.marks.forEach((mark) => {
        const y = this.yOf(mark.db, h);
        ctx.strokeStyle = mark.color;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = mark.color;
        ctx.fillText(`${mark.label} ${mark.db.toFixed(1)} dBFS`, 10, y - 5);
      });
    }
  }

  window.SetupCanvas = Object.freeze({ LiveScope });
})();
