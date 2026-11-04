(() => {
  "use strict";

  class StepInstall {
    constructor() {
      this.isRunning = false;
      this.isDone = false;
      this.timer = null;
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepInstallI18n && window.SetupStepInstallI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    log(msg) {
      const consoleEl = document.getElementById("install-console-log");
      if (!consoleEl) return;
      const line = document.createElement("div");
      line.textContent = `> [${new Date().toLocaleTimeString()}] ${msg}`;
      consoleEl.prepend(line);
    }

    setOverallProgress(pct) {
      const fill = document.getElementById("install-overall-fill");
      const label = document.getElementById("install-overall-val");
      if (fill) fill.style.width = `${pct}%`;
      if (label) label.textContent = `${Math.round(pct)}%`;
    }

    renderItems() {
      const listEl = document.getElementById("install-items-list");
      if (!listEl) return;
      listEl.innerHTML = "";

      const selected = window.SetupStorage.get("selectedComponents") || ["voice", "sandbox", "ear", "vision"];
      const allPkgs = (window.SetupStepComponentsI18n && window.SetupStepComponentsI18n.packages) || [];
      const pkgsToInstall = allPkgs.filter((p) => selected.includes(p.id));

      pkgsToInstall.forEach((pkg) => {
        const row = document.createElement("div");
        row.className = "os-install-item-row";
        row.id = `install-pkg-${pkg.id}`;

        const left = document.createElement("div");
        left.className = "os-install-item-left";

        const icon = document.createElement("span");
        icon.className = "os-install-item-icon";
        icon.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="9"></circle></svg>';

        const info = document.createElement("div");
        info.className = "os-install-item-info";

        const name = document.createElement("span");
        name.className = "os-install-item-name";
        name.textContent = pkg.title;

        const status = document.createElement("span");
        status.className = "os-install-item-status";
        status.textContent = this.t("status_pending");

        info.appendChild(name);
        info.appendChild(status);
        left.appendChild(icon);
        left.appendChild(info);

        const size = document.createElement("span");
        size.className = "os-install-item-size";
        size.textContent = pkg.size;

        row.appendChild(left);
        row.appendChild(size);
        listEl.appendChild(row);
      });
    }

    async runInstallSequence() {
      if (this.isRunning || this.isDone) return;
      this.isRunning = true;

      const btnNext = document.getElementById("btn-next");
      if (btnNext) btnNext.disabled = true;

      const selected = window.SetupStorage.get("selectedComponents") || ["voice", "sandbox", "ear", "vision"];
      const allPkgs = (window.SetupStepComponentsI18n && window.SetupStepComponentsI18n.packages) || [];
      const pkgsToInstall = allPkgs.filter((p) => selected.includes(p.id));

      this.log("Inizializzazione sottosistema pacchetti Nuxiva OS...");
      this.setOverallProgress(5);

      const stepInc = 90 / Math.max(1, pkgsToInstall.length);
      let currentProgress = 5;

      for (let i = 0; i < pkgsToInstall.length; i++) {
        const pkg = pkgsToInstall[i];
        const row = document.getElementById(`install-pkg-${pkg.id}`);
        if (row) {
          row.classList.add("is-active");
          const status = row.querySelector(".os-install-item-status");
          if (status) status.textContent = this.t("status_downloading");
          const icon = row.querySelector(".os-install-item-icon");
          if (icon) {
            icon.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>';
          }
        }

        this.log(`Download modulo [${pkg.id}] (${pkg.size})...`);
        await new Promise((r) => setTimeout(r, 600));

        if (row) {
          const status = row.querySelector(".os-install-item-status");
          if (status) status.textContent = this.t("status_extracting");
        }
        this.log(`Verifica crittografica e unpacking [${pkg.id}]...`);
        await new Promise((r) => setTimeout(r, 500));

        if (row) {
          row.classList.remove("is-active");
          row.classList.add("is-done");
          const status = row.querySelector(".os-install-item-status");
          if (status) status.textContent = this.t("status_completed");
          const icon = row.querySelector(".os-install-item-icon");
          if (icon) {
            icon.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';
          }
        }

        currentProgress += stepInc;
        this.setOverallProgress(Math.min(95, currentProgress));
        this.log(`Modulo [${pkg.id}] configurato e attivo.`);
      }

      this.setOverallProgress(100);
      this.log("Installazione di tutti i moduli completata con successo.");
      this.isDone = true;
      this.isRunning = false;

      window.SetupStorage.set("componentsInstalled", true);

      const banner = document.getElementById("install-banner-done");
      if (banner) {
        banner.classList.add("show");
        banner.textContent = this.t("ready_badge");
      }

      if (btnNext) {
        btnNext.disabled = false;
      }
    }

    init() {
      this.renderItems();
      const alreadyDone = window.SetupStorage.get("componentsInstalled");
      if (alreadyDone) {
        this.setOverallProgress(100);
        const banner = document.getElementById("install-banner-done");
        if (banner) {
          banner.classList.add("show");
          banner.textContent = this.t("ready_badge");
        }
        const rows = document.querySelectorAll(".os-install-item-row");
        rows.forEach((r) => {
          r.classList.add("is-done");
          const st = r.querySelector(".os-install-item-status");
          if (st) st.textContent = this.t("status_completed");
          const ic = r.querySelector(".os-install-item-icon");
          if (ic) ic.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';
        });
        const btnNext = document.getElementById("btn-next");
        if (btnNext) btnNext.disabled = false;
        return;
      }

      this.runInstallSequence();
    }
  }

  window.SetupStepInstall = new StepInstall();
})();
