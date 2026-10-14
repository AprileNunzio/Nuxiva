(() => {
  "use strict";

  class OscilloscopeCanvas {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.bins = new Array(64).fill(0.05);
      this.laserY = 0.75;
      this.running = false;
      this.phase = 0;
    }

    start() {
      if (this.running) return;
      this.running = true;
      const render = () => {
        if (!this.running) return;
        this.draw();
        requestAnimationFrame(render);
      };
      requestAnimationFrame(render);
    }

    stop() {
      this.running = false;
    }

    update(bins, thresholdNorm) {
      if (bins && bins.length) this.bins = bins;
      if (thresholdNorm !== undefined) this.laserY = thresholdNorm;
    }

    draw() {
      const { width: w, height: h } = this.canvas;
      const ctx = this.ctx;
      ctx.clearRect(0, 0, w, h);

      const gradBg = ctx.createLinearGradient(0, 0, 0, h);
      gradBg.addColorStop(0, "rgba(2,10,20,0.7)");
      gradBg.addColorStop(1, "rgba(5,20,35,0.85)");
      ctx.fillStyle = gradBg;
      ctx.fillRect(0, 0, w, h);

      const barW = (w / 64) - 2;
      for (let i = 0; i < 64; i++) {
        const x = i * (barW + 2);
        const val = this.bins[i] || 0.05;
        const barH = val * (h * 0.7);
        const y = h - barH;
        const isVoice = i >= 8 && i <= 36;
        ctx.fillStyle = isVoice ? "rgba(0,240,255,0.65)" : "rgba(80,120,160,0.3)";
        ctx.fillRect(x, y, barW, barH);
      }

      ctx.save();
      ctx.beginPath();
      ctx.strokeStyle = "#00f0ff";
      ctx.lineWidth = 2.5;
      ctx.shadowColor = "#00f0ff";
      ctx.shadowBlur = 10;
      this.phase += 0.08;
      const midY = h * 0.45;
      for (let x = 0; x < w; x += 4) {
        const binIdx = Math.floor((x / w) * 64);
        const amp = (this.bins[binIdx] || 0.1) * 45;
        const y = midY + Math.sin(x * 0.04 + this.phase) * amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      ctx.beginPath();
      ctx.strokeStyle = "rgba(180,100,255,0.7)";
      ctx.lineWidth = 1.8;
      for (let x = 0; x < w; x += 4) {
        const binIdx = Math.floor((x / w) * 64);
        const amp = (this.bins[binIdx] || 0.1) * 35;
        const y = midY - Math.sin(x * 0.04 + this.phase * 1.2) * amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.restore();

      const lineY = h * (1.0 - this.laserY);
      ctx.save();
      ctx.beginPath();
      ctx.strokeStyle = "#ff3366";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.shadowColor = "#ff3366";
      ctx.shadowBlur = 8;
      ctx.moveTo(0, lineY);
      ctx.lineTo(w, lineY);
      ctx.stroke();
      ctx.fillStyle = "#ff3366";
      ctx.font = ["10px", "monospace"].join(" ");
      ctx.fillText("VAD LASER THRESHOLD", 12, lineY - 6);
      ctx.restore();
    }
  }

  class BiometricRadarCanvas {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.points = new Array(128).fill(0.3);
      this.running = false;
      this.rot = 0;
    }

    start() {
      if (this.running) return;
      this.running = true;
      const render = () => {
        if (!this.running) return;
        this.draw();
        requestAnimationFrame(render);
      };
      requestAnimationFrame(render);
    }

    stop() {
      this.running = false;
    }

    update(points) {
      if (points && points.length) this.points = points;
    }

    draw() {
      const { width: w, height: h } = this.canvas;
      const ctx = this.ctx;
      const cx = w / 2;
      const cy = h / 2;
      const maxR = Math.min(cx, cy) * 0.85;

      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate(cx, cy);

      ctx.strokeStyle = "rgba(0,240,255,0.15)";
      ctx.lineWidth = 1;
      for (let r of [maxR * 0.33, maxR * 0.66, maxR]) {
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.stroke();
      }

      this.rot += 0.015;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, maxR, this.rot, this.rot + 0.5);
      ctx.closePath();
      ctx.fillStyle = "rgba(0,240,255,0.08)";
      ctx.fill();

      ctx.beginPath();
      const n = this.points.length;
      for (let i = 0; i < n; i++) {
        const angle = (i / n) * Math.PI * 2;
        const rad = maxR * (0.2 + this.points[i] * 0.8);
        const px = Math.cos(angle) * rad;
        const py = Math.sin(angle) * rad;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = "rgba(0,240,255,0.22)";
      ctx.fill();
      ctx.strokeStyle = "#00f0ff";
      ctx.lineWidth = 2;
      ctx.shadowColor = "#00f0ff";
      ctx.shadowBlur = 12;
      ctx.stroke();
      ctx.restore();
    }
  }

  class NeuralSpikeCanvas {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.nodes = [];
      this.links = [];
      this.running = false;
      this.initNodes(8);
    }

    initNodes(count) {
      const { width: w, height: h } = this.canvas;
      this.nodes = [];
      this.links = [];
      for (let i = 0; i < count; i++) {
        this.nodes.push({
          x: 40 + Math.random() * (w - 80),
          y: 40 + Math.random() * (h - 80),
          vx: (Math.random() - 0.5) * 0.8,
          vy: (Math.random() - 0.5) * 0.8,
          potential: Math.random(),
          size: 4 + Math.random() * 4
        });
      }
      for (let i = 0; i < count; i++) {
        for (let j = i + 1; j < count; j++) {
          if (Math.random() < 0.45) this.links.push([i, j]);
        }
      }
    }

    start() {
      if (this.running) return;
      this.running = true;
      const render = () => {
        if (!this.running) return;
        this.draw();
        requestAnimationFrame(render);
      };
      requestAnimationFrame(render);
    }

    stop() {
      this.running = false;
    }

    setPreset(name) {
      const counts = {
        "nuxiva-5.0-veloce": 6,
        "nuxiva-5.0-empatico": 10,
        "nuxiva-6.0-pro": 14,
        "nuxiva-6.5-ultra": 20,
        "nuxiva-6.5-auto": 12
      };
      this.initNodes(counts[name] || 10);
    }

    draw() {
      const { width: w, height: h } = this.canvas;
      const ctx = this.ctx;
      ctx.clearRect(0, 0, w, h);

      for (let node of this.nodes) {
        node.x += node.vx;
        node.y += node.vy;
        if (node.x < 20 || node.x > w - 20) node.vx *= -1;
        if (node.y < 20 || node.y > h - 20) node.vy *= -1;
        node.potential = (node.potential + 0.02) % 1.0;
      }

      ctx.save();
      for (let [i, j] of this.links) {
        const a = this.nodes[i];
        const b = this.nodes[j];
        if (!a || !b) continue;
        const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
        grad.addColorStop(0, "rgba(0,240,255,0.35)");
        grad.addColorStop(1, "rgba(180,100,255,0.35)");
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }

      for (let node of this.nodes) {
        ctx.beginPath();
        const glow = node.potential > 0.8;
        ctx.arc(node.x, node.y, node.size * (glow ? 1.5 : 1.0), 0, Math.PI * 2);
        ctx.fillStyle = glow ? "#ffffff" : "#00f0ff";
        ctx.shadowColor = glow ? "#ff3366" : "#00f0ff";
        ctx.shadowBlur = glow ? 16 : 6;
        ctx.fill();
      }
      ctx.restore();
    }
  }

  window.SetupCanvas = {
    Oscilloscope: OscilloscopeCanvas,
    BiometricRadar: BiometricRadarCanvas,
    NeuralSpike: NeuralSpikeCanvas
  };
})();
