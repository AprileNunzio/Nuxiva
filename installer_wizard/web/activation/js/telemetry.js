import { bus } from "./bus.js";

export class TelemetryWidget {
  constructor() {
    this.timer = null;
    this.elIp = document.getElementById("dock-ip");
    this.elHost = document.getElementById("dock-host");
    this.elPing = document.getElementById("dock-ping");
    this.elCpu = document.getElementById("dock-cpu");
    this.elRam = document.getElementById("dock-ram");
    this.elDisk = document.getElementById("dock-disk");
  }

  mount() {
    this.fetchData();
    this.timer = setInterval(() => this.fetchData(), 2000);
  }

  unmount() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  async fetchData() {
    try {
      const res = await fetch("/api/activation/telemetry");
      if (!res.ok) return;
      const data = await res.json();
      this.applyData(data);
      bus.emit("telemetry:updated", data);
    } catch (e) {
    }
  }

  applyData(data) {
    if (data.ip && this.elIp) this.elIp.textContent = data.ip;
    if (data.hostname && this.elHost) this.elHost.textContent = data.hostname;

    const ping = data.latency_ms ?? data.ping_ms;
    if (ping !== undefined && ping !== null && this.elPing) {
      this.elPing.textContent = `${Math.round(ping)} ms`;
    }

    const cpu = data.cpu_pct ?? data.cpu_percent;
    if (cpu !== undefined && this.elCpu) {
      this.elCpu.textContent = `${Math.round(cpu)}%`;
    }

    const ram = data.ram_pct ?? data.ram_percent;
    if (ram !== undefined && this.elRam) {
      this.elRam.textContent = `${Math.round(ram)}%`;
    }

    const disk = data.disk_free_gb !== undefined ? `${data.disk_free_gb} GB` : (data.disk_free || "");
    if (disk && this.elDisk) {
      this.elDisk.textContent = disk;
    }
  }
}
