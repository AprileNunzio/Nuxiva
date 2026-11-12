(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const Audio = window.SetupAudio;
  const NAME_RE = /^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{0,31}$/;
  const FIRST_RE = /^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ-]{0,39}$/;
  const WAKE_PREFIX = /^(?:hey|hei|ehi|hi|ok|okay)\s+/i;
  const SUGGESTED_NAMES = Object.freeze(["Aria", "Atlas", "Athena", "Orion", "Nova"]);
  const FACE_KINDS = Object.freeze(["front", "three_left", "three_right"]);
  const LANGS = Object.freeze([["it", "Italiano"], ["en", "English"], ["es", "Español"], ["fr", "Français"]]);
  let scope = null;

  const db = (v) => (typeof v === "number" ? `${v.toFixed(1)} dB` : null);
  const wakeWord = (name) => String(name || "").trim().replace(WAKE_PREFIX, "").trim().toLowerCase();

  function stopMic() {
    if (scope) scope.stop();
    Audio.close();
  }

  async function micOrExplain(ctx, target) {
    if (!Audio.available()) throw new Error("mic-unavailable");
    try {
      const mic = await Audio.open();
      if (target) {
        if (!scope) scope = new window.SetupCanvas.LiveScope(target);
        scope.attach(mic.analyser);
      }
      return mic;
    } catch (error) {
      if (error && error.name === "NotAllowedError") throw new Error("mic-denied");
      if (error && error.name === "NotFoundError") throw new Error("mic-missing");
      throw error;
    }
  }

  const step1 = {
    async render(ctx) {
      const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      ctx.draft.browserTz = browserTz;
      $("tz-browser").textContent = browserTz || "—";
      const grid = $("lang-cards");
      grid.replaceChildren();
      LANGS.forEach(([code, name]) => {
        const card = ctx.el("button", `lang-hud-card ${ctx.lang() === code ? "active" : ""}`);
        card.type = "button";
        card.setAttribute("aria-pressed", String(ctx.lang() === code));
        card.append(ctx.el("b", "", name), ctx.el("small", "", code.toUpperCase()));
        card.addEventListener("click", () => ctx.switchLanguage(code).catch(ctx.fail));
        grid.append(card);
      });
      const hw = await ctx.hardware();
      $("tz-server").textContent = hw.timezone || "—";
      $("tz-mismatch").hidden = !browserTz || !hw.timezone || browserTz === hw.timezone;
      ctx.refresh();
    },
    collect: (ctx) => ({ locale: ctx.locales[ctx.lang()] }),
    checks: (ctx) => {
      const server = $("tz-server").textContent;
      return [
        { key: "chk-lang", ok: true, vars: { lang: ctx.lang().toUpperCase() } },
        { key: "chk-tz-read", ok: server !== "—" ? true : null },
        { key: "chk-tz-match", ok: server === "—" ? null : server === ctx.draft.browserTz }
      ];
    },
    analytics: (ctx) => [["an-locale", ctx.locales[ctx.lang()]], ["an-tz-browser", ctx.draft.browserTz], ["an-tz-server", $("tz-server").textContent]]
  };

  function micVerdict(snr) {
    if (typeof snr !== "number") return null;
    return snr >= 25 ? "mic-good" : snr >= 15 ? "mic-ok" : "mic-poor";
  }

  function paintMic(ctx) {
    const mic = ctx.draft.mic || ctx.config.mic;
    const box = $("mic-results");
    box.replaceChildren();
    if (!mic) return;
    [["an-noise", db(mic.noise_db)], ["an-voice", db(mic.voice_db)], ["an-snr", db(mic.snr_db)]]
      .forEach(([k, v]) => {
        const cell = ctx.el("div", "metric-box");
        cell.append(ctx.el("span", "m-label", ctx.t(k)), ctx.el("b", "m-val", v));
        box.append(cell);
      });
  }

  const step2 = {
    render(ctx) {
      const button = $("btn-mic-measure");
      const msg = $("mic-phase-msg");
      button.disabled = !Audio.available();
      msg.textContent = Audio.available() ? "" : ctx.t("mic-unavailable");
      paintMic(ctx);
      button.onclick = async () => {
        button.disabled = true;
        try {
          const mic = await micOrExplain(ctx, $("canvas-scope"));
          scope.setMarks([]);
          msg.textContent = ctx.t("mic-phase-silence");
          const quiet = await Audio.sampleLevels(mic, 3000);
          scope.setMarks([{ label: ctx.t("mark-noise"), db: quiet.low, color: "#ff3366" }]);
          msg.textContent = ctx.t("mic-phase-voice");
          const voice = await Audio.sampleLevels(mic, 4000);
          const result = { noise_db: Math.round(quiet.low * 10) / 10, voice_db: Math.round(voice.high * 10) / 10,
                           snr_db: Math.round((voice.high - quiet.low) * 10) / 10, sample_rate: mic.rate, device: mic.label.slice(0, 120) };
          scope.setMarks([{ label: ctx.t("mark-noise"), db: result.noise_db, color: "#ff3366" },
                          { label: ctx.t("mark-voice"), db: result.voice_db, color: "#00ffaa" }]);
          ctx.draft.mic = result;
          msg.textContent = ctx.t(micVerdict(result.snr_db));
          ctx.log(ctx.t("log-mic", { snr: result.snr_db.toFixed(1) }));
          paintMic(ctx);
          ctx.refresh();
        } catch (error) {
          msg.textContent = ctx.t(error.message);
          ctx.fail(error);
        } finally {
          button.disabled = !Audio.available();
        }
      };
    },
    leave: stopMic,
    collect: (ctx) => (ctx.draft.mic ? { mic: ctx.draft.mic } : {}),
    checks: (ctx) => {
      const mic = ctx.draft.mic || ctx.config.mic;
      return [
        { key: "chk-mic-access", ok: Audio.available() },
        { key: "chk-mic-noise", ok: mic ? true : null },
        { key: "chk-mic-snr", ok: mic ? mic.snr_db >= 15 : null }
      ];
    },
    analytics: (ctx) => {
      const mic = ctx.draft.mic || ctx.config.mic;
      return [["an-noise", mic && db(mic.noise_db)], ["an-voice", mic && db(mic.voice_db)], ["an-snr", mic && db(mic.snr_db)],
              ["an-device", mic && mic.device], ["an-rate", mic && `${mic.sample_rate} Hz`]];
    }
  };

  function voiceFor(ctx, gender) {
    const id = ((ctx.boot.voices_by_lang_gender || {})[ctx.lang()] || {})[gender] || "";
    return { id, label: (ctx.boot.voices || {})[id] || id };
  }

  function assistantName(ctx) {
    return ctx.draft.assistant_name ?? ctx.config.assistant_name ?? "";
  }

  function paintRings(ctx) {
    const name = assistantName(ctx).trim();
    $("ring-prompt-txt").textContent = name ? ctx.t("wake-prompt", { name }) : ctx.t("wake-need-name");
    const box = $("wake-rings");
    box.replaceChildren();
    const samples = ctx.config.wake_samples || {};
    [1, 2, 3].forEach((i) => {
      const sample = samples[String(i)];
      const ring = ctx.el("button", `chamber-ring ${sample ? (sample.usable ? "passed" : "failed") : ""}`);
      ring.type = "button";
      ring.disabled = !name || !Audio.available();
      ring.append(ctx.el("span", "r-num", i), ctx.el("small", "", ctx.t(`wake-shot-${i}`, { name })));
      if (sample) ring.append(ctx.el("small", "r-metric", `SNR ${sample.snr_db.toFixed(1)} dB · ${ctx.t(sample.usable ? "wake-usable" : `wake-${sample.reason || "weak"}`)}`));
      ring.addEventListener("click", () => recordShot(ctx, i, ring));
      box.append(ring);
    });
  }

  async function recordShot(ctx, index, ring) {
    const name = assistantName(ctx).trim();
    if (!NAME_RE.test(name)) return ctx.fail(new Error("err-assistant-name"));
    ring.classList.add("active");
    try {
      const mic = await micOrExplain(ctx);
      await ctx.save({ assistant_name: name, assistant_gender: ctx.draft.gender || ctx.config.assistant_gender });
      ctx.status(ctx.t("wake-recording", { name }));
      const blob = await Audio.record(mic, 2200);
      const result = await ctx.net.json(`/api/setup/wake-sample?index=${index}`, { method: "POST", body: blob, headers: { "Content-Type": "audio/wav" } });
      ctx.config.wake_samples = { ...(ctx.config.wake_samples || {}), [String(index)]: result };
      ctx.status(ctx.t(result.usable ? "wake-usable" : `wake-${result.reason || "weak"}`), result.usable ? "ok" : "error");
      ctx.log(ctx.t("log-wake", { n: index, snr: result.snr_db.toFixed(1), speech: result.speech_db.toFixed(1) }));
    } catch (error) {
      ctx.fail(error);
    } finally {
      ring.classList.remove("active");
      paintRings(ctx);
      ctx.refresh();
    }
  }

  function paintVoices(ctx) {
    const box = $("voice-cards");
    box.replaceChildren();
    const gender = ctx.draft.gender || ctx.config.assistant_gender || "female";
    ["female", "male"].forEach((g) => {
      const card = ctx.el("button", `voice-card ${g === gender ? "active" : ""}`);
      card.type = "button";
      card.setAttribute("aria-pressed", String(g === gender));
      card.append(ctx.el("b", "", ctx.t(`voice-${g}`)), ctx.el("small", "", voiceFor(ctx, g).label));
      card.addEventListener("click", () => {
        ctx.draft.gender = g;
        paintVoices(ctx);
        ctx.refresh();
      });
      box.append(card);
    });
  }

  const step3 = {
    render(ctx) {
      const input = $("input-assistant-name");
      input.value = assistantName(ctx);
      input.oninput = () => {
        ctx.draft.assistant_name = input.value;
        paintRings(ctx);
        ctx.refresh();
      };
      const chips = $("quick-name-chips");
      chips.replaceChildren();
      SUGGESTED_NAMES.forEach((name) => {
        const chip = ctx.el("button", "chip", name);
        chip.type = "button";
        chip.addEventListener("click", () => { input.value = name; input.oninput(); });
        chips.append(chip);
      });
      paintVoices(ctx);
      paintRings(ctx);
      $("btn-voice-preview").onclick = async () => {
        const name = assistantName(ctx).trim() || "Nuxiva";
        try {
          const response = await ctx.net.request("/api/setup/voice_preview", { method: "POST", json: { lang: ctx.lang(), gender: ctx.draft.gender || ctx.config.assistant_gender, name } });
          const url = URL.createObjectURL(await response.blob());
          const player = new window.Audio(url);
          player.onended = () => URL.revokeObjectURL(url);
          await player.play();
          ctx.draft.previewOk = true;
          ctx.log(ctx.t("log-preview", { voice: voiceFor(ctx, ctx.draft.gender || ctx.config.assistant_gender).label }));
        } catch (error) {
          ctx.draft.previewOk = false;
          ctx.fail(error);
        }
        ctx.refresh();
      };
    },
    leave: stopMic,
    collect(ctx) {
      const name = assistantName(ctx).trim();
      if (!NAME_RE.test(name)) throw new Error("err-assistant-name");
      return { assistant_name: name, assistant_gender: ctx.draft.gender || ctx.config.assistant_gender || "female" };
    },
    checks(ctx) {
      const samples = Object.values(ctx.config.wake_samples || {});
      return [
        { key: "chk-name", ok: NAME_RE.test(assistantName(ctx).trim()) },
        { key: "chk-voice-heard", ok: ctx.draft.previewOk === undefined ? null : ctx.draft.previewOk },
        { key: "chk-wake", ok: samples.length ? samples.some((s) => s.usable) : null, vars: { n: samples.filter((s) => s.usable).length } }
      ];
    },
    analytics(ctx) {
      const samples = Object.values(ctx.config.wake_samples || {});
      const best = samples.reduce((m, s) => Math.max(m, s.snr_db), -Infinity);
      return [["an-wake-word", wakeWord(assistantName(ctx))], ["an-voice-id", voiceFor(ctx, ctx.draft.gender || ctx.config.assistant_gender).label],
              ["an-wake-samples", `${samples.filter((s) => s.usable).length} / 3`], ["an-wake-best", samples.length ? db(best) : null]];
    }
  };

  function ownerNames(ctx) {
    return { first: ($("owner-first-input").value || "").trim(), last: ($("owner-last-input").value || "").trim() };
  }

  function validateOwner(ctx) {
    const { first, last } = ownerNames(ctx);
    if (!FIRST_RE.test(first)) throw new Error("err-owner-name");
    const assistant = wakeWord(ctx.config.assistant_name);
    if (assistant && first.toLowerCase() === assistant) throw new Error("err-name-conflict");
    return { owner_name: first, owner_last: last };
  }

  function paintFaces(ctx) {
    const box = $("face-shots");
    box.replaceChildren();
    const done = ctx.config.face_views || [];
    FACE_KINDS.forEach((kind) => {
      const button = ctx.el("button", `face-shot ${done.includes(kind) ? "passed" : ""}`);
      button.type = "button";
      button.append(ctx.el("b", "", ctx.t(`face-${kind}`)), ctx.el("small", "", ctx.t(done.includes(kind) ? "face-done" : "face-todo")));
      button.addEventListener("click", () => captureFace(ctx, kind, button));
      box.append(button);
    });
  }

  async function captureFace(ctx, kind, button) {
    const msg = $("face-msg");
    button.disabled = true;
    try {
      await ctx.save(validateOwner(ctx));
      msg.textContent = ctx.t("face-capturing");
      const result = await ctx.net.json(`/api/setup/face?kind=${kind}`, { method: "POST" });
      ctx.config.face_views = result.views;
      msg.textContent = ctx.t("face-ok", { n: result.views.length });
      ctx.log(ctx.t("log-face", { kind: ctx.t(`face-${kind}`) }));
    } catch (error) {
      msg.textContent = error instanceof ctx.net.SetupError ? error.message : ctx.t(error.message);
      ctx.fail(error);
    } finally {
      button.disabled = false;
      paintFaces(ctx);
      ctx.refresh();
    }
  }

  const step4 = {
    render(ctx) {
      $("owner-first-input").value = ctx.config.owner_name || "";
      $("owner-last-input").value = ctx.config.owner_last || "";
      $("owner-first-input").oninput = ctx.refresh;
      $("face-msg").textContent = "";
      paintFaces(ctx);
    },
    collect: validateOwner,
    checks(ctx) {
      const { first } = ownerNames(ctx);
      const assistant = wakeWord(ctx.config.assistant_name);
      return [
        { key: "chk-owner", ok: FIRST_RE.test(first) },
        { key: "chk-owner-unique", ok: first ? first.toLowerCase() !== assistant : null },
        { key: "chk-face", ok: (ctx.config.face_views || []).length ? true : null, vars: { n: (ctx.config.face_views || []).length } }
      ];
    },
    analytics(ctx) {
      const { first, last } = ownerNames(ctx);
      return [["an-owner", `${first} ${last}`.trim()], ["an-face-views", `${(ctx.config.face_views || []).length} / 3`]];
    }
  };

  window.SetupStepDefs = Object.assign(window.SetupStepDefs || {}, { 1: step1, 2: step2, 3: step3, 4: step4 });
})();
