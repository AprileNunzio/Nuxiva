(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const MODES = Object.freeze(["local", "remote", "cloud"]);
  const URL_RE = /^https?:\/\/[A-Za-z0-9.-]{1,253}(:\d{1,5})?(\/[A-Za-z0-9._~/-]{0,200})?$/;
  const gb = (v) => (typeof v === "number" ? `${v.toFixed(1)} GB` : null);

  function camerasOf(ctx) {
    return ctx.draft.cameras || { devices: ctx.config.cameras || [], scanned: Array.isArray(ctx.config.cameras) };
  }

  function paintCameras(ctx) {
    const cams = camerasOf(ctx);
    const grid = $("cam-matrix");
    grid.replaceChildren();
    cams.devices.forEach((device) => {
      const card = ctx.el("div", "metric-box cam-card");
      card.append(ctx.el("b", "", device.name || ctx.t("cam-unnamed")),
                  ctx.el("small", "", `${ctx.t(`cam-type-${device.type}`)} · ${device.host}`));
      grid.append(card);
    });
    if (cams.scanned && !cams.devices.length) grid.append(ctx.el("p", "live-note", ctx.t("cam-none")));
    $("cams-count-text").textContent = cams.scanned
      ? ctx.t("cam-count", { n: cams.devices.length, ms: cams.scan_ms ?? "—" }) + (cams.network_error ? ` · ${cams.network_error}` : "")
      : "";
  }

  async function scan(ctx) {
    const radar = $("cam-radar");
    const button = $("btn-cam-scan");
    radar.classList.add("scanning");
    button.disabled = true;
    try {
      const result = await ctx.net.json("/api/setup/cameras/scan", { method: "POST" });
      ctx.draft.cameras = { ...result, scanned: true };
      ctx.config.cameras = result.devices;
      ctx.log(ctx.t("log-cams", { n: result.count }));
    } catch (error) {
      ctx.fail(error);
    } finally {
      radar.classList.remove("scanning");
      button.disabled = false;
      paintCameras(ctx);
      ctx.refresh();
    }
  }

  const step5 = {
    render(ctx) {
      $("btn-cam-scan").onclick = () => scan(ctx);
      paintCameras(ctx);
      if (!camerasOf(ctx).scanned) return scan(ctx);
      return null;
    },
    collect: () => ({}),
    checks(ctx) {
      const cams = camerasOf(ctx);
      return [
        { key: "chk-cam-scan", ok: cams.scanned ? true : null },
        { key: "chk-cam-found", ok: cams.scanned ? cams.devices.length > 0 : null, vars: { n: cams.devices.length } }
      ];
    },
    analytics(ctx) {
      const cams = camerasOf(ctx);
      const count = (type) => cams.devices.filter((d) => d.type === type).length;
      return [["an-cams", cams.scanned ? cams.devices.length : null], ["an-cams-onvif", cams.scanned ? count("onvif") : null],
              ["an-cams-usb", cams.scanned ? count("usb") : null], ["an-scan-ms", cams.scan_ms !== undefined ? `${cams.scan_ms} ms` : null]];
    }
  };

  function brain(ctx) {
    const d = ctx.draft;
    const c = ctx.config;
    return {
      mode: d.brain || c.brain || "local",
      profile: d.profile || c.profile || "auto",
      packages: d.packages || c.packages || ctx.boot.suggested || []
    };
  }

  function choiceButton(ctx, label, sub, active, onClick, extraClass = "") {
    const button = ctx.el("button", `brain-card ${active ? "active" : ""} ${extraClass}`.trim());
    button.type = "button";
    button.setAttribute("aria-pressed", String(active));
    button.append(ctx.el("b", "", label));
    if (sub) button.append(ctx.el("small", "", sub));
    button.addEventListener("click", onClick);
    return button;
  }

  function paintBrain(ctx) {
    const b = brain(ctx);
    const hw = ctx.draft.hw || {};
    const modes = $("brain-modes");
    modes.replaceChildren(...MODES.map((m) => choiceButton(ctx, ctx.t(`brain-${m}`), ctx.t(`brain-${m}-sub`), b.mode === m, () => {
      ctx.draft.brain = m;
      paintBrain(ctx);
      ctx.refresh();
    }, "mode")));
    const presets = $("brain-presets");
    presets.hidden = b.mode !== "local";
    presets.replaceChildren(...Object.entries(ctx.boot.profiles || {}).map(([id, p]) => {
      const fits = !p.min_ram_gb || !hw.ram_gb || hw.ram_gb >= p.min_ram_gb;
      const sub = [p.model ? `${p.model} · ${gb(p.size_gb)}` : ctx.t("profile-auto-sub"),
                   p.min_ram_gb ? ctx.t("profile-ram", { gb: p.min_ram_gb }) : "",
                   id === hw.recommended ? ctx.t("profile-recommended") : "", fits ? "" : ctx.t("profile-too-big")].filter(Boolean).join(" · ");
      return choiceButton(ctx, ctx.t(`profile-${id}`), sub, b.profile === id, () => {
        ctx.draft.profile = id;
        paintBrain(ctx);
        ctx.refresh();
      }, fits ? "" : "warn");
    }));
    $("brain-remote").hidden = b.mode !== "remote";
    $("brain-cloud").hidden = b.mode !== "cloud";
    const grid = $("package-grid");
    grid.replaceChildren(...Object.entries(ctx.boot.packages || {}).map(([id, pkg]) => {
      const on = b.packages.includes(id);
      const sub = [gb(pkg.size_gb), pkg.heavy ? ctx.t("pkg-heavy") : "", (ctx.boot.suggested || []).includes(id) ? ctx.t("pkg-suggested") : ""].filter(Boolean).join(" · ");
      return choiceButton(ctx, ctx.t(`pkg-${id}`), sub, on, () => {
        ctx.draft.packages = on ? b.packages.filter((p) => p !== id) : [...b.packages, id];
        paintBrain(ctx);
      });
    }));
  }

  function paintHardware(ctx) {
    const hw = ctx.draft.hw;
    const grid = $("hw-grid");
    grid.replaceChildren();
    if (!hw) return;
    [["an-ram", gb(hw.ram_gb)], ["an-cpu", hw.cpu], ["an-gpu", hw.gpu_name ? `${hw.gpu_name}${hw.vram_total_gb ? ` · ${gb(hw.vram_total_gb)}` : ""}` : ctx.t("gpu-none")],
     ["an-disk", gb(hw.disk_free_gb)]].forEach(([k, v]) => {
      const cell = ctx.el("div", "metric-box");
      cell.append(ctx.el("span", "m-label", ctx.t(k)), ctx.el("b", "m-val", v ?? "—"));
      grid.append(cell);
    });
  }

  const step6 = {
    async render(ctx) {
      const provider = $("cloud-provider-in");
      provider.replaceChildren(ctx.el("option", "", ctx.t("brain-cloud-pick")), ...Object.entries(ctx.boot.clouds || {}).map(([id, name]) => {
        const opt = ctx.el("option", "", name);
        opt.value = id;
        return opt;
      }));
      provider.firstChild.value = "";
      provider.value = ctx.config.cloud_provider || "";
      $("ollama-url-in").value = ctx.config.ollama_url || "";
      $("ha-url-in").value = ctx.config.ha_url || "";
      $("cloud-key-in").placeholder = ctx.session.secrets_set.cloud_key ? ctx.t("secret-kept") : "";
      $("ha-token-in").placeholder = ctx.session.secrets_set.ha_token ? ctx.t("secret-kept") : ctx.t("ha-token");
      paintBrain(ctx);
      ctx.draft.hw = await ctx.hardware();
      paintHardware(ctx);
      paintBrain(ctx);
    },
    collect(ctx) {
      const b = brain(ctx);
      const out = { brain: b.mode, profile: b.profile, packages: b.packages, ollama_url: $("ollama-url-in").value.trim(),
                    cloud_provider: $("cloud-provider-in").value, ha_url: $("ha-url-in").value.trim() };
      const cloudKey = $("cloud-key-in").value.trim();
      const haToken = $("ha-token-in").value.trim();
      if (b.mode === "remote" && !URL_RE.test(out.ollama_url)) throw new Error("err-remote-url");
      if (b.mode === "cloud" && (!out.cloud_provider || (!cloudKey && !ctx.session.secrets_set.cloud_key))) throw new Error("err-cloud");
      if (out.ha_url && !URL_RE.test(out.ha_url)) throw new Error("err-ha");
      if (out.ha_url && !haToken && !ctx.session.secrets_set.ha_token) throw new Error("err-ha");
      if (cloudKey) out.cloud_key = cloudKey;
      if (haToken) out.ha_token = haToken;
      return out;
    },
    checks(ctx) {
      const hw = ctx.draft.hw;
      const b = brain(ctx);
      const p = (ctx.boot.profiles || {})[b.profile] || {};
      return [
        { key: "chk-hw", ok: hw ? true : null },
        { key: "chk-brain-fit", ok: b.mode !== "local" || !hw ? null : !p.min_ram_gb || hw.ram_gb >= p.min_ram_gb },
        { key: "chk-ha", ok: $("ha-url-in").value.trim() || ctx.config.ha_url ? true : null }
      ];
    },
    analytics(ctx) {
      const hw = ctx.draft.hw || {};
      return [["an-ram", gb(hw.ram_gb)], ["an-cpu", hw.cpu], ["an-gpu", hw.gpu_name || (ctx.draft.hw ? ctx.t("gpu-none") : null)],
              ["an-disk", gb(hw.disk_free_gb)], ["an-recommended", hw.recommended ? ctx.t(`profile-${hw.recommended}`) : null]];
    }
  };

  function summary(ctx) {
    const c = ctx.config;
    const samples = Object.values(c.wake_samples || {});
    return [
      [1, "step-1-name", c.locale],
      [2, "step-2-name", c.mic ? `SNR ${c.mic.snr_db.toFixed(1)} dB` : ctx.t("sum-skipped")],
      [3, "step-3-name", c.assistant_name ? `${c.assistant_name} · ${samples.filter((s) => s.usable).length}/3` : null],
      [4, "step-4-name", [c.owner_name, c.owner_last].filter(Boolean).join(" ") ? `${[c.owner_name, c.owner_last].filter(Boolean).join(" ")} · ${(c.face_views || []).length}/3` : null],
      [5, "step-5-name", Array.isArray(c.cameras) ? String(c.cameras.length) : ctx.t("sum-skipped")],
      [6, "step-6-name", c.brain === "local" ? ctx.t(`profile-${c.profile}`) : ctx.t(`brain-${c.brain}`)]
    ];
  }

  const step7 = {
    render(ctx) {
      const grid = $("matrix-summary");
      grid.replaceChildren(...summary(ctx).map(([step, key, value]) => {
        const card = ctx.el("div", `ready-summary-card ${value ? "" : "missing"}`);
        const text = ctx.el("div");
        text.append(ctx.el("b", "", ctx.t(key)), ctx.el("small", "", value || ctx.t("sum-missing")));
        const edit = ctx.el("button", "hud-btn-ghost", ctx.t("sum-edit"));
        edit.type = "button";
        edit.addEventListener("click", () => ctx.goToStep(step));
        card.append(text, edit);
        return card;
      }));
      const button = $("btn-final-launch");
      const msg = $("launch-msg");
      $("launch-btn-label").textContent = ctx.t("btn-activate", { name: (ctx.config.assistant_name || "").toUpperCase() });
      button.disabled = !ctx.config.assistant_name || !ctx.config.owner_name;
      msg.textContent = button.disabled ? ctx.t("launch-missing") : "";
      button.onclick = async () => {
        button.disabled = true;
        msg.textContent = ctx.t("launch-running");
        try {
          const result = await ctx.net.json("/api/setup/finalize", { method: "POST", json: {} });
          msg.textContent = ctx.t("launch-ok", { name: result.assistant_name });
          ctx.log(msg.textContent);
          setTimeout(() => window.location.replace("/"), 2500);
        } catch (error) {
          msg.textContent = error.message;
          ctx.fail(error);
          button.disabled = false;
        }
      };
    },
    checks(ctx) {
      const c = ctx.config;
      return [
        { key: "chk-ready-name", ok: Boolean(c.assistant_name) },
        { key: "chk-ready-owner", ok: Boolean(c.owner_name) },
        { key: "chk-ready-brain", ok: ctx.session.completed.includes(6) }
      ];
    },
    analytics(ctx) {
      return [["an-steps-done", `${ctx.session.completed.filter((s) => s < 7).length} / 6`]];
    }
  };

  window.SetupStepDefs = Object.assign(window.SetupStepDefs || {}, { 5: step5, 6: step6, 7: step7 });
})();
