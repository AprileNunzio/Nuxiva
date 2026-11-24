(() => {
  const WIDTH = 320;
  const HEIGHT = 240;
  const NAME_LIMIT = 64;
  const OUTCOMES = new Set([
    "matched", "no_face", "many_faces", "small_face", "unknown", "ambiguous",
    "no_gallery", "not_authorized", "liveness_needed", "spoof", "unavailable",
  ]);
  const FAILURES = new Map([
    [400, "remote_media_probe_error_frame"],
    [401, "remote_media_probe_error_auth"],
    [403, "remote_media_probe_error_disabled"],
    [404, "remote_media_probe_error_session"],
    [408, "remote_media_probe_error_timeout"],
    [413, "remote_media_probe_error_frame"],
    [415, "remote_media_probe_error_frame"],
    [429, "remote_media_probe_busy"],
    [503, "remote_media_probe_error_engine"],
  ]);

  function capture(video) {
    const sourceWidth = video.videoWidth, sourceHeight = video.videoHeight;
    if (!sourceWidth || !sourceHeight || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return null;
    const canvas = document.createElement("canvas");
    canvas.width = WIDTH;
    canvas.height = HEIGHT;
    const context = canvas.getContext("2d", { willReadFrequently: true, alpha: false });
    if (!context) return null;
    const scale = Math.max(WIDTH / sourceWidth, HEIGHT / sourceHeight);
    const width = sourceWidth * scale, height = sourceHeight * scale;
    context.drawImage(video, (WIDTH - width) / 2, (HEIGHT - height) / 2, width, height);
    return context.getImageData(0, 0, WIDTH, HEIGHT).data;
  }

  async function send(frame, token, signal) {
    let response;
    try {
      response = await fetch("/api/display/remote-media/camera/probe", {
        method: "POST",
        cache: "no-store",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Nuxiva-Request": "1",
          "X-Nuxiva-Camera-Session": token,
        },
        body: frame,
        signal,
      });
    } catch (error) {
      console.warn("remote_probe_network", error.name);
      return { key: error.name === "AbortError" ? "remote_media_probe_error_timeout" : "remote_media_probe_error_network" };
    }
    if (!response.ok) {
      console.warn("remote_probe_status", response.status);
      return { key: FAILURES.get(response.status) ?? "remote_media_probe_error_generic", status: response.status };
    }
    let result;
    try {
      result = await response.json();
    } catch (error) {
      console.warn("remote_probe_body", error.name);
      return { key: "remote_media_probe_error_generic" };
    }
    const outcome = OUTCOMES.has(result?.outcome) ? result.outcome : "unavailable";
    const name = typeof result?.name === "string" ? result.name.slice(0, NAME_LIMIT) : "";
    return { key: `remote_media_probe_${outcome}`, matched: outcome === "matched", name };
  }

  window.NuxivaRemoteProbe = Object.freeze({ capture, send });
})();
