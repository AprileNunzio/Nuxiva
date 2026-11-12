(() => {
  "use strict";

  const SHOTS = ["front", "three_left", "three_right"];
  const GOOD = 70;
  const STEADY = 3;
  const TICK_MS = 450;
  const MAX_SIDE = 640;
  const HEADERS = { "X-Nuxiva-Request": "1" };
  const LIGHT_ALERTS = ["black", "dark", "flat", "overexposed"];

  const $ = (id) => document.getElementById(id);

  async function detail(res) {
    const body = await res.json().catch(() => null);
    return body && typeof body.detail === "string" ? body.detail : "";
  }

  class StepFace {
    constructor() {
      this.source = "client";
      this.mode = "server";
      this.stream = null;
      this.done = new Map();
      this.current = 0;
      this.steady = 0;
      this.busy = false;
      this.running = false;
      this.timer = 0;
      this.lastBlob = null;
      this.lastScore = 0;
      this.previewUrl = "";
      this.initialized = false;
    }

    t(key, vars) {
      const lang = window.SetupStorage.get("lang") || "it";
      const all = (window.SetupStepFaceI18n && window.SetupStepFaceI18n.dict) || {};
      const text = (all[lang] && all[lang][key]) || (all.it && all.it[key]) || "";
      return vars ? text.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : "")) : text;
    }

    applyTexts() {
      document.querySelectorAll("#screen-face [data-face-i18n]").forEach((el) => {
        el.textContent = this.t(el.dataset.faceI18n);
      });
    }

    get target() {
      return SHOTS[this.current] || null;
    }

    active() {
      const screen = $("screen-face");
      return Boolean(screen && screen.classList.contains("active"));
    }

    setText(id, text) {
      const el = $(id);
      if (el) el.textContent = text;
    }

    alert(text) {
      const el = $("face-alert");
      if (!el) return;
      el.textContent = text || "";
      el.hidden = !text;
    }

    showPermError(msg) {
      const err = $("face-perm-error");
      const fallback = $("btn-face-perm-fallback");
      if (err) {
        err.textContent = msg;
        err.style.display = msg ? "block" : "none";
      }
      if (fallback) fallback.style.display = msg ? "inline-block" : "none";
    }

    canUseBrowserCamera() {
      return Boolean(window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    async loadContext() {
      try {
        const res = await fetch("/api/setup/face/context", { headers: HEADERS, cache: "no-store" });
        if (!res.ok) return { mode: "server", views: [] };
        return await res.json();
      } catch (err) {
        return { mode: "server", views: [] };
      }
    }

    async requestWebcam(deviceId) {
      const overlay = $("face-perm-overlay");
      const video = $("face-video-feed");
      this.showPermError("");
      this.stopClientCamera();
      if (!this.canUseBrowserCamera()) {
        if (overlay) overlay.classList.remove("is-hidden");
        this.showPermError(this.t("err_insecure"));
        return;
      }
      try {
        const constraint = deviceId && deviceId !== "default"
          ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } };
        this.stream = await navigator.mediaDevices.getUserMedia({ video: constraint, audio: false });
        if (video) {
          video.srcObject = this.stream;
          await video.play().catch(() => undefined);
        }
        if (overlay) overlay.classList.add("is-hidden");
        await this.listClientCameras(deviceId);
      } catch (err) {
        if (overlay) overlay.classList.remove("is-hidden");
        this.setText("btn-req-face-perm", this.t("btn_req_again"));
        const name = err && err.name;
        const key = name === "NotFoundError" || name === "DevicesNotFoundError" ? "err_missing"
          : name === "NotReadableError" || name === "TrackStartError" ? "err_busy" : "err_denied";
        this.showPermError(this.t(key));
      }
    }

    async listClientCameras(selected) {
      const select = $("face-camera-select");
      if (!select || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
      select.replaceChildren(...devices.map((d, i) => {
        const opt = document.createElement("option");
        opt.value = d.deviceId || "default";
        opt.textContent = d.label || this.t("camera_n", { n: i + 1 });
        opt.selected = Boolean(selected) && d.deviceId === selected;
        return opt;
      }));
    }

    async listServerCameras() {
      const select = $("face-camera-select");
      if (!select) return;
      try {
        const res = await fetch("/api/setup/cameras/scan", { method: "POST", headers: HEADERS });
        const devices = res.ok ? ((await res.json()).devices || []) : [];
        const options = devices.length ? devices.map((d) => {
          const opt = document.createElement("option");
          opt.value = String(d.id);
          opt.textContent = `${d.name || d.id}${d.type ? ` (${String(d.type).toUpperCase()})` : ""}`;
          return opt;
        }) : [Object.assign(document.createElement("option"), { value: "none", textContent: this.t("server_none") })];
        select.replaceChildren(...options);
      } catch (err) {
        select.replaceChildren(Object.assign(document.createElement("option"), { value: "none", textContent: this.t("server_none") }));
      }
    }

    stopClientCamera() {
      if (this.stream) {
        this.stream.getTracks().forEach((track) => track.stop());
        this.stream = null;
      }
      const video = $("face-video-feed");
      if (video) video.srcObject = null;
    }

    setSource(source) {
      this.source = source;
      this.steady = 0;
      this.lastBlob = null;
      window.SetupStorage.set("faceSource", source);
      const client = source === "client";
      $("face-tab-client")?.classList.toggle("is-active", client);
      $("face-tab-server")?.classList.toggle("is-active", !client);
      const video = $("face-video-feed");
      const img = $("face-server-feed");
      if (video) video.hidden = !client;
      if (img) img.hidden = client;
      [video, img].forEach((el) => el && el.classList.add("os-face-mirror"));
      this.alert("");
      if (client) {
        this.requestWebcam();
      } else {
        this.stopClientCamera();
        $("face-perm-overlay")?.classList.add("is-hidden");
        this.listServerCameras();
      }
    }

    async refreshPreview() {
      const img = $("face-server-feed");
      const res = await fetch(`/api/setup/face/preview.jpg?t=${Date.now()}`, { headers: HEADERS, cache: "no-store" });
      if (!res.ok) throw new Error(await detail(res) || this.t("alert_preview"));
      const url = URL.createObjectURL(await res.blob());
      if (img) img.src = url;
      if (this.previewUrl) URL.revokeObjectURL(this.previewUrl);
      this.previewUrl = url;
    }

    grabFrame() {
      const video = $("face-video-feed");
      if (!video || !video.videoWidth) return Promise.resolve(null);
      const k = Math.min(1, MAX_SIDE / Math.max(video.videoWidth, video.videoHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(video.videoWidth * k);
      canvas.height = Math.round(video.videoHeight * k);
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.88));
    }

    async analyze() {
      if (this.source === "server") {
        await this.refreshPreview();
        const res = await fetch("/api/setup/face/analyze", { headers: HEADERS, cache: "no-store" });
        if (!res.ok) throw new Error(await detail(res) || this.t("alert_vision"));
        return res.json();
      }
      const blob = await this.grabFrame();
      if (!blob) return null;
      const res = await fetch("/api/setup/face/analyze", {
        method: "POST", headers: { ...HEADERS, "Content-Type": "image/jpeg" }, body: blob,
      });
      if (!res.ok) throw new Error(await detail(res) || this.t("alert_vision"));
      this.lastBlob = blob;
      return res.json();
    }

    draw(report, good) {
      const canvas = $("face-overlay");
      if (!canvas) return;
      const ratio = window.devicePixelRatio || 1;
      const cw = canvas.clientWidth;
      const ch = canvas.clientHeight;
      canvas.width = Math.round(cw * ratio);
      canvas.height = Math.round(ch * ratio);
      const ctx = canvas.getContext("2d");
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, cw, ch);
      if (!report || !report.face || !Array.isArray(report.frame)) return;
      const [fw, fh] = report.frame;
      const scale = Math.max(cw / fw, ch / fh);
      const dx = (cw - fw * scale) / 2;
      const dy = (ch - fh * scale) / 2;
      const map = (nx, ny) => [cw - (nx * fw * scale + dx), ny * fh * scale + dy];
      const color = good ? "#34d399" : "#fbbf24";
      const [bx, by, bw, bh] = report.box;
      const [x0, y0] = map(bx + bw, by);
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x0, y0, bw * fw * scale, bh * fh * scale);
      ctx.fillStyle = color;
      for (let i = 0; i < 10; i += 2) {
        const [px, py] = map(report.points[i], report.points[i + 1]);
        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    telemetry(report) {
      const q = report && report.face ? report.quality || {} : null;
      const light = (report && report.light) || {};
      const round = (v, d = 0) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(d) : "—");
      this.setText("face-val-pose", q ? this.t("pose_value", { y: round(q.yaw), p: round(q.pitch), r: round(q.roll) }) : "—");
      this.setText("face-val-dist", q ? this.t("distance_value", { cm: round(report.distance_cm) }) : "—");
      this.setText("face-val-eyes", q ? this.t("eyes_value", { px: round(q.eye_px) }) : "—");
      this.setText("face-val-conf", q ? `${round((report.confidence || 0) * 100, 1)}%` : "—");
      this.setText("face-val-sharp", q ? this.t("sharp_value", { v: round(q.sharpness) }) : "—");
      const issue = (light.issues || []).find((i) => LIGHT_ALERTS.includes(i));
      this.setText("face-val-light", report ? `${this.t(issue ? `light_${issue}` : "light_ok")} · ${this.t("light_value", { b: round(light.mean), c: round(light.std) })}` : "—");
      this.setText("face-val-quality", q ? this.t("quality_value", { q: round(q.score) }) : "—");
      const bar = $("face-quality-bar");
      if (bar) bar.style.width = `${q ? Math.max(0, Math.min(100, q.score || 0)) : 0}%`;
      this.alert(issue ? this.t(`alert_${issue}`) : "");
    }

    judge(report) {
      if (!report || !report.face) {
        this.setText("face-hint", this.t("hint_no_face"));
        return false;
      }
      const q = report.quality || {};
      const issues = Array.isArray(q.issues) ? q.issues : [];
      if (q.kind !== this.target) {
        this.setText("face-hint", this.t(`hint_${this.target}`));
        return false;
      }
      if ((q.score || 0) < GOOD || issues.length) {
        const why = issues.map((i) => this.t(`issue_${i}`) || i).join(", ");
        this.setText("face-hint", this.t("hint_improve", { q: Math.round(q.score || 0), issues: why }));
        return false;
      }
      this.setText("face-hint", this.t(this.source === "server" ? "hint_hold_server" : "hint_hold"));
      return true;
    }

    markShots() {
      SHOTS.forEach((kind, i) => {
        const item = $(`face-shot-${kind}`);
        if (!item) return;
        const status = item.querySelector(".os-face-shot-status");
        const done = this.done.get(kind);
        item.classList.toggle("is-done", done !== undefined);
        item.classList.toggle("is-active", i === this.current);
        if (status) {
          status.textContent = done !== undefined ? this.t("shot_done", { q: Math.round(done) })
            : i === this.current ? this.t("shot_now") : this.t("shot_wait");
        }
      });
      const btn = $("btn-face-capture");
      if (btn) {
        btn.disabled = this.busy || this.target === null;
        btn.textContent = this.t(this.target === null ? "btn_done" : "btn_capture");
      }
    }

    async capture() {
      const kind = this.target;
      if (!kind || this.busy) return;
      this.busy = true;
      this.markShots();
      const status = $(`face-shot-${kind}`)?.querySelector(".os-face-shot-status");
      if (status) status.textContent = this.t("shot_saving");
      try {
        if (this.source === "client" && !this.lastBlob) this.lastBlob = await this.grabFrame();
        const browser = this.source === "client" && this.lastBlob;
        const res = await fetch(`/api/setup/face?kind=${encodeURIComponent(kind)}`, {
          method: "POST",
          headers: browser ? { ...HEADERS, "Content-Type": "image/jpeg" } : HEADERS,
          body: browser ? this.lastBlob : undefined,
        });
        if (!res.ok) throw new Error(await detail(res) || this.t("alert_vision"));
        const result = await res.json();
        const score = result.vision && result.vision.quality ? result.vision.quality.score : this.lastScore;
        this.done.set(kind, typeof score === "number" ? score : this.lastScore);
        this.current = SHOTS.findIndex((s) => !this.done.has(s));
        if (this.current < 0) this.current = SHOTS.length;
        window.SetupStorage.set("faceEnrolled", this.done.size > 0);
        if (this.target === null) this.finish();
      } catch (err) {
        this.alert(err.message);
        if (status) status.textContent = this.t("shot_failed");
      } finally {
        this.steady = 0;
        this.busy = false;
        this.markShots();
      }
    }

    finish() {
      this.stop();
      this.setText("face-hint", this.t("hint_done"));
      window.SetupStorage.set("faceEnrolled", true);
    }

    async tick() {
      if (!this.running) return;
      if (!this.active()) {
        this.stop();
        return;
      }
      if (!this.busy && this.target !== null) {
        try {
          const report = await this.analyze();
          if (report) {
            this.telemetry(report);
            const good = this.judge(report);
            this.draw(report, good);
            this.lastScore = report.face && report.quality ? report.quality.score || 0 : 0;
            this.steady = good ? this.steady + 1 : 0;
            if (this.steady >= STEADY) await this.capture();
          }
        } catch (err) {
          this.alert(err.message);
          this.draw(null, false);
        }
      }
      if (this.running) this.timer = window.setTimeout(() => this.tick(), TICK_MS);
    }

    start() {
      this.stop();
      this.running = true;
      this.timer = window.setTimeout(() => this.tick(), TICK_MS);
    }

    stop() {
      this.running = false;
      window.clearTimeout(this.timer);
      if (!this.active()) this.stopClientCamera();
    }

    bind() {
      $("face-tab-client")?.addEventListener("click", () => this.setSource("client"));
      $("face-tab-server")?.addEventListener("click", () => this.setSource("server"));
      $("btn-req-face-perm")?.addEventListener("click", () => this.requestWebcam($("face-camera-select")?.value));
      $("btn-face-perm-fallback")?.addEventListener("click", () => this.setSource("server"));
      $("btn-face-capture")?.addEventListener("click", () => this.capture());
      $("face-camera-select")?.addEventListener("change", (e) => {
        if (this.source === "client") this.requestWebcam(e.target.value);
      });
    }

    async init() {
      if (!this.initialized) {
        this.initialized = true;
        this.bind();
      }
      this.applyTexts();
      $("face-empty-box")?.classList.remove("show");
      const ctx = await this.loadContext();
      this.mode = ctx.mode === "remote" ? "remote" : "server";
      this.done = new Map((Array.isArray(ctx.views) ? ctx.views : []).filter((k) => SHOTS.includes(k)).map((k) => [k, 0]));
      this.current = SHOTS.findIndex((s) => !this.done.has(s));
      if (this.current < 0) this.current = SHOTS.length;
      const browserOk = this.canUseBrowserCamera();
      const source = this.mode === "remote" && browserOk ? "client" : "server";
      this.setText("face-mode", this.t(this.mode === "server" ? "mode_server" : browserOk ? "mode_remote" : "mode_remote_insecure"));
      this.setSource(source);
      this.markShots();
      if (this.target === null) {
        this.finish();
        return;
      }
      this.setText("face-hint", this.t(`hint_${this.target}`));
      this.start();
    }
  }

  window.SetupStepFace = new StepFace();
})();
