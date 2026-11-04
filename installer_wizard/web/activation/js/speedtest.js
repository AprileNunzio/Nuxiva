import { bus } from "./bus.js";

export class SpeedtestWidget {
  constructor() {
    this.elPill = document.getElementById("dock-speedtest");
    this.elVal = document.getElementById("dock-speed");
    this.isRunning = false;
  }

  mount() {
    if (this.elPill) {
      this.elPill.addEventListener("click", () => this.runTest());
    }
    setTimeout(() => this.runTest(), 800);
  }

  async runTest() {
    if (this.isRunning) return;
    this.isRunning = true;
    if (this.elVal) {
      this.elVal.textContent = "...";
    }
    try {
      const res = await fetch("/api/activation/speedtest");
      if (res.ok) {
        const data = await res.json();
        const mbps = data.speed_mbps ?? data.mbps;
        const text = mbps !== undefined ? `${mbps} Mbps` : "OK";
        if (this.elVal) {
          this.elVal.textContent = text;
        }
        bus.emit("speedtest:completed", data);
      } else {
        if (this.elVal) this.elVal.textContent = "N/A";
      }
    } catch (e) {
      if (this.elVal) this.elVal.textContent = "Offline";
    } finally {
      this.isRunning = false;
    }
  }
}
