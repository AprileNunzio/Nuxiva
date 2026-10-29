(() => {
  const LANGUAGES = ["it", "en", "fr", "es"];
  const FALLBACK = "en";
  const root = document.createElement("section");
  const button = document.createElement("button");
  const dot = document.createElement("i");
  const name = document.createElement("span");
  const free = document.createElement("span");
  const popover = document.createElement("div");
  const heading = document.createElement("p");
  const route = document.createElement("p");
  const pool = document.createElement("p");
  const change = document.createElement("p");
  let dictionary = {};
  let current = null;
  let previousId = "";
  let opened = false;

  root.className = "brain-route-host";
  root.dataset.surface = "brain_badge";
  root.hidden = true;
  button.className = "brain-route-button";
  button.type = "button";
  dot.className = "brain-route-dot";
  dot.setAttribute("aria-hidden", "true");
  name.className = "brain-route-name";
  free.className = "brain-route-free";
  popover.className = "brain-route-popover";
  popover.hidden = true;
  [heading, route, pool, change].forEach((item) => popover.append(item));
  button.append(dot, name, free);
  root.append(popover, button);
  document.body.append(root);

  const language = () => {
    const candidate = (document.documentElement.lang || FALLBACK).slice(0, 2).toLowerCase();
    return LANGUAGES.includes(candidate) ? candidate : FALLBACK;
  };

  const text = (key, values = {}) => {
    let value = dictionary[key] || key;
    Object.entries(values).forEach(([field, replacement]) => {
      value = value.split(`{${field}}`).join(String(replacement));
    });
    return value;
  };

  const loadLanguage = async () => {
    const selected = language();
    try {
      const response = await fetch(`/static/display/widgets/live_brain_badge/language/${selected}.json`, { cache: "force-cache" });
      if (!response.ok) throw new Error(`translation ${response.status}`);
      const result = await response.json();
      dictionary = result.dictionary || {};
      if (current) render(current);
    } catch (primaryError) {
      if (selected === FALLBACK) {
        console.error("Nuxiva display translations unavailable", primaryError);
        return;
      }
      try {
        const response = await fetch(`/static/display/widgets/live_brain_badge/language/${FALLBACK}.json`, { cache: "force-cache" });
        if (!response.ok) throw new Error(`fallback translation ${response.status}`);
        dictionary = (await response.json()).dictionary || {};
      } catch (fallbackError) {
        console.error("Nuxiva display translations unavailable", { primaryError, fallbackError });
      }
    }
  };

  const render = (event) => {
    current = event;
    const active = event.active_route || {};
    const failure = event.failover_event || {};
    name.textContent = `${active.provider_label || active.provider_id || ""} · ${active.model_short_name || active.model_id || ""}`;
    free.textContent = text("free");
    button.setAttribute("aria-label", text("active_model", { model: name.textContent }));
    button.setAttribute("aria-expanded", String(opened));
    popover.hidden = !opened;
    heading.textContent = text("active_model_title");
    route.textContent = text("model", { model: active.model_id || "" });
    pool.textContent = text("pool", { pool: text(`pool_${active.pool || "chat"}`) });
    change.textContent = failure.triggered
      ? text("switched", { previous: failure.previous_model || failure.previous_provider, next: active.model_id || "" })
      : "";
    root.hidden = !active.model_id || active.is_free_tier !== true;
    button.classList.toggle("brain-route-switch", failure.triggered === true && previousId !== active.model_id);
    previousId = active.model_id || "";
    window.setTimeout(() => button.classList.remove("brain-route-switch"), 2600);
  };

  button.addEventListener("click", () => {
    opened = !opened;
    if (current) render(current);
  });
  window.addEventListener("nuxiva-brain-route", (event) => render(event.detail || {}));
  new MutationObserver(() => void loadLanguage()).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  void loadLanguage();
})();
