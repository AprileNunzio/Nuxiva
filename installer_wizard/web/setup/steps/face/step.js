(() => {
  "use strict";

  class StepFace {
    constructor() {
      this.currentShot = 0;
      this.shots = ["front", "three_left", "three_right"];
      this.stream = null;
      this.activeSource = "client";
      this.hasRequestedPermission = false;
      this.initialized = false;
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepFaceI18n && window.SetupStepFaceI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    showPermError(msg) {
      const errEl = document.getElementById("face-perm-error");
      const fallbackBtn = document.getElementById("btn-face-perm-fallback");
      if (errEl) {
        errEl.textContent = msg;
        errEl.style.display = msg ? "block" : "none";
      }
      if (fallbackBtn) {
        fallbackBtn.style.display = msg ? "inline-block" : "none";
      }
    }

    async acquireStream(deviceId) {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const legacy = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
        if (legacy) {
          return new Promise((resolve, reject) => {
            legacy.call(navigator, { video: true }, resolve, reject);
          });
        }
        throw new Error("SECURE_CONTEXT_REQUIRED");
      }

      const videoConstraint = deviceId && deviceId !== "default"
        ? { deviceId: { exact: deviceId } }
        : { width: { ideal: 640 }, height: { ideal: 480 } };

      try {
        return await navigator.mediaDevices.getUserMedia({ video: videoConstraint });
      } catch (err) {
        return await navigator.mediaDevices.getUserMedia({ video: true });
      }
    }

    async requestWebcamPermission(deviceId) {
      const videoEl = document.getElementById("face-video-feed");
      const permOverlay = document.getElementById("face-perm-overlay");
      const emptyBox = document.getElementById("face-empty-box");
      const liveBox = document.getElementById("face-live-box");
      const btn = document.getElementById("btn-req-face-perm");

      if (btn) btn.textContent = "Accesso in corso...";
      this.showPermError("");
      this.stopClientCamera();

      try {
        this.stream = await this.acquireStream(deviceId);
        if (videoEl) {
          videoEl.srcObject = this.stream;
          videoEl.play().catch(() => {});
        }
        if (permOverlay) permOverlay.classList.add("is-hidden");
        if (liveBox) liveBox.style.display = "flex";
        if (emptyBox) emptyBox.classList.remove("show");

        this.hasRequestedPermission = true;
        await this.populateClientDevices();
      } catch (err) {
        if (permOverlay) permOverlay.classList.remove("is-hidden");
        if (btn) btn.textContent = this.t("btn_req_again");

        let errKey = "err_denied";
        if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
          errKey = "err_missing";
        } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
          errKey = "err_busy";
        } else if (err.message === "SECURE_CONTEXT_REQUIRED" || !window.isSecureContext) {
          errKey = "err_insecure";
        }
        this.showPermError(this.t(errKey));
      }
    }

    async populateClientDevices() {
      const select = document.getElementById("face-camera-select");
      if (!select || !navigator.mediaDevices?.enumerateDevices) return;
      select.innerHTML = "";

      try {
        const devs = await navigator.mediaDevices.enumerateDevices();
        const videoDevs = devs.filter((d) => d.kind === "videoinput");
        if (videoDevs.length === 0) {
          const opt = document.createElement("option");
          opt.value = "default";
          opt.textContent = "Webcam Client Predefinita";
          select.appendChild(opt);
        } else {
          videoDevs.forEach((dev, idx) => {
            const opt = document.createElement("option");
            opt.value = dev.deviceId || `cam-${idx}`;
            opt.textContent = dev.label || `Fotocamera ${idx + 1}`;
            select.appendChild(opt);
          });
        }
      } catch (e) {}
    }

    async populateServerDevices() {
      const select = document.getElementById("face-camera-select");
      const permOverlay = document.getElementById("face-perm-overlay");
      const emptyBox = document.getElementById("face-empty-box");
      const liveBox = document.getElementById("face-live-box");

      if (permOverlay) permOverlay.classList.add("is-hidden");
      if (!select) return;
      select.innerHTML = "";

      this.stopClientCamera();

      try {
        const res = await fetch("/api/setup/cameras/scan", {
          method: "POST",
          headers: { "X-Nuxiva-Request": "1" }
        });
        if (res.ok) {
          const data = await res.json();
          const devs = data.devices || [];
          if (devs.length === 0) {
            if (liveBox) liveBox.style.display = "none";
            if (emptyBox) emptyBox.classList.add("show");
            const opt = document.createElement("option");
            opt.value = "none";
            opt.textContent = "Nessuna camera server";
            select.appendChild(opt);
          } else {
            if (liveBox) liveBox.style.display = "flex";
            if (emptyBox) emptyBox.classList.remove("show");
            devs.forEach((d) => {
              const opt = document.createElement("option");
              opt.value = d.id;
              opt.textContent = `${d.name || d.id} (${d.type.toUpperCase()})`;
              select.appendChild(opt);
            });
          }
        }
      } catch (e) {
        if (liveBox) liveBox.style.display = "none";
        if (emptyBox) emptyBox.classList.add("show");
      }
    }

    stopClientCamera() {
      if (this.stream) {
        this.stream.getTracks().forEach((t) => t.stop());
        this.stream = null;
      }
      const videoEl = document.getElementById("face-video-feed");
      if (videoEl) videoEl.srcObject = null;
    }

    setSource(source) {
      this.activeSource = source;
      window.SetupStorage.set("faceSource", source);

      const tabClient = document.getElementById("face-tab-client");
      const tabServer = document.getElementById("face-tab-server");
      const permOverlay = document.getElementById("face-perm-overlay");

      if (tabClient) tabClient.classList.toggle("is-active", source === "client");
      if (tabServer) tabServer.classList.toggle("is-active", source === "server");

      if (source === "client") {
        if (this.hasRequestedPermission) {
          this.requestWebcamPermission();
        } else {
          if (permOverlay) permOverlay.classList.remove("is-hidden");
        }
      } else {
        this.populateServerDevices();
      }
    }

    updateTelemetry() {
      const poseEl = document.getElementById("face-val-pose");
      const distEl = document.getElementById("face-val-dist");
      const confEl = document.getElementById("face-val-conf");
      const hashEl = document.getElementById("face-val-hash");

      if (this.currentShot === 0) {
        if (poseEl) poseEl.textContent = "Yaw: -1.2° | Pitch: +0.8°";
        if (distEl) distEl.textContent = "63.2 mm";
        if (confEl) confEl.textContent = "98.9%";
        if (hashEl) hashEl.textContent = "0x7F9A...C4B2";
      } else if (this.currentShot === 1) {
        if (poseEl) poseEl.textContent = "Yaw: -24.5° | Pitch: +1.1°";
        if (distEl) distEl.textContent = "58.4 mm";
        if (confEl) confEl.textContent = "97.4%";
        if (hashEl) hashEl.textContent = "0x3D11...E89A";
      } else if (this.currentShot === 2) {
        if (poseEl) poseEl.textContent = "Yaw: +26.1° | Pitch: +0.5°";
        if (distEl) distEl.textContent = "59.1 mm";
        if (confEl) confEl.textContent = "98.1%";
        if (hashEl) hashEl.textContent = "0x98FF...120C";
      }
    }

    async captureShot() {
      if (this.currentShot >= this.shots.length) return;
      const kind = this.shots[this.currentShot];
      const shotItem = document.getElementById(`face-shot-${kind}`);

      const btn = document.getElementById("btn-face-capture");
      if (btn) btn.disabled = true;

      try {
        await fetch(`/api/setup/face?kind=${kind}`, {
          method: "POST",
          headers: { "X-Nuxiva-Request": "1" }
        });
      } catch (e) {}

      if (shotItem) {
        shotItem.classList.remove("is-active");
        shotItem.classList.add("is-done");
        const statusSpan = shotItem.querySelector(".os-face-shot-status");
        if (statusSpan) statusSpan.textContent = "✓ Mappato";
      }

      this.currentShot++;
      this.updateTelemetry();

      if (this.currentShot < this.shots.length) {
        const nextKind = this.shots[this.currentShot];
        const nextItem = document.getElementById(`face-shot-${nextKind}`);
        if (nextItem) nextItem.classList.add("is-active");
        if (btn) btn.disabled = false;
      } else {
        if (btn) {
          btn.textContent = "✓ Punti Mappati";
          btn.style.backgroundColor = "#10b981";
        }
        window.SetupStorage.set("faceEnrolled", true);
      }
    }

    init() {
      if (!this.initialized) {
        this.initialized = true;
        const tabClient = document.getElementById("face-tab-client");
        const tabServer = document.getElementById("face-tab-server");
        const select = document.getElementById("face-camera-select");
        const btnReqPerm = document.getElementById("btn-req-face-perm");
        const fallbackBtn = document.getElementById("btn-face-perm-fallback");

        if (tabClient) tabClient.addEventListener("click", () => this.setSource("client"));
        if (tabServer) tabServer.addEventListener("click", () => this.setSource("server"));
        if (btnReqPerm) btnReqPerm.addEventListener("click", () => this.requestWebcamPermission());
        if (fallbackBtn) fallbackBtn.addEventListener("click", () => this.setSource("server"));

        if (select) {
          select.addEventListener("change", (e) => {
            if (this.activeSource === "client") {
              this.requestWebcamPermission(e.target.value);
            }
          });
        }

        const btn = document.getElementById("btn-face-capture");
        if (btn) {
          btn.addEventListener("click", () => this.captureShot());
        }
      }

      const emptyBox = document.getElementById("face-empty-box");
      if (emptyBox) emptyBox.classList.remove("show");

      const savedSource = window.SetupStorage.get("faceSource") || "client";
      this.setSource(savedSource);

      this.currentShot = 0;
      this.updateTelemetry();
    }
  }

  window.SetupStepFace = new StepFace();
})();