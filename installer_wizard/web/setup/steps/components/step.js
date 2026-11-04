(() => {
  "use strict";

  class StepComponents {
    renderList(containerId, list) {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.innerHTML = "";

      const selected = window.SetupStorage.get("selectedComponents") || ["voice", "ear", "vision", "sandbox", "brain_local"];
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepComponentsI18n && window.SetupStepComponentsI18n.dict[lang]) || {};

      list.forEach((pkg) => {
        const isChecked = selected.includes(pkg.id);
        const card = document.createElement("div");
        card.className = `os-card-addon ${isChecked ? "is-selected" : ""}`;

        const info = document.createElement("div");
        info.className = "os-card-addon-info";

        const header = document.createElement("div");
        header.className = "os-card-addon-header";

        const name = document.createElement("span");
        name.className = "os-card-addon-name";
        name.textContent = pkg.title;
        header.appendChild(name);

        const size = document.createElement("span");
        size.className = "os-card-addon-size";
        size.textContent = pkg.size;
        header.appendChild(size);

        if (pkg.core) {
          const coreBadge = document.createElement("span");
          coreBadge.className = "os-badge-core";
          coreBadge.textContent = dict.badge_core || "Obbligatorio";
          header.appendChild(coreBadge);
        }

        const desc = document.createElement("span");
        desc.className = "os-card-addon-desc";
        desc.textContent = pkg.desc;

        info.appendChild(header);
        info.appendChild(desc);

        const toggleCtrl = document.createElement("div");
        toggleCtrl.className = "os-toggle-control";

        const toggleSwitch = document.createElement("label");
        toggleSwitch.className = "os-toggle-switch";

        const inp = document.createElement("input");
        inp.type = "checkbox";
        inp.className = "os-toggle-input";
        inp.checked = isChecked;
        inp.disabled = Boolean(pkg.core);

        const slider = document.createElement("span");
        slider.className = "os-toggle-slider";

        toggleSwitch.appendChild(inp);
        toggleSwitch.appendChild(slider);
        toggleCtrl.appendChild(toggleSwitch);

        const updateState = (newChecked) => {
          if (pkg.core) return;
          inp.checked = newChecked;
          let sel = [...(window.SetupStorage.get("selectedComponents") || [])];
          if (newChecked) {
            if (!sel.includes(pkg.id)) sel.push(pkg.id);
            card.classList.add("is-selected");
          } else {
            sel = sel.filter((id) => id !== pkg.id);
            card.classList.remove("is-selected");
          }
          window.SetupStorage.set("selectedComponents", sel);
        };

        inp.addEventListener("change", (e) => {
          updateState(e.target.checked);
        });

        card.addEventListener("click", (e) => {
          if (e.target.closest(".os-toggle-switch")) return;
          if (pkg.core) return;
          updateState(!inp.checked);
        });

        card.appendChild(info);
        card.appendChild(toggleCtrl);
        container.appendChild(card);
      });
    }

    render() {
      const i18n = window.SetupStepComponentsI18n;
      if (!i18n) return;
      if (document.getElementById("components-list-core")) {
        this.renderList("components-list-core", i18n.packagesCore);
      }
      if (document.getElementById("components-list-opt")) {
        this.renderList("components-list-opt", i18n.packagesOpt);
      }
      if (document.getElementById("components-list")) {
        this.renderList("components-list", i18n.packages);
      }
    }

    init() {
      this.render();
    }
  }

  window.SetupStepComponents = new StepComponents();
})();
