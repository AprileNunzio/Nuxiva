import { bus } from "./bus.js";

export class DownloadMeterWidget {
  constructor() {
    this.hideTimer = null;
  }

  mount() {
    bus.on("log:message", (text) => this.parseLogForDownload(text));
  }

  parseLogForDownload(text) {
    if (!text || typeof text !== "string") return;

    const curlMatch = text.match(/([0-9]{1,3}\.[0-9]%|[0-9]{1,3}%)\s+([0-9.]+[kMGT]?)\s+([0-9.]+[kMGT]?\/s)/i);
    const wgetMatch = text.match(/([0-9]{1,3}%)\s+([0-9.]+[kMGT]?)\s+([0-9.]+[kMGT]?\/s)/i);
    const piperMatch = text.match(/([0-9]+)\/([0-9]+)\s+bytes\s+\(([0-9.]+)%\)\s+([0-9.]+\s+[A-Za-z]+\/s)/i);
    const generalMatch = text.match(/(?:download|fetch|pulling)[^:]*:\s*([0-9]{1,3})%/i);

    if (curlMatch || wgetMatch) {
      const match = curlMatch || wgetMatch;
      const pct = parseFloat(match[1]);
      const speed = match[3];
      this.show(pct, speed, "");
    } else if (piperMatch) {
      const pct = parseFloat(piperMatch[3]);
      const curMb = (parseInt(piperMatch[1], 10) / 1048576).toFixed(1);
      const totMb = (parseInt(piperMatch[2], 10) / 1048576).toFixed(1);
      const speed = piperMatch[4];
      this.show(pct, speed, `${curMb} / ${totMb} MB`);
    } else if (generalMatch) {
      const pct = parseFloat(generalMatch[1]);
      this.show(pct, "", "");
    }
  }

  show(percent, speed, stats) {
    const elMeter = document.getElementById("os-download-strip");
    const elFill = document.getElementById("download-fill");
    const elSpeed = document.getElementById("download-speed-lbl");
    const elStats = document.getElementById("download-stats-lbl");

    if (!elMeter) return;
    elMeter.classList.add("active");
    if (elFill) elFill.style.width = `${percent}%`;
    if (elSpeed && speed) elSpeed.textContent = speed;
    if (elStats && stats) elStats.textContent = stats;

    if (this.hideTimer) clearTimeout(this.hideTimer);
    if (percent >= 100) {
      this.hideTimer = setTimeout(() => {
        elMeter.classList.remove("active");
      }, 3000);
    } else {
      this.hideTimer = setTimeout(() => {
        elMeter.classList.remove("active");
      }, 15000);
    }
  }
}
