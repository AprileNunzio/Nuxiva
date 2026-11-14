(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const TIERS = Object.freeze({
    ultra: { rank: 3, dpr: 2, shadows: true, shadowSize: 2048, tex: 1024, fps: 60, glow: true, steam: true, leds: 24, reflect: 0.9, screens: 12 },
    high: { rank: 2, dpr: 1.75, shadows: true, shadowSize: 1024, tex: 1024, fps: 60, glow: true, steam: true, leds: 16, reflect: 0.7, screens: 10 },
    medium: { rank: 1, dpr: 1.25, shadows: true, shadowSize: 512, tex: 512, fps: 45, glow: false, steam: false, leds: 8, reflect: 0.45, screens: 6 },
    low: { rank: 0, dpr: 1, shadows: false, shadowSize: 256, tex: 256, fps: 30, glow: false, steam: false, leds: 4, reflect: 0.25, screens: 3 },
  });
  const ORDER = ["low", "medium", "high", "ultra"];
  const WINDOW = 90;

  function initial() {
    const gpu = (window.nuxivaGpu && window.nuxivaGpu.info) || {};
    const coarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
    const software = /software|swiftshader|llvmpipe/i.test(gpu.renderer || "");
    const memory = gpu.device_memory || navigator.deviceMemory || 4;
    const cores = gpu.cores || navigator.hardwareConcurrency || 4;
    const pixels = gpu.pixels || screen.width * screen.height;
    if (software) return "low";
    if (coarse || memory <= 2 || cores <= 2) return memory <= 2 ? "low" : "medium";
    if (memory >= 8 && cores >= 8 && pixels < 9e6) return "ultra";
    return memory >= 4 && cores >= 4 ? "high" : "medium";
  }

  function capFromGovernor() {
    const body = document.body.classList;
    if (body.contains("tier-minimal")) return "low";
    if (body.contains("tier-reduced") || body.contains("res-pressure")) return "medium";
    if (body.contains("lite")) return "medium";
    return "ultra";
  }

  const clampTier = (name, cap) => ORDER[Math.min(ORDER.indexOf(name), ORDER.indexOf(cap))];

  function create(onChange) {
    const base = initial();
    const st = { base, current: clampTier(base, capFromGovernor()), samples: [], calm: 0, last: 0 };

    function apply(name, reason) {
      if (name === st.current) return;
      st.current = name;
      st.samples.length = 0;
      st.calm = 0;
      onChange(TIERS[name], name, reason);
    }

    function govern() {
      const cap = capFromGovernor();
      const target = clampTier(st.base, cap);
      const now = ORDER.indexOf(st.current);
      const goal = ORDER.indexOf(target);
      if (now > goal) apply(ORDER[goal], "governor");
    }

    function frame(ms) {
      if (ms <= 0 || ms > 500) return;
      st.samples.push(ms);
      if (st.samples.length < WINDOW) return;
      const sorted = [...st.samples].sort((a, b) => a - b);
      const p90 = sorted[Math.floor(sorted.length * 0.9)];
      st.samples.length = 0;
      const budget = 1000 / TIERS[st.current].fps;
      const idx = ORDER.indexOf(st.current);
      if (p90 > budget * 1.45 && idx > 0) {
        st.calm = 0;
        st.base = ORDER[Math.min(ORDER.indexOf(st.base), idx - 1)];
        apply(ORDER[idx - 1], "slow");
      } else if (p90 < budget * 0.55 && idx < ORDER.indexOf(clampTier(st.base, capFromGovernor())) ) {
        st.calm += 1;
        if (st.calm >= 4) apply(ORDER[idx + 1], "headroom");
      } else {
        st.calm = 0;
      }
    }

    window.addEventListener("nuxiva-tier", govern);
    window.addEventListener("nuxiva-resource-level", govern);
    return {
      get spec() { return TIERS[st.current]; },
      get name() { return st.current; },
      frame,
      govern,
      dispose() {
        window.removeEventListener("nuxiva-tier", govern);
        window.removeEventListener("nuxiva-resource-level", govern);
      },
    };
  }

  LAB.quality = Object.freeze({ create, TIERS, ORDER });
})();
