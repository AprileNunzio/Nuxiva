import { bus } from "./bus.js";

export class TerminalWidget {
  constructor() {
    this.elLatest = document.getElementById("drawer-latest-msg");
    this.elBtn = document.getElementById("terminal-drawer-btn");
    this.elModal = document.getElementById("terminal-modal");
    this.elClose = document.getElementById("modal-close-btn");
    this.elLogs = document.getElementById("terminal-logs");
    this.maxLines = 250;
    this.lastRaw = "";
    this.lastCount = 1;
    this.lastMsgSpan = null;
  }

  mount() {
    if (this.elBtn && this.elModal) {
      this.elBtn.addEventListener("click", () => {
        this.elModal.classList.add("open");
      });
    }
    if (this.elClose && this.elModal) {
      this.elClose.addEventListener("click", () => {
        this.elModal.classList.remove("open");
      });
    }
    bus.on("log:message", (text) => this.appendLine(text));
  }

  appendLine(raw) {
    if (!raw) return;

    if (this.elLatest) {
      if (raw === this.lastRaw) {
        this.lastCount += 1;
        this.elLatest.textContent = `${raw} (x${this.lastCount})`;
      } else {
        this.elLatest.textContent = raw;
      }
    }

    if (!this.elLogs) return;

    if (raw === this.lastRaw && this.lastMsgSpan) {
      this.lastMsgSpan.textContent = `${raw} (x${this.lastCount})`;
      return;
    }

    this.lastRaw = raw;
    this.lastCount = 1;

    const line = document.createElement("div");
    line.className = "log-entry";

    const timeSpan = document.createElement("span");
    timeSpan.className = "log-time";
    const now = new Date();
    timeSpan.textContent = now.toTimeString().split(" ")[0];

    const msgSpan = document.createElement("span");
    msgSpan.className = "log-text";

    if (raw.includes("ERR") || raw.includes("fail") || raw.includes("Error")) {
      msgSpan.classList.add("error");
    } else if (raw.includes("OK") || raw.includes("success") || raw.includes("COMPLETED")) {
      msgSpan.classList.add("success");
    } else if (raw.includes("[JOURNEY]") || raw.includes("Starting")) {
      msgSpan.classList.add("highlight");
    }
    msgSpan.textContent = raw;
    this.lastMsgSpan = msgSpan;

    line.appendChild(timeSpan);
    line.appendChild(msgSpan);
    this.elLogs.appendChild(line);

    while (this.elLogs.childElementCount > this.maxLines) {
      this.elLogs.removeChild(this.elLogs.firstElementChild);
    }

    const isNearBottom = this.elLogs.scrollHeight - this.elLogs.scrollTop - this.elLogs.clientHeight < 100;
    if (isNearBottom) {
      this.elLogs.scrollTop = this.elLogs.scrollHeight;
    }
  }
}
