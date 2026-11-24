(() => {
  const D = window.NuxivaDisplay;
  const SHOW_MS = 6000;
  const TONES = { saved: "ok", delivered_later: "ok", queued: "warn", blocked: "warn", disabled: "warn", no_target: "warn", failed: "error" };
  const local = ["127.0.0.1", "localhost", "::1"].includes(location.hostname);
  let seen = null, timer = 0;

  function show(key, params, tone) {
    const el = document.getElementById("toast-shot");
    if (!el) return;
    el.replaceChildren();
    PageText.bind(el, key, params);
    el.dataset.tone = tone;
    el.classList.add("show");
    clearTimeout(timer);
    timer = setTimeout(() => el.classList.remove("show"), SHOW_MS);
  }

  D.screenshotNotice = (report) => {
    if (!report || typeof report.id !== "number") return;
    if (seen === null) { seen = report.id; return; }
    if (report.id <= seen) return;
    seen = report.id;
    const tone = TONES[report.status];
    if (!tone) return;
    show(`screenshot_${report.status}`, { name: report.name || "", folder: report.folder || "", count: report.count || 0 }, tone);
  };

  async function request() {
    try {
      const res = await fetch("/api/display/screenshot", { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" }, body: "{}" });
      if (!res.ok) show("screenshot_service", {}, "error");
    } catch (err) {
      console.warn("Richiesta screenshot non riuscita", err);
      show("screenshot_service", {}, "error");
    }
  }

  if (local) {
    window.addEventListener("keyup", (ev) => {
      if (ev.key === "PrintScreen" || ev.code === "PrintScreen") request();
    });
  }
})();
