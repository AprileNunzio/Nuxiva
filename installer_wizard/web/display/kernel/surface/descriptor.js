(() => {
  const media = (q) => typeof matchMedia === "function" && matchMedia(q).matches;
  let refresh = 60;

  function sample() {
    if (typeof requestAnimationFrame !== "function") return;
    const marks = [];
    const tick = (t) => {
      marks.push(t);
      if (marks.length < 31) { requestAnimationFrame(tick); return; }
      const span = marks[marks.length - 1] - marks[0];
      const hz = span > 0 ? Math.round((1000 * (marks.length - 1)) / span) : 60;
      refresh = Math.max(24, Math.min(500, hz));
    };
    requestAnimationFrame(tick);
  }

  function gpu() {
    try {
      const gl = document.createElement("canvas").getContext("webgl2");
      return gl ? { webgl2: true, max_texture: Math.min(65536, gl.getParameter(gl.MAX_TEXTURE_SIZE) | 0) } : { webgl2: false, max_texture: 0 };
    } catch (err) {
      console.warn("Capacità grafiche non rilevate", err);
      return { webgl2: false, max_texture: 0 };
    }
  }
  const caps = gpu();

  function describe() {
    const ratio = window.devicePixelRatio || 1;
    return {
      kind: "monitor",
      width: Math.max(1, Math.min(16384, Math.round(window.innerWidth * ratio))),
      height: Math.max(1, Math.min(16384, Math.round(window.innerHeight * ratio))),
      refresh_hz: refresh,
      input: { touch: media("(pointer: coarse)"), pointer: media("(pointer: fine)"), hands: !!window.NuxivaHands,
        gaze: false, keyboard: !media("(pointer: coarse)") },
      gpu: caps,
    };
  }

  sample();
  window.NuxivaSurface = Object.freeze({ describe });
})();
