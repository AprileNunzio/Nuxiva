(() => {
  const D = window.NuxivaDisplay;
  const LIST = Object.freeze([
    { id: "show_clock", key: "surf_clock", flag: true },
    { id: "show_date", key: "surf_date", flag: true },
    { id: "show_presence", key: "surf_presence", flag: true },
    { id: "show_thinking", key: "surf_thinking", flag: true },
    { id: "show_telemetry_chips", key: "surf_chips", flag: true },
    { id: "show_desk_widgets", key: "surf_desk", flag: true },
    { id: "rail_voice", key: "surf_rail_voice", def: false },
    { id: "rail_home", key: "surf_rail_home", def: true },
    { id: "rail_scan", key: "surf_rail_scan", def: true },
    { id: "rail_vitals", key: "surf_rail_vitals", def: true },
    { id: "rail_learned", key: "surf_rail_learned", def: true },
    { id: "project", key: "surf_project", def: true },
    { id: "music_clock", key: "surf_music_clock", def: true },
    { id: "brain_badge", key: "surf_brain_badge", def: true },
  ]);
  const OWN = LIST.filter((s) => !s.flag);
  let settings = {};

  const enabled = (id) => {
    const item = LIST.find((s) => s.id === id);
    if (!item) return false;
    if (item.flag) return settings[id] !== false;
    return settings.surfaces && typeof settings.surfaces[id] === "boolean" ? settings.surfaces[id] : item.def;
  };

  function apply(cfg) {
    settings = cfg || {};
    document.body.dataset.surfacesOff = OWN.filter((s) => !enabled(s.id)).map((s) => s.id).join(" ");
    window.dispatchEvent(new CustomEvent("nuxiva-surfaces"));
    if (window.NuxivaDesk) window.NuxivaDesk.relayout();
  }

  async function save(body) {
    const r = await fetch("/api/system/display-settings", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    if (d && d.settings) {
      try { localStorage.setItem("nuxiva_display_settings", JSON.stringify(d.settings)); } catch (_) {}
      if (D.applyDisplaySettings) D.applyDisplaySettings(d.settings);
      else apply(d.settings);
    }
    return d.settings || null;
  }

  function set(id, on) {
    const item = LIST.find((s) => s.id === id);
    if (!item || typeof on !== "boolean") return Promise.reject(new TypeError(id));
    return save(item.flag ? { [id]: on } : { surfaces: { [id]: on } });
  }

  D.Surfaces = Object.freeze({ list: LIST, enabled, apply, set, save, get settings() { return settings; } });
})();
