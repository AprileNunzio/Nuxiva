(() => {
  const $ = (id) => document.getElementById(id);
  const q = new URLSearchParams(location.search);
  const mirror = q.get("mirror") === "1";
  const n = mirror ? 0 : Math.min(16, Math.max(1, Math.trunc(Number(q.get("n")) || 1)));
  const x = Math.trunc(Number(q.get("x")) || 0);
  const assistant = (window.NUXIVA_ASSISTANT && window.NUXIVA_ASSISTANT.name) || "";
  const grid = window.NuxivaScreenGrid;
  if (mirror) PageText.bind($("screen-name"), "mirror_label", { assistant });
  else PageText.bind($("screen-name"), "screen_n", { n: n + 1 });
  document.body.classList.toggle("screen-mirror", mirror);

  function tick() {
    const d = new Date();
    const time = d.toLocaleTimeString(Nuxiva.fmt.locale(), { hour: "2-digit", minute: "2-digit" });
    const date = Nuxiva.fmt.date(d);
    $("clock").textContent = time;
    $("date").textContent = date;
    $("rest-time").textContent = time;
    $("rest-date").textContent = date;
  }

  function onState(s) {
    if (!["READY", "DEGRADED"].includes(s.phase)) return;
    if (s.asset_version && window.NUXIVA_ASSET_V && s.asset_version !== window.NUXIVA_ASSET_V) { location.reload(); return; }
    NuxivaDesk.setScreens(s.screens);
    if (!mirror) NuxivaScreenMap.render(s.screens, s.screen_roles, n);
    NuxivaDesk.render(s.desk || []);
    if (window.NuxivaParticles && !mirror) window.NuxivaParticles.update(s.particles, n);
  }

  NuxivaScreenMap.mount($("screen-map"), mirror ? [] : [$("screen-role"), $("rest-role")]);
  NuxivaScreenPager.mount($("pager"));
  NuxivaDesk.mount($("desk"), { screen: n, x, satellite: true, quiet: mirror, speak: () => {}, layout: grid.layout });
  grid.bind(NuxivaDesk.relayout);
  setInterval(tick, 1000); tick();
  NuxivaDelta.connectDelta("/api/stream/delta", onState, (ok) => $("link").classList.toggle("show", !ok));
})();
