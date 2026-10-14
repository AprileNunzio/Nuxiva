(() => {
  const A = window.NuxivaAdmin, { $, fmt } = A;
  const BADGE = { installed: "ok", installing: "running", queued: "warn", failed: "down" };
  let mode = "pending";
  let pick = "local";

  function selectMode(m) {
    pick = m;
    for (const b of $("brain-mode").children) {
      b.classList.toggle("on", b.dataset.mode === m);
      b.setAttribute("aria-checked", String(b.dataset.mode === m));
    }
    $("brain-url").hidden = m !== "remote";
    $("brain-save").hidden = m === mode && m !== "remote";
  }

  function render(d) {
    mode = d.brain;
    $("brain-note").textContent = A.t("packages.note_" + mode) || "";
    selectMode(mode === "pending" ? "local" : mode);
    $("pkg-body").innerHTML = d.packages.map((p) => {
      const on = p.wanted;
      const action = p.state === "installing" ? ""
        : !on ? `<button class="btn sm primary" type="button" data-pkg="${fmt.esc(p.id)}" data-on="1">${fmt.esc(A.t("packages.install"))}</button>`
        : p.removable ? `<button class="btn sm" type="button" data-pkg="${fmt.esc(p.id)}" data-on="0">${fmt.esc(A.t("packages.remove"))}</button>` : "";
      const dev = p.detected ? ` · ${fmt.esc(A.t("packages.device_detected"))}` : "";
      const heavy = p.heavy ? ` · ${fmt.esc(A.t("packages.heavy_for_system"))}` : "";
      const stateLabel = A.t("packages.state_" + p.state) || p.state;
      return `<tr><td>${fmt.esc(p.title)}<div class="faint" style="font-size:12px">${fmt.esc(p.description)}${dev}${heavy}</div></td>
        <td class="mono">${Number(p.size_gb).toFixed(1)} GB</td>
        <td><span class="badge ${BADGE[p.state] || ""}">${fmt.esc(stateLabel)}</span></td>
        <td style="text-align:right">${action}</td></tr>`;
    }).join("");
  }

  const load = () => A.api("GET", "/api/packages").then(render).catch((e) => A.toast(e.message, true));

  function init() {
    $("brain-mode").addEventListener("click", (e) => {
      const b = e.target.closest("[data-mode]");
      if (b) selectMode(b.dataset.mode);
    });
    $("brain-save").addEventListener("click", async () => {
      const b = $("brain-save");
      const body = { mode: pick };
      if (pick === "remote") body.url = $("brain-url").value.trim();
      if (pick !== mode && !confirm(A.t("packages.confirm_brain"))) return;
      b.disabled = true;
      try {
        await A.api("POST", "/api/packages/brain", body);
        A.toast(A.t("packages.saved_applying"));
        await load();
      } catch (err) {
        A.toast(err.message, true);
      } finally {
        b.disabled = false;
      }
    });
    $("pkg-body").addEventListener("click", async (e) => {
      const b = e.target.closest("[data-pkg]");
      if (!b) return;
      const on = b.dataset.on === "1";
      if (!on && !confirm(A.t("packages.confirm_remove"))) return;
      b.disabled = true;
      try {
        await A.api("POST", `/api/packages/${encodeURIComponent(b.dataset.pkg)}`, { on });
        A.toast(on ? A.t("packages.installed_bg") : A.t("packages.deactivated"));
        await load();
      } catch (err) {
        A.toast(err.message, true);
        b.disabled = false;
      }
    });
    setInterval(() => { if (A.isOn("packages")) load(); }, 5000);
  }

  A.tab("packages", { title: A.t("packages.title"), init, load });
})();
