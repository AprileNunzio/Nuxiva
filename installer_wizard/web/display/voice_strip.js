(() => {
  const D = window.NuxivaDisplay;
  const BARS = 28;
  const strip = document.createElement("div");
  strip.className = "voice-strip";
  strip.setAttribute("aria-hidden", "true");
  strip.innerHTML = Array.from({ length: BARS }, () => "<i></i>").join("");
  document.body.appendChild(strip);
  const bars = [...strip.children];
  let raf = 0, t = 0, level = 0, last = 0;

  const frame = (ts) => {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.05, (ts - (last || ts)) / 1000);
    last = ts;
    const a = D.avatar;
    const target = a && a.speaking ? (typeof a.levelTarget === "number" ? Math.max(0.25, a.levelTarget) : 0.6) : 0;
    level += (target - level) * Math.min(1, dt * 10);
    t += dt * (1.2 + level * 4);
    bars.forEach((b, i) => {
      const k = i / (BARS - 1), bell = Math.sin(Math.PI * k);
      const wave = 0.5 + 0.5 * Math.sin(t * 3 + i * 0.55) * Math.cos(t * 1.7 - i * 0.31);
      b.style.transform = `scaleY(${(0.08 + bell * (0.12 + level * wave * 0.9)).toFixed(3)})`;
    });
  };

  const reasons = new Set();
  D.setVoiceOnly = (on, reason = "desk") => {
    if (on) reasons.add(reason); else reasons.delete(reason);
    const want = reasons.size > 0;
    if (document.body.classList.contains("voice-only") === want) return;
    document.body.classList.toggle("voice-only", want);
    cancelAnimationFrame(raf); last = 0;
    if (want && !matchMedia("(prefers-reduced-motion: reduce)").matches) raf = requestAnimationFrame(frame);
  };
})();
