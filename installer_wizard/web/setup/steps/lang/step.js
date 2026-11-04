(() => {
  "use strict";

  class StepLang {
    constructor() {
      this.filter = "";
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = window.SetupStepLangI18n.dict[lang] || window.SetupStepLangI18n.dict.it;
      return dict[key] || key;
    }

    render() {
      const container = document.getElementById("lang-list");
      if (!container) return;
      container.innerHTML = "";

      const currentLang = window.SetupStorage.get("lang") || "it";
      const filterText = this.filter.toLowerCase().trim();

      const list = window.SetupStepLangI18n.languages.filter((l) => {
        if (!filterText) return true;
        return l.name.toLowerCase().includes(filterText) ||
               l.sub.toLowerCase().includes(filterText) ||
               l.code.toLowerCase().includes(filterText);
      });

      if (list.length === 0) {
        const empty = document.createElement("div");
        empty.className = "os-lang-empty";
        empty.textContent = this.t("no_results");
        container.appendChild(empty);
        return;
      }

      list.forEach((l) => {
        const isSelected = l.code === currentLang;
        const item = document.createElement("div");
        item.className = `os-lang-item ${isSelected ? "is-selected" : ""}`;
        item.setAttribute("role", "option");
        item.setAttribute("tabindex", "0");
        item.setAttribute("aria-selected", isSelected ? "true" : "false");
        item.setAttribute("data-lang", l.code);

        const badge = document.createElement("span");
        badge.className = "os-lang-badge";
        badge.textContent = l.badge;

        const info = document.createElement("div");
        info.className = "os-lang-info";

        const name = document.createElement("span");
        name.className = "os-lang-primary";
        name.textContent = l.name;

        const sub = document.createElement("span");
        sub.className = "os-lang-secondary";
        sub.textContent = l.sub;

        info.appendChild(name);
        info.appendChild(sub);

        const svgNs = "http:" + "//www.w3.org/2000/svg";
        const check = document.createElementNS(svgNs, "svg");
        check.setAttribute("class", "os-lang-check");
        check.setAttribute("width", "18");
        check.setAttribute("height", "18");
        check.setAttribute("viewBox", "0 0 24 24");
        check.setAttribute("fill", "none");
        check.setAttribute("stroke", "currentColor");
        check.setAttribute("stroke-width", "2.8");
        check.setAttribute("stroke-linecap", "round");
        check.setAttribute("stroke-linejoin", "round");
        check.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';

        item.appendChild(badge);
        item.appendChild(info);
        item.appendChild(check);

        const select = () => {
          window.SetupStorage.set("lang", l.code);
          document.documentElement.setAttribute("lang", l.code);
          this.render();
          if (window.SetupApp && typeof window.SetupApp.onLangChanged === "function") {
            window.SetupApp.onLangChanged(l.code);
          }
        };

        item.addEventListener("click", select);
        item.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            select();
          }
        });

        container.appendChild(item);
      });
    }

    init() {
      const searchInp = document.getElementById("lang-search-input");
      if (searchInp) {
        searchInp.setAttribute("placeholder", this.t("search_placeholder"));
        searchInp.addEventListener("input", (e) => {
          this.filter = e.target.value;
          this.render();
        });
      }
      this.render();
    }
  }

  window.SetupStepLang = new StepLang();
})();
