(() => {
  const $ = (id) => document.getElementById(id);
  const q = new URLSearchParams(location.search);
  const mirror = q.get("mirror") === "1";
  const n = mirror ? 0 : Math.max(1, +(q.get("n") || 1)), x = +(q.get("x") || 0);
  const assistant = (window.NUXIVA_ASSISTANT && window.NUXIVA_ASSISTANT.name) || "";
  if (mirror) PageText.bind($("screen-name"), "mirror_label", { assistant });
  else PageText.bind($("screen-name"), "screen_n", { n: n + 1 });

  function tick() {
    const d = new Date();
    $("clock").textContent = d.toLocaleTimeString(Nuxiva.fmt.locale(), { hour: "2-digit", minute: "2-digit" });
    $("date").textContent = Nuxiva.fmt.date(d);
  }

  function onState(s) {
    if (!["READY", "DEGRADED"].includes(s.phase)) return;
    if (s.asset_version && window.NUXIVA_ASSET_V && s.asset_version !== window.NUXIVA_ASSET_V) { location.reload(); return; }
    NuxivaDesk.setScreens(s.screens);
    NuxivaDesk.render(s.desk || []);
  }

  NuxivaDesk.mount($("desk"), { screen: n, x, satellite: true, quiet: mirror, speak: () => {} });
  setInterval(tick, 1000); tick();
  Nuxiva.connectState("/api/stream", onState, (ok) => $("link").classList.toggle("show", !ok));
})();
