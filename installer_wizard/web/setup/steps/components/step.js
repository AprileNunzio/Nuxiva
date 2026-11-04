(() => {
  "use strict";

  class StepComponents {
    render() {
      const container = document.getElementById("components-list");
      if (!container) return;
      container.innerHTML = "";

      const selected = window.SetupStorage.get("selectedComponents") || ["voice", "ear", "vision", "sandbox", "brain_local"];

      window.SetupStepComponentsI18n.packages.forEach((pkg) => {
        const isChecked = selected.includes(pkg.id);
        const card = document.createElement("label");
        card.className = `os-card-addon ${isChecked ? "is-selected" : ""}`;

        const checkWrap = document.createElement("div");
        checkWrap.className = "os-checkbox-wrapper";

        const inp = document.createElement("input");
        inp.type = "checkbox";
        inp.className = "os-checkbox-input";
        inp.checked = isChecked;
        inp.disabled = pkg.core;

        inp.addEventListener("change", () => {
          let list = [...(window.SetupStorage.get("selectedComponents") || [])];
          if (inp.checked) {
            if (!list.includes(pkg.id)) list.push(pkg.id);
            card.classList.add("is-selected");
          } else {
            list = list.filter((id) => id !== pkg.id);
            card.classList.remove("is-selected");
          }
          window.SetupStorage.set("selectedComponents", list);
        });

        const box = document.createElement("div");
        box.className = "os-checkbox-box";
        box.innerHTML = '<svg class="os-checkbox-tick" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';

        checkWrap.appendChild(inp);
        checkWrap.appendChild(box);

        const info = document.createElement("div");
        info.className = "os-card-addon-info";

        const name = document.createElement("span");
        name.className = "os-card-addon-name";
        name.textContent = pkg.title;

        const badge = document.createElement("span");
        badge.className = "os-card-addon-badge";
        badge.textContent = pkg.size;
        name.appendChild(badge);

        const desc = document.createElement("span");
        desc.className = "os-card-addon-desc";
        desc.textContent = pkg.desc;

        info.appendChild(name);
        info.appendChild(desc);

        card.appendChild(checkWrap);
        card.appendChild(info);
        container.appendChild(card);
      });
    }

    init() {
      this.render();
    }
  }

  window.SetupStepComponents = new StepComponents();
})();
