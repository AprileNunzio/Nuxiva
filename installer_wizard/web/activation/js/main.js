import { bus } from "./bus.js";
import { i18n } from "./i18n.js";
import { TelemetryWidget } from "./telemetry.js";
import { SpeedtestWidget } from "./speedtest.js";
import { ProgressManager } from "./reactor.js";
import { DownloadMeterWidget } from "./download-meter.js";
import { TerminalWidget } from "./terminal.js";
import { StepFlowWidget } from "./step-flow.js";

class ActivationCockpitKernel {
  constructor() {
    this.telemetry = new TelemetryWidget();
    this.speedtest = new SpeedtestWidget();
    this.progress = new ProgressManager();
    this.downloadMeter = new DownloadMeterWidget();
    this.terminal = new TerminalWidget();
    this.stepFlow = new StepFlowWidget();
    this.evtSource = null;
    this.pollTimer = null;
  }

  async boot() {
    await i18n.setLanguage("it");

    this.telemetry.mount();
    this.speedtest.mount();
    this.progress.mount();
    this.downloadMeter.mount();
    this.terminal.mount();
    this.stepFlow.mount();

    this.connectEventStream();
    this.startJourneySync();
  }

  connectEventStream() {
    try {
      this.evtSource = new EventSource("/api/stream");
      this.evtSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          this.dispatchSystemEvent(data);
        } catch (err) {
          if (typeof e.data === "string") {
            bus.emit("log:message", e.data);
          }
        }
      };
      this.evtSource.onerror = () => {
        if (this.evtSource) {
          this.evtSource.close();
          this.evtSource = null;
        }
        setTimeout(() => this.connectEventStream(), 3000);
      };
    } catch (e) {
      console.error(e);
    }
  }

  dispatchSystemEvent(data) {
    if (data.type === "log" && data.message) {
      bus.emit("log:message", data.message);
    } else if (data.message && typeof data.message === "string") {
      bus.emit("log:message", data.message);
    }
  }

  startJourneySync() {
    this.syncJourneyState();
    this.pollTimer = setInterval(() => this.syncJourneyState(), 1200);
  }

  async syncJourneyState() {
    try {
      const res = await fetch(`/api/activation/state?t=${Date.now()}`);
      if (!res.ok) return;
      const state = await res.json();

      const stepId = state.current_step ? state.current_step.id : "";
      const stepTitle = stepId ? i18n.t(`step_${stepId}_title`, `Sequenza: ${stepId}`) : "";

      bus.emit("journey:progress", {
        percent: typeof state.percent === "number" ? state.percent : 0,
        title: stepTitle,
        stepPercent: state.step_percent
      });

      if (state.current_step) {
        bus.emit("journey:step", state.current_step);
      }

      if (state.stage === "completed" || state.is_completed) {
        if (this.pollTimer) {
          clearInterval(this.pollTimer);
          this.pollTimer = null;
        }
        setTimeout(() => {
          window.location.href = "/";
        }, 2000);
      }
    } catch (e) {
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const kernel = new ActivationCockpitKernel();
  kernel.boot();
});
