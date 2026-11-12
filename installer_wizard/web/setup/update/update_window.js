(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  class SetupUpdateWindow {
    constructor() {
      this.ctx = null;
      this.onDone = null;
      this.root = null;
      this.statePanel = null;
      this.statusText = null;
      this.localRev = null;
      this.targetRev = null;
      this.targetMeta = null;
      this.changelogWrap = null;
      this.changelogList = null;
      this.btnNext = null;
      this.btnRetry = null;
    }

    init(ctx, onDone) {
      this.ctx = ctx;
      this.onDone = onDone;
      this.root = $("update-window");
      if (!this.root) return;

      this.statePanel = $("update-status-panel");
      this.statusText = $("update-status-text");
      this.localRev = $("update-local-rev");
      this.targetRev = $("update-target-rev");
      this.targetMeta = $("update-target-meta");
      this.changelogWrap = $("update-changelog-wrap");
      this.changelogList = $("update-changelog-list");
      this.btnNext = $("btn-update-next");
      this.btnRetry = $("btn-update-retry");

      this.btnNext.addEventListener("click", () => this.proceed());
      this.btnRetry.addEventListener("click", () => this.sync());

      this.show();
      this.sync();
    }

    show() {
      if (this.root) this.root.hidden = false;
      const top = $("hud-top");
      const bottom = $("hud-bottom");
      const left = $("quad-left");
      const right = $("quad-right");
      if (top) top.style.display = "none";
      if (bottom) bottom.style.display = "none";
      if (left) left.style.display = "none";
      if (right) right.style.display = "none";
    }

    proceed() {
      if (this.root) this.root.hidden = true;
      const top = $("hud-top");
      const bottom = $("hud-bottom");
      const left = $("quad-left");
      const right = $("quad-right");
      if (top) top.style.display = "";
      if (bottom) bottom.style.display = "";
      if (left) left.style.display = "";
      if (right) right.style.display = "";
      if (typeof this.onDone === "function") this.onDone();
    }

    async sync() {
      this.btnNext.hidden = true;
      this.btnRetry.hidden = true;
      this.changelogWrap.hidden = true;
      this.targetMeta.hidden = true;
      this.statePanel.dataset.state = "busy";
      this.statusText.textContent = this.ctx.t("update-status-checking");

      try {
        const info = await this.ctx.net.json("/api/setup/update");
        if (info && info.local_rev) {
          this.localRev.textContent = info.local_rev.slice(0, 10);
        }
      } catch (err) {
      }

      try {
        const res = await this.ctx.net.json("/api/setup/update/sync", { method: "POST" });
        if (res.local_rev) {
          this.localRev.textContent = res.local_rev.slice(0, 10);
        }
        if (res.applied) {
          this.statePanel.dataset.state = "ready";
          this.statusText.textContent = this.ctx.t("update-status-applied");
          if (res.target_rev) {
            this.targetMeta.hidden = false;
            this.targetRev.textContent = res.target_rev.slice(0, 10);
          }
          if (Array.isArray(res.changelog) && res.changelog.length > 0) {
            this.renderChangelog(res.changelog);
          }
        } else if (res.uptodate || res.success) {
          this.statePanel.dataset.state = "ready";
          this.statusText.textContent = this.ctx.t("update-status-uptodate");
        } else {
          this.statePanel.dataset.state = "error";
          this.statusText.textContent = res.error || this.ctx.t("update-status-error");
          this.btnRetry.hidden = false;
        }
      } catch (err) {
        this.statePanel.dataset.state = "error";
        this.statusText.textContent = this.ctx.t("update-status-error");
        this.btnRetry.hidden = false;
      } finally {
        this.btnNext.hidden = false;
      }
    }

    renderChangelog(entries) {
      this.changelogList.replaceChildren();
      entries.forEach((item) => {
        const li = document.createElement("li");
        li.className = "update-changelog-item";
        li.textContent = item;
        this.changelogList.appendChild(li);
      });
      this.changelogWrap.hidden = false;
    }
  }

  window.SetupUpdateWindow = new SetupUpdateWindow();
})();
