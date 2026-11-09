(() => {
  const D = window.NuxivaDisplay;
  if (D.local || !window.isSecureContext || !navigator.mediaDevices?.getUserMedia) return;

  const panel = document.getElementById("remote-media");
  const camera = document.getElementById("remote-media-camera");
  const microphone = document.getElementById("remote-media-mic");
  const video = document.getElementById("remote-media-preview");
  const status = document.getElementById("remote-media-status");
  let stream = null, generation = 0, timer = 0, policyGeneration = 0;

  function stopCamera() {
    generation++;
    if (stream) stream.getTracks().forEach((track) => track.stop());
    stream = null;
    video.srcObject = null;
    video.hidden = true;
  }

  function apply(policy) {
    const previous = D.remoteMedia;
    D.remoteMedia = policy;
    if (!policy.camera_preview) {
      stopCamera();
      D.stopBrowserCamera();
    }
    if (previous?.microphone && !policy.microphone) D.Ear.disableRemote();
    panel.hidden = !policy.camera_preview && !policy.microphone;
    camera.hidden = !policy.camera_preview;
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
    } catch (error) {
      console.warn("remote_media_policy", error.name);
    } finally {
      clearTimeout(timeout);
    }
    if (requestGeneration !== policyGeneration) return;
    apply(policy);
    timer = setTimeout(refresh, 5000);
  }

  camera.addEventListener("click", async () => {
    if (D.remoteMedia?.camera_preview !== true || stream) return;
    const requestGeneration = ++generation;
    camera.disabled = true;
    try {
      const next = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      if (requestGeneration !== generation || D.remoteMedia?.camera_preview !== true) {
        next.getTracks().forEach((track) => track.stop());
        return;
      }
      stream = next;
      next.getVideoTracks()[0].addEventListener("ended", stopCamera, { once: true });
      video.srcObject = next;
      video.hidden = false;
      PageText.plain(status, "");
    } catch (error) {
      console.warn("remote_media_camera", error.name);
      PageText.bind(status, "remote_media_unavailable");
    } finally {
      camera.disabled = false;
    }
  });

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
    D.stopBrowserCamera();
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
