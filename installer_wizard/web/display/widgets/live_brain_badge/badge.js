(() => {
  const LANGUAGES = ["it", "en", "fr", "es"];
  const FALLBACK = "en";
  const CONFIG_URL = "/api/v2/brain/config";
  const POLL_MS = 4000;
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
  let freeRoute = null;
  let configured = null;
  let revision = "";
  let previousId = "";
  let opened = false;
  let timer = 0;

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
  popover.setAttribute("aria-live", "polite");
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

  const clean = (value, max = 160) => (typeof value === "string" ? value.slice(0, max) : "");

  const describe = (entry) => {
    if (!entry || typeof entry !== "object") return null;
    const model = clean(entry.model);
    return model ? { model, provider: clean(entry.provider, 80) } : null;
  };

  const loadDictionary = async (selected) => {
    const response = await fetch(`/static/display/widgets/live_brain_badge/language/${selected}.json`, { cache: "force-cache" });
    if (!response.ok) throw new Error(`translation ${response.status}`);
    return (await response.json()).dictionary || {};
  };

  const loadLanguage = async () => {
    const selected = language();
    try {
      dictionary = await loadDictionary(selected);
    } catch (primaryError) {
      if (selected === FALLBACK) {
        console.error("Nuxiva display translations unavailable", primaryError);
        return;
      }
      try {
        dictionary = await loadDictionary(FALLBACK);
      } catch (fallbackError) {
        console.error("Nuxiva display translations unavailable", { primaryError, fallbackError });
        return;
      }
    }
    render();
  };

  const flash = () => {
    button.classList.add("brain-route-switch");
    window.setTimeout(() => button.classList.remove("brain-route-switch"), 2600);
  };

  const renderFree = (event) => {
    const active = event.active_route || {};
    const failure = event.failover_event || {};
    name.textContent = `${active.provider_label || active.provider_id || ""} · ${active.model_short_name || active.model_id || ""}`;
    free.textContent = text("free");
    free.hidden = false;
    heading.textContent = text("active_model_title");
    route.textContent = text("model", { model: active.model_id || "" });
    pool.textContent = text("pool", { pool: text(`pool_${active.pool || "chat"}`) });
    change.textContent = failure.triggered
      ? text("switched", { previous: failure.previous_model || failure.previous_provider, next: active.model_id || "" })
      : "";
    if (failure.triggered === true && previousId !== active.model_id) flash();
    previousId = active.model_id || "";
    return Boolean(active.model_id);
  };

  const renderConfigured = () => {
    const talking = configured && configured.talking;
    if (!talking) return false;
    const working = configured.working;
    name.textContent = talking.provider ? `${talking.provider} · ${talking.model}` : talking.model;
    free.textContent = "";
    free.hidden = true;
    heading.textContent = text("now_title");
    route.textContent = text("talking", { model: talking.model });
    pool.textContent = working ? text("working", { model: working.model }) : "";
    change.textContent = configured.updated ? text("updated") : "";
    return true;
  };

  function render() {
    const usingFree = freeRoute && (freeRoute.active_route || {}).is_free_tier === true;
    const visible = usingFree ? renderFree(freeRoute) : renderConfigured();
    button.setAttribute("aria-label", text("active_model", { model: name.textContent }));
    button.setAttribute("aria-expanded", String(opened));
    popover.hidden = !opened;
    root.hidden = !visible;
  }

  const poll = async () => {
    window.clearTimeout(timer);
    if (!document.hidden) {
      try {
        const response = await fetch(CONFIG_URL, { cache: "no-store", credentials: "same-origin" });
        if (!response.ok) throw new Error(`brain config ${response.status}`);
        const data = await response.json();
        const next = clean(data.revision, 64);
        const updated = Boolean(revision) && next !== revision;
        configured = { talking: describe(data.active), working: describe(data.working), updated: updated || Boolean(configured && configured.updated) };
        if (updated) {
          freeRoute = null;
          flash();
        }
        revision = next;
        render();
      } catch (error) {
        console.error("Nuxiva brain badge refresh failed", error);
      }
    }
    timer = window.setTimeout(poll, POLL_MS);
  };

  button.addEventListener("click", () => {
    opened = !opened;
    if (!opened && configured) configured.updated = false;
    render();
  });
  window.addEventListener("nuxiva-brain-route", (event) => {
    freeRoute = event.detail || null;
    render();
  });
  document.addEventListener("visibilitychange", () => !document.hidden && void poll());
  new MutationObserver(() => void loadLanguage()).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  void loadLanguage();
  void poll();
})();
