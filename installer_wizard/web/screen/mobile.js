(() => {
  const query = "(max-width: 900px), (pointer: coarse) and (max-width: 1100px)";
  const DOCK_MIN_HEIGHT = 760;
  const DOCK_MIN_WIDTH = 700;
  const SIZES = Object.freeze({ "core-full": 0, "core-dock": 112, flow: 44 });
  const BARS = 24;
  const decide = ({ width, height, widgets }) => {
    if (!widgets) return "core-full";
    return width >= DOCK_MIN_WIDTH && height >= DOCK_MIN_HEIGHT ? "core-dock" : "flow";
  };
  const api = { decide, SIZES, active: false };
  window.NuxivaScreenMobile = Object.freeze(api);
  if (typeof document === "undefined") return;
  const params = new URLSearchParams(location.search);
  const media = window.matchMedia(query);
  if (params.get("mirror") !== "1" || !media.matches) return;

  const root = document.createElement("section");
  root.className = "mb-core";
  root.setAttribute("aria-hidden", "true");
  root.innerHTML = '<div class="mb-orb"><i></i><i></i><i></i></div><div class="mb-flow">' + "<b></b>".repeat(BARS) + "</div>";
  document.body.appendChild(root);
  document.body.classList.add("screen-mobile");
  Object.defineProperty(api, "active", { value: true });
  const bars = [...root.querySelectorAll(".mb-flow b")];
  const orb = root.querySelector(".mb-orb");
  let mode = "";
  let level = 0;
  let analyser = null;
  let samples = null;
  let last = 0;
  let t = 0;

  const apply = () => {
    const next = decide({ width: innerWidth, height: innerHeight, widgets: document.body.classList.contains("desk-has") });
    if (next === mode) return;
    mode = next;
    root.dataset.mode = next;
    document.body.dataset.coreH = String(SIZES[next]);
    document.body.style.setProperty("--mb-core-h", `${SIZES[next]}px`);
    dispatchEvent(new Event("resize"));
  };

  const measure = () => {
    if (!analyser) return 0;
    analyser.getByteTimeDomainData(samples);
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      const v = (samples[i] - 128) / 128;
      sum += v * v;
    }
    return Math.min(1, Math.sqrt(sum / samples.length) * 4);
  };

  const frame = (ts) => {
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (ts - (last || ts)) / 1000);
    last = ts;
    level += (measure() - level) * Math.min(1, dt * 12);
    t += dt * (1 + level * 4);
    orb.style.setProperty("--mb-level", level.toFixed(3));
    bars.forEach((bar, i) => {
      const k = i / (BARS - 1);
      const bell = Math.sin(Math.PI * k);
      const wave = 0.5 + 0.5 * Math.sin(t * 3 + i * 0.6) * Math.cos(t * 1.6 - i * 0.3);
      bar.style.transform = `scaleY(${(0.1 + bell * (0.12 + level * wave * 1.2)).toFixed(3)})`;
    });
  };

  const listen = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      samples = new Uint8Array(analyser.fftSize);
      ctx.createMediaStreamSource(stream).connect(analyser);
    } catch (error) {
      console.warn("flusso audio mobile: microfono non disponibile", error);
    }
  };

  new MutationObserver(apply).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  addEventListener("resize", apply);
  apply();
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) requestAnimationFrame(frame);
  listen();
})();
