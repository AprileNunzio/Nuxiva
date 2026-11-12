import { bus } from "./bus.js";

export class ProgressManager {
  constructor() {
    this.currentPercent = 0;
    this.targetPercent = 0;
    this.rafId = null;
  }

  mount() {
    bus.on("journey:progress", (data) => this.onProgress(data));
    this.loop();
  }

  onProgress(data) {
    if (typeof data.percent === "number") {
      this.targetPercent = Math.max(0, Math.min(100, data.percent));
    }
  }

  loop() {
    const diff = this.targetPercent - this.currentPercent;
    if (Math.abs(diff) > 0.1) {
      this.currentPercent += diff * 0.12;
      this.render();
    } else if (this.currentPercent !== this.targetPercent) {
      this.currentPercent = this.targetPercent;
      this.render();
    }
    this.rafId = requestAnimationFrame(() => this.loop());
  }

  render() {
    const p = Math.round(this.currentPercent);
    const elFill = document.getElementById("os-progress-fill");
    const elVal = document.getElementById("os-progress-pct");
    const elTime = document.getElementById("os-progress-time");

    if (elFill) elFill.style.width = `${this.currentPercent}%`;
    if (elVal) elVal.textContent = `${p}%`;
    if (elTime) {
      if (p >= 100) {
        elTime.textContent = "Completato";
      } else if (p > 85) {
        elTime.textContent = "Meno di un minuto rimanente";
      } else if (p > 50) {
        elTime.textContent = "Circa 2 minuti rimanenti";
      } else if (p > 20) {
        elTime.textContent = "Circa 4 minuti rimanenti";
      } else {
        elTime.textContent = "Calcolo del tempo rimanente...";
      }
    }
  }

  unmount() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }
}
