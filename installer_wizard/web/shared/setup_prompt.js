(() => {
  "use strict";
  const show = () => {
    if (document.querySelector(".setup-cta")) return;
    const a = document.createElement("a");
    a.className = "setup-cta";
    a.setAttribute("data-i18n-scope", "web/shared");
    a.href = "/setup";
    const icon = document.createElement("i");
    icon.textContent = "✦";
    const text = document.createElement("span");
    const strong = document.createElement("strong");
    PageText.bind(strong, "setup_cta");
    const small = document.createElement("small");
    PageText.bind(small, "setup_cta_sub");
    text.append(strong, small);
    a.append(icon, text);
    document.body.append(a);
  };
  fetch("/api/setup", { credentials: "same-origin", cache: "no-store" })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => { if (d && d.needed) show(); })
    .catch((error) => console.warn("stato della configurazione non letto", error));
})();
