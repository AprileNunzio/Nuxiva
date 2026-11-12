(() => {
  const CLEAN = /[^\w\s().,/+:;@#-]/g;

  function probe() {
    const out = { renderer: "", device_memory: navigator.deviceMemory || 0, cores: navigator.hardwareConcurrency || 0,
      max_texture: 0, pixels: Math.round(screen.width * screen.height * (window.devicePixelRatio || 1) ** 2), webgpu: "gpu" in navigator };
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
      if (gl) {
        const info = gl.getExtension("WEBGL_debug_renderer_info");
        out.renderer = String(gl.getParameter(info ? info.UNMASKED_RENDERER_WEBGL : gl.RENDERER) || "").replace(CLEAN, "").slice(0, 160);
        out.max_texture = gl.getParameter(gl.MAX_TEXTURE_SIZE) || 0;
        const lose = gl.getExtension("WEBGL_lose_context");
        if (lose) lose.loseContext();
      } else out.renderer = "software";
    } catch (err) { console.warn("GPU probe failed", err); }
    return Object.freeze(out);
  }

  const shortName = (renderer) => String(renderer || "?").replace(/^ANGLE \(|\)$/g, "")
    .replace(/\s*\(0x[0-9a-f]+\)|Direct3D11.*|vs_\d.*$/gi, "").slice(0, 60).trim() || "?";

  const info = probe();
  window.nuxivaGpu = Object.freeze({ info, name: shortName(info.renderer) });
})();
