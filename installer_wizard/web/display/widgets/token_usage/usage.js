(() => {
  const LANGUAGES = ["it", "en", "fr", "es"];
  const FALLBACK = "en";
  const SURFACE = "token_usage";
  const USAGE_URL = "/api/brain/usage";
  const POLL_MS = 30000;
  const root = document.createElement("section");
  const title = document.createElement("p");
  const figures = document.createElement("div");
  const today = document.createElement("span");
  const month = document.createElement("span");
  const track = document.createElement("div");
  const bar = document.createElement("i");
  const note = document.createElement("p");
  let dictionary = {};
  let data = null;
  let timer = 0;

  root.className = "token-usage-host";
  root.dataset.surface = SURFACE;
  root.setAttribute("aria-live", "polite");
  title.className = "token-usage-title";
  figures.className = "token-usage-figures";
  track.className = "token-usage-track";
  track.setAttribute("role", "meter");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");
  note.className = "token-usage-note";
  track.append(bar);
  figures.append(today, month);
  root.append(title, figures, track, note);
  root.hidden = true;
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

  const count = (value) => (typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : 0);
  const compact = (value) => new Intl.NumberFormat(language(), { notation: "compact", maximumFractionDigits: 1 }).format(count(value));
  const enabled = () => Boolean(window.NuxivaDisplay && window.NuxivaDisplay.Surfaces && window.NuxivaDisplay.Surfaces.enabled(SURFACE));

  const loadDictionary = async (selected) => {
    const response = await fetch(`/static/display/widgets/token_usage/language/${selected}.json`, { cache: "force-cache" });
    if (!response.ok) throw new Error(`translation ${response.status}`);
    return (await response.json()).dictionary || {};
  };

  const loadLanguage = async () => {
    const selected = language();
    try {
      dictionary = await loadDictionary(selected);
    } catch (primaryError) {
      if (selected === FALLBACK) {
        console.error("Nuxiva token widget translations unavailable", primaryError);
        return;
      }
      try {
        dictionary = await loadDictionary(FALLBACK);
      } catch (fallbackError) {
        console.error("Nuxiva token widget translations unavailable", { primaryError, fallbackError });
        return;
      }
    }
    render();
  };

  function render() {
    if (!data || !enabled()) {
      root.hidden = true;
      return;
    }
    title.textContent = text("title");
    today.textContent = text("today", { n: compact(data.today) });
    month.textContent = text("month", { n: compact(data.month) });
    const used = typeof data.used === "number" && data.used >= 0 ? Math.min(1, data.used) : null;
    track.hidden = used === null;
    if (used !== null) {
      const percent = Math.round(used * 100);
      bar.style.width = `${percent}%`;
      bar.dataset.level = percent >= 90 ? "high" : percent >= 70 ? "mid" : "low";
      track.setAttribute("aria-valuenow", String(percent));
      track.setAttribute("aria-label", text("budget", { used: compact(data.cloud), cap: compact(data.budget) }));
      note.textContent = text("budget", { used: compact(data.cloud), cap: compact(data.budget) });
    } else {
      note.textContent = text("no_budget");
    }
    root.hidden = false;
  }

  const poll = async () => {
    window.clearTimeout(timer);
    if (!document.hidden && enabled()) {
      try {
        const response = await fetch(USAGE_URL, { cache: "no-store", credentials: "same-origin" });
        if (!response.ok) throw new Error(`token usage ${response.status}`);
        data = await response.json();
      } catch (error) {
        console.error("Nuxiva token widget refresh failed", error);
      }
    }
    render();
    timer = window.setTimeout(poll, POLL_MS);
  };

  window.addEventListener("nuxiva-surfaces", () => void poll());
  document.addEventListener("visibilitychange", () => !document.hidden && void poll());
  new MutationObserver(() => void loadLanguage()).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  void loadLanguage();
  void poll();
})();
