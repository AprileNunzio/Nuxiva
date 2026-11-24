(() => {
  const D = window.NuxivaDisplay;
  if (D.local || !navigator.mediaDevices?.getUserMedia || !window.NuxivaRemoteProbe) return;

  const panel = document.getElementById("remote-media");
  const camera = document.getElementById("remote-media-camera");
  const probe = document.getElementById("remote-media-probe");
  const microphone = document.getElementById("remote-media-mic");
  const video = document.getElementById("remote-media-preview");
  const status = document.getElementById("remote-media-status");
  let stream = null, pendingStream = null, lease = null, generation = 0, timer = 0, policyGeneration = 0;
  let probeRequest = null, probeTimer = 0;
  const Probe = window.NuxivaRemoteProbe;
  const AUTO_PROBE_MS = 2500;
  const STOP_STATUSES = new Set([401, 403, 404]);
  const AUTO_KEY = "nuxiva.remote_media.auto";
  let autoStarted = false;

  function autoWanted() {
    try {
      return localStorage.getItem(AUTO_KEY) !== "off";
    } catch (error) {
      console.warn("remote_media_auto_read", error.name);
      return true;
    }
  }

  function rememberAuto(enabled) {
    try {
      localStorage.setItem(AUTO_KEY, enabled ? "on" : "off");
    } catch (error) {
      console.warn("remote_media_auto_write", error.name);
    }
  }

  function autoStart(policy) {
    if (autoStarted || (!policy.camera_preview && !policy.microphone)) return;
    autoStarted = true;
    if (!autoWanted()) return;
    if (policy.camera_preview) {
      panel.open = true;
      openCamera();
    }
    if (policy.microphone) {
      D.Ear.enableRemote().catch((error) => console.warn("remote_media_auto_mic", error.name));
    }
  }

  function cameraSession(method, token, signal) {
    const headers = { "X-Nuxiva-Request": "1" };
    if (token) headers["X-Nuxiva-Camera-Session"] = token;
    return fetch("/api/display/remote-media/camera", { method, headers, signal, keepalive: method === "DELETE" });
  }

  function revoke(token) {
    if (token) cameraSession("DELETE", token).catch((error) => console.warn("remote_media_revoke", error.name));
  }

  function stopCamera() {
    generation++;
    clearTimeout(probeTimer);
    probeTimer = 0;
    probeRequest?.abort();
    const token = lease;
    lease = null;
    revoke(token);
    if (stream) stream.getTracks().forEach((track) => track.stop());
    if (pendingStream) pendingStream.getTracks().forEach((track) => track.stop());
    stream = null;
    pendingStream = null;
    video.srcObject = null;
    video.hidden = true;
    probe.hidden = true;
    PageText.plain(status, "");
  }

  function apply(policy) {
    const previous = D.remoteMedia;
    D.remoteMedia = policy;
    if (!policy.camera_preview && (stream || pendingStream || previous?.camera_preview)) {
      stopCamera();
    }
    if (previous?.camera_probe && !policy.camera_probe) {
      clearTimeout(probeTimer);
      probeRequest?.abort();
    }
    if (!previous?.camera_probe && policy.camera_probe && lease) scheduleProbe();
    if (previous?.microphone && !policy.microphone) D.Ear.disableRemote();
    panel.hidden = !policy.camera_preview && !policy.microphone;
    camera.hidden = !policy.camera_preview;
    probe.hidden = !policy.camera_probe || !stream;
    microphone.hidden = !policy.microphone;
    autoStart(policy);
  }

  async function refresh() {
    const requestGeneration = policyGeneration;
    let policy = {};
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    try {
      const response = await fetch("/api/display/remote-media", {
        cache: "no-store",
        signal: controller.signal,
      });
      if (response.ok) policy = await response.json();
      const token = lease;
      if (policy.camera_preview && token) {
        const renewed = await cameraSession("PUT", token, controller.signal);
        if (!renewed.ok && lease === token) stopCamera();
      }
    } catch (error) {
      console.warn("remote_media_policy", error.name);
      policy = {};
    } finally {
      clearTimeout(timeout);
    }
    if (requestGeneration !== policyGeneration) return;
    apply(policy);
    timer = setTimeout(refresh, 5000);
  }

  async function openCamera() {
    if (D.remoteMedia?.camera_preview !== true || stream) return;
    if (camera.disabled) return;
    const requestGeneration = ++generation;
    camera.disabled = true;
    let next = null, token = null, timeout;
    try {
      next = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      if (requestGeneration !== generation || D.remoteMedia?.camera_preview !== true) return;
      pendingStream = next;
      const controller = new AbortController();
      timeout = setTimeout(() => controller.abort(), 4000);
      const response = await cameraSession("POST", null, controller.signal);
      if (!response.ok) throw new Error("camera_session_denied");
      ({ token } = await response.json());
      if (requestGeneration !== generation || D.remoteMedia?.camera_preview !== true
          || next.getVideoTracks()[0]?.readyState !== "live") return;
      lease = token;
      stream = next;
      next.getVideoTracks()[0].addEventListener("ended", stopCamera, { once: true });
      video.srcObject = next;
      video.hidden = false;
      probe.hidden = !D.remoteMedia.camera_probe;
      if (D.remoteMedia.camera_probe) {
        PageText.bind(status, "remote_media_probe_auto");
        scheduleProbe();
      } else {
        PageText.plain(status, "");
      }
    } catch (error) {
      console.warn("remote_media_camera", error.name);
      if (requestGeneration === generation) PageText.bind(status, "remote_media_unavailable");
    } finally {
      clearTimeout(timeout);
      if (pendingStream === next) pendingStream = null;
      if (next && stream !== next) next.getTracks().forEach((track) => track.stop());
      if (token && lease !== token) revoke(token);
      camera.disabled = false;
    }
  }

  function scheduleProbe() {
    clearTimeout(probeTimer);
    probeTimer = 0;
    if (lease && D.remoteMedia?.camera_probe) probeTimer = setTimeout(() => runProbe(false), AUTO_PROBE_MS);
  }

  async function runProbe(manual) {
    if (!D.remoteMedia?.camera_probe) {
      if (manual) PageText.bind(status, "remote_media_probe_error_disabled");
      return;
    }
    if (!lease) {
      if (manual) PageText.bind(status, "remote_media_probe_error_session");
      return;
    }
    if (probeRequest) return;
    const frame = Probe.capture(video);
    if (!frame) {
      if (manual) PageText.bind(status, "remote_media_probe_no_frame");
      scheduleProbe();
      return;
    }
    const token = lease;
    const controller = new AbortController();
    probeRequest = controller;
    probe.disabled = true;
    if (manual) PageText.bind(status, "remote_media_probe_working");
    const timeout = setTimeout(() => controller.abort(), 8000);
    let result = {};
    try {
      result = await Probe.send(frame, token, controller.signal);
      const quiet = !manual && result.status === 429;
      if (!quiet && lease === token && D.remoteMedia?.camera_probe) {
        PageText.bind(status, result.key, result.name ? { name: result.name } : undefined);
      }
    } finally {
      clearTimeout(timeout);
      if (probeRequest === controller) probeRequest = null;
      probe.disabled = false;
      if (lease === token && !STOP_STATUSES.has(result.status)) scheduleProbe();
    }
  }

  camera.addEventListener("click", () => {
    rememberAuto(true);
    openCamera();
  });
  probe.addEventListener("click", () => runProbe(true));
  D.openRemoteCamera = () => {
    panel.open = true;
    camera.focus();
  };

  microphone.addEventListener("click", async () => {
    rememberAuto(true);
    microphone.disabled = true;
    try {
      if (await D.Ear.enableRemote()) PageText.bind(status, "remote_media_mic_active");
      else PageText.bind(status, "remote_media_unavailable");
    } finally {
      microphone.disabled = false;
    }
  });

  document.getElementById("remote-media-stop").addEventListener("click", () => {
    rememberAuto(false);
    stopCamera();
    D.Ear.disableRemote();
    PageText.plain(status, "");
  });
  window.addEventListener("pagehide", () => {
    policyGeneration++;
    clearTimeout(timer);
    apply({});
  });
  window.addEventListener("pageshow", (event) => { if (event.persisted) refresh(); });
  refresh();
})();
