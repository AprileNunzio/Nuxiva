(() => {
  const PRESENCE = Object.freeze({ core_hero: "normal", floating_orb: "small", ambient_stream: "mini", whisper_pill: "" });
  let form = "";

  function sceneFor(state) {
    const scenes = state && state.scene;
    if (!scenes || typeof scenes !== "object") return null;
    const desk = window.NuxivaDesk;
    const screen = desk && Number.isInteger(desk.screen) ? desk.screen : 0;
    return scenes[String(screen)] || scenes["0"] || null;
  }

  function apply(state) {
    const scene = sceneFor(state);
    const next = scene && Object.hasOwn(PRESENCE, scene.nucleus) ? scene.nucleus : "";
    if (next === form) return;
    form = next;
    if (next) document.body.dataset.nucleus = next;
    else delete document.body.dataset.nucleus;
    const D = window.NuxivaDisplay;
    const presence = PRESENCE[next];
    if (presence && D && typeof D.setPresence === "function" && !document.body.classList.contains("desk-full")) D.setPresence(presence);
    window.dispatchEvent(new CustomEvent("nuxiva:nucleus", { detail: { form: next } }));
  }

  window.addEventListener("nuxiva:state", (ev) => apply(ev.detail));
  window.NuxivaNucleus = Object.freeze({ get form() { return form; }, apply });
})();
