(() => {
  const D = window.NuxivaDisplay;
  if (D.local || !window.isSecureContext || !navigator.mediaDevices?.getUserMedia) return;

  const panel = document.getElementById("remote-media");
  const camera = document.getElementById("remote-media-camera");
  const probe = document.getElementById("remote-media-probe");
  const microphone = document.getElementById("remote-media-mic");
  const video = document.getElementById("remote-media-preview");
  const status = document.getElementById("remote-media-status");
  let stream = null, pendingStream = null, lease = null, generation = 0, timer = 0, policyGeneration = 0;
  let probeRequest = null;

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
    if (previous?.camera_probe && !policy.camera_probe) probeRequest?.abort();
    if (previous?.microphone && !policy.microphone) D.Ear.disableRemote();
    panel.hidden = !policy.camera_preview && !policy.microphone;
    camera.hidden = !policy.camera_preview;
    probe.hidden = !policy.camera_probe || !stream;
    microphone.hidden = !policy.microphone;
    if ((!previous?.camera_preview && !previous?.microphone) && !panel.hidden) panel.open = true;
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
      PageText.plain(status, "");
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

  camera.addEventListener("click", openCamera);
  probe.addEventListener("click", async () => {
    if (!lease || !D.remoteMedia?.camera_probe || !video.videoWidth) return;
    const token = lease;
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const context = canvas.getContext("2d");
    if (!context) return;
    const scale = Math.min(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
    const width = video.videoWidth * scale, height = video.videoHeight * scale;
    context.drawImage(video, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
    probe.disabled = true;
    const controller = new AbortController();
    probeRequest = controller;
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch("/api/display/remote-media/camera/probe", {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Nuxiva-Request": "1",
          "X-Nuxiva-Camera-Session": token,
        },
        body: context.getImageData(0, 0, canvas.width, canvas.height).data,
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("camera_probe_failed");
      const result = await response.json();
      if (lease === token && D.remoteMedia?.camera_probe) {
        PageText.bind(status, result.matched ? "remote_media_probe_match" : "remote_media_probe_no_match");
      }
    } catch (error) {
      console.warn("remote_media_probe", error.name);
      if (lease === token && D.remoteMedia?.camera_probe) PageText.bind(status, "remote_media_unavailable");
    } finally {
      clearTimeout(timeout);
      if (probeRequest === controller) probeRequest = null;
      probe.disabled = false;
    }
  });
  D.openRemoteCamera = () => {
    panel.open = true;
    camera.focus();
  };

  microphone.addEventListener("click", async () => {
    microphone.disabled = true;
    try {
      if (await D.Ear.enableRemote()) PageText.bind(status, "remote_media_mic_active");
      else PageText.bind(status, "remote_media_unavailable");
    } finally {
      microphone.disabled = false;
    }
  });

  document.getElementById("remote-media-stop").addEventListener("click", () => {
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
