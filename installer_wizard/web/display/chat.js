(() => {
  const D = window.NuxivaDisplay, { $ } = D;

  function thinking(on) {
    const { avatar } = D;
    if (!avatar) return;
    avatar.setTint(on ? "#b36bff" : (D.currentTint ? D.currentTint() : (D.tint || "#29e0ff")));
    if (avatar.face) avatar.face.thinking = on;
  }

  D.wakeDesk = () => {
    if (window.NuxivaTouch) { window.NuxivaTouch.hideMenu(); window.NuxivaTouch.hideSheet(); }
    fetch("/api/desk/wake", { method: "POST" }).catch((err) => console.warn("Chiusura dei widget automatici non riuscita:", err));
  };

  D.greetWake = async () => {
    if (D.busy) return;
    D.busy = true; D.lastInteraction = Date.now();
    try {
      const d = await fetch("/api/assistant/wake", { method: "POST", headers: { "Content-Type": "application/json", "X-Nuxiva-Client": D.clientId || "" }, body: JSON.stringify({ client_id: D.clientId }) }).then((r) => r.json());
      parseActions(d);
      if (D.mode !== "face") D.setMode("face");
      D.Mood.joy();
      $("you").textContent = "";
      D.typeInto($("say"), d.reply);
      D.lastVoice = true;
      D.speak(d.reply);
    } catch (err) {
      D.Ear.followup(8);
    } finally {
      D.busy = false; D.lastInteraction = Date.now();
    }
  };

  function enrollUi(d) {
    if (!d.ui || d.ui.mode !== "enroll") return false;
    D.setMode("face");
    D.typeInto($("say"), d.reply);
    D.lastVoice = false;
    D.speak(d.reply);
    D.Enroll.start(d.ui);
    return true;
  }

  function parseActions(d) {
    if (!d || !d.reply) return;
    const tags = [];
    d.reply = d.reply.replace(/\[AZIONE:\s*([^\]]+)\]/gi, (match, action) => {
      tags.push(action.trim());
      return "";
    }).trim();
    if (tags.length && D.avatar && D.avatar.express) tags.forEach((tag) => D.avatar.express(tag.toLowerCase(), 2.2));
  }

  const ACTION_TAG = /\[AZIONE:[^\]]*\]?/gi;
  const SENTENCE = /^([\s\S]*?(?:[.!?…:;](?=\s)|\n))(\s*)/;

  function cleanLive(text) {
    return text.replace(ACTION_TAG, "").replace(/[ \t]+/g, " ").replace(/\n{2,}/g, "\n").trimStart();
  }

  async function askStream(text, lang, heard) {
    const r = await fetch("/api/assistant/chat/stream", { method: "POST", headers: { "Content-Type": "application/json", "X-Nuxiva-Client": D.clientId || "" },
      body: JSON.stringify({ text, lang, client_id: D.clientId, ...heard }) });
    if (!r.ok || !r.body) return null;
    const reader = r.body.getReader(), decoder = new TextDecoder();
    let buffer = "", said = "", cut = 0, code = false, voice = null, final = null;
    const speakReady = () => {
      if (code) return;
      let pending = said.slice(cut);
      const fence = pending.indexOf("```");
      if (fence >= 0) { pending = pending.slice(0, fence); code = true; }
      let m;
      while (pending && (m = SENTENCE.exec(pending)) && m[0].length) {
        voice.add(m[1]);
        cut += m[0].length;
        pending = pending.slice(m[0].length);
      }
      if (code && pending.trim()) { voice.add(pending); cut += pending.length; }
    };
    while (!final) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let split;
      while ((split = buffer.indexOf("\n\n")) >= 0) {
        const line = buffer.slice(0, split).trim();
        buffer = buffer.slice(split + 2);
        if (!line.startsWith("data: ")) continue;
        const ev = JSON.parse(line.slice(6));
        if (ev.type === "brain_route") {
          window.dispatchEvent(new CustomEvent("nuxiva-brain-route", { detail: ev.route }));
        } else if (ev.type === "token") {
          if (!voice) { voice = D.speakStream(lang); D.setMode("face"); }
          said = cleanLive(said + ev.t);
          $("say").textContent = said;
          speakReady();
        } else if (ev.type === "error") {
          throw new Error(ev.detail || PageText.t("web/display", "chat_error"));
        } else if (ev.type === "done") {
          final = ev;
        }
      }
    }
    if (!final) throw new Error(PageText.t("web/display", "chat_interrupted"));
    if (voice) {
      parseActions(final);
      const reply = final.reply || "", flat = cleanLive(reply), prefix = said.slice(0, cut);
      if (code || prefix.startsWith(flat)) {
        voice.close(reply);
      } else if (flat.startsWith(prefix)) {
        voice.add(flat.slice(cut));
        voice.close(reply);
      } else if (!cut) {
        voice.add(flat);
        voice.close(reply);
      } else {
        await voice.close(reply);
        D.speak(reply, final.lang);
      }
    }
    return { data: final, spoken: Boolean(voice) };
  }

  function show(text, d, spoken = false) {
    parseActions(d);
    $("you").textContent = `« ${text} »`;
    if (enrollUi(d)) return;
    const ui = d.ui || { mode: "face" };
    if (ui.mode === "focus") { D.renderStage(ui); D.typeInto($("focus-say"), d.reply); }
    D.personalUi = ui.mode === "focus" && ui.personal ? { at: Date.now() } : null;
    D.setPresence(ui.presence || "normal");
    D.setMode(ui.mode);
    if (ui.camera && D.setCamera) D.setCamera(ui.camera === "on");
    if (ui.agency && D.agency) D.agency.sync(ui.agency);
    if (spoken) $("say").textContent = d.reply;
    else { D.typeInto($("say"), d.reply); D.speak(d.reply, d.lang); }
    if (ui.mode === "face" || ui.mode === "focus") setTimeout(() => D.refreshBrain(true), 1500);
  }

  async function predict(text) {
    const pred = await fetch(`/api/assistant/predict?q=${encodeURIComponent(text)}`).then((r) => r.json()).catch(() => null);
    if (pred && pred.skeleton && pred.skeleton.mode === "focus") { D.renderSkeleton(pred.skeleton); D.setMode("focus"); }
    else if (pred && pred.intent === "brain") D.setMode("brain");
  }

  D.ask = async (text, lang, heard = {}) => {
    D.busy = true; D.lastInteraction = Date.now();
    thinking(true);
    const payload = { ...heard };
    if (!heard.followup) {
      $("you").textContent = `« ${text} »`;
      $("say").textContent = "…";
    }
    try {
      if (!heard.followup) await predict(text);
      const streamed = await askStream(text, lang, payload);
      if (streamed) {
        if (streamed.data.ignored) { D.lastVoice = false; D.Ear.followup(12); return; }
        show(text, streamed.data, streamed.spoken);
        return;
      }
      const r = await fetch("/api/assistant/chat", { method: "POST", headers: { "Content-Type": "application/json", "X-Nuxiva-Client": D.clientId || "" },
        body: JSON.stringify({ text, lang, client_id: D.clientId, ...payload }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Errore");
      if (d.ignored) { D.lastVoice = false; D.Ear.followup(12); return; }
      show(text, d);
    } catch (err) {
      D.setMode("face");
      $("say").textContent = `⚠ ${err.message}`;
      if (D.avatar && D.avatar.express) D.avatar.express("sad", 2.6);
    } finally {
      D.busy = false; D.lastInteraction = Date.now();
      thinking(false);
    }
  };

  D.startChat = () => {
    const inputEl = $("in");
    const dockEl = document.querySelector(".dock");
    if (inputEl && dockEl) {
      inputEl.addEventListener("focus", () => dockEl.classList.add("expanded"));
      inputEl.addEventListener("blur", () => {
        if (!inputEl.value.trim()) dockEl.classList.remove("expanded");
      });
    }
    const send = () => {
      if (D.isFamilyNear && !D.isFamilyNear()) return;
      const text = $("in").value.trim();
      if (!text || D.busy) return;
      $("in").value = "";
      $("btn-send").disabled = true;
      D.ask(text);
    };
    $("in").addEventListener("input", () => {
      D.pingActivity(false);
      $("btn-send").disabled = !$("in").value.trim() || (D.isFamilyNear && !D.isFamilyNear());
    });
    $("in").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
    const editable = (el) => !!el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));
    addEventListener("keydown", (e) => {
      if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.key.length !== 1 || editable(document.activeElement)) return;
      if (D.isFamilyNear && !D.isFamilyNear()) return;
      if (D.mode !== "face" || document.body.matches(".desk-full, .desk-whiteboard, .desk-immersive")) return;
      if (dockEl.offsetParent === null || inputEl.disabled) return;
      dockEl.classList.add("expanded");
      inputEl.focus({ preventScroll: true });
    });
    dockEl.querySelector(".dock-bar").addEventListener("pointerdown", (e) => {
      if (e.target.closest("button") || document.activeElement === inputEl) return;
      dockEl.classList.add("expanded");
      requestAnimationFrame(() => inputEl.focus({ preventScroll: true }));
    });
    $("btn-send").addEventListener("click", send);
    const dock = document.querySelector(".dock");
    const setTools = (open) => {
      dock.classList.toggle("tools-open", open);
      $("btn-tools").setAttribute("aria-expanded", String(open));
    };
    $("btn-tools").addEventListener("click", () => {
      if (D.isFamilyNear && !D.isFamilyNear()) return;
      setTools(!dock.classList.contains("tools-open"));
    });
    document.addEventListener("pointerdown", (e) => {
      if (dock.classList.contains("tools-open") && !dock.contains(e.target)) setTools(false);
    }, { capture: true, passive: true });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") setTools(false); });
    $("dock-tools").addEventListener("click", (e) => { if (e.target.closest("button")) setTools(false); });
    if (!D.local) {
      fetch("/api/auth/me", { credentials: "include" }).then((r) => {
        if (!r.ok) PageText.bind($("note"), "chat_view_only", { assistant: D.assistantName() });
      }).catch((err) => console.warn("Sessione non verificata", err));
    }
  };
})();
