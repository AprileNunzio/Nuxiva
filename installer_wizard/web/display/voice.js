(() => {
  const D = window.NuxivaDisplay, { $ } = D;

  const Voice = (() => {
    let ctx = null, gain = null, volume = 1, analyser = null, samples = null, spectrum = null, source = null, generation = 0, active = false, raf = 0;

    function ensure() {
      if (!ctx) {
        ctx = new (window.AudioContext || window.webkitAudioContext)();
        analyser = ctx.createAnalyser();
        analyser.fftSize = 1024;
        analyser.smoothingTimeConstant = 0.35;
        gain = ctx.createGain();
        gain.gain.value = volume;
        analyser.connect(gain);
        gain.connect(ctx.destination);
        samples = new Float32Array(analyser.fftSize);
        spectrum = new Uint8Array(analyser.frequencyBinCount);
      }
      if (ctx.state === "suspended") ctx.resume();
    }

    function sentences(text) {
      const parts = text.replace(/\s+/g, " ").match(/[^.!?;:]+[.!?;:]*/g) || [text];
      const out = [];
      for (const p of parts.map((x) => x.trim()).filter(Boolean)) {
        if (out.length > 1 && (out[out.length - 1].length < 40 || p.length < 12)) out[out.length - 1] += " " + p;
        else out.push(p);
      }
      if (out.length && out[0].length > 70) {
        const cut = out[0].indexOf(",", 20);
        if (cut > 0 && cut < out[0].length - 15) out.splice(0, 1, out[0].slice(0, cut + 1), out[0].slice(cut + 1).trim());
      }
      return out;
    }

    async function synth(text, lang, signal) {
      const r = await fetch("/api/assistant/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, lang }), signal });
      if (!r.ok) throw new Error(`TTS ${r.status}`);
      return ctx.decodeAudioData(await r.arrayBuffer());
    }

    function play(buffer, gen, onStart) {
      return new Promise((resolve) => {
        if (gen !== generation) return resolve();
        source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(analyser);
        source.onended = resolve;
        source.start();
        if (onStart) onStart("neural_scheduled");
      });
    }

    function level() {
      analyser.getFloatTimeDomainData(samples);
      let sum = 0;
      for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
      return Math.min(1.4, Math.sqrt(sum / samples.length) * 7);
    }

    function bands() {
      analyser.getByteFrequencyData(spectrum);
      const hz = ctx.sampleRate / analyser.fftSize;
      const sum = (a, b) => {
        let s = 0; const i0 = Math.floor(a / hz), i1 = Math.min(spectrum.length - 1, Math.ceil(b / hz));
        for (let i = i0; i <= i1; i++) s += spectrum[i];
        return s / Math.max(1, i1 - i0 + 1) / 255;
      };
      return { low: sum(250, 900), mid: sum(1000, 2600), high: sum(3500, 8000) };
    }

    function animate() {
      const l = level();
      if (D.avatar) { D.avatar.setSpeaking(true, l); if (D.avatar.setVoice) D.avatar.setVoice(bands()); }
      raf = requestAnimationFrame(animate);
    }

    function quiet() {
      active = false; cancelAnimationFrame(raf);
      if (D.avatar) { D.avatar.setSpeaking(false); if (D.avatar.face) D.avatar.face.realAudio = false; }
    }

    let pendingAudio = null;
    const scheduled = new Set();
    let nextTime = 0;

    function silence() {
      const live = Array.from(scheduled);
      scheduled.clear();
      nextTime = 0;
      if (!live.length || !ctx) return;
      const t = ctx.currentTime;
      gain.gain.cancelScheduledValues(t);
      gain.gain.setValueAtTime(gain.gain.value, t);
      gain.gain.linearRampToValueAtTime(0, t + 0.03);
      setTimeout(() => {
        live.forEach((node) => { try { node.stop(); } catch (e) {} });
        gain.gain.cancelScheduledValues(ctx.currentTime);
        gain.gain.setValueAtTime(volume, ctx.currentTime);
      }, 35);
    }

    function beginAudio() {
      stop();
      pendingAudio = new AbortController();
      return { gen: generation, signal: pendingAudio.signal };
    }

    async function speak(text, lang, onStart) {
      const { gen, signal } = beginAudio();
      ensure();
      const parts = sentences(text);
      active = true;
      if (D.avatar && D.avatar.face) D.avatar.face.realAudio = true;
      cancelAnimationFrame(raf); animate();
      try {
        for (let i = 0; i < parts.length; i++) {
          const buffer = await synth(parts[i], lang, signal);
          if (gen !== generation) return;
          await play(buffer, gen, i === 0 ? onStart : undefined);
        }
      } catch (err) {
        if (!signal.aborted) throw err;
      } finally {
        if (gen === generation) quiet();
      }
    }

    function stream(lang) {
      const { gen, signal } = beginAudio();
      ensure();
      active = true;
      if (D.avatar && D.avatar.face) D.avatar.face.realAudio = true;
      cancelAnimationFrame(raf); animate();
      let chain = Promise.resolve();
      return {
        add(text) {
          const part = (text || "").trim();
          if (!part || gen !== generation) return;
          chain = chain.then(async () => {
            if (signal.aborted) return;
            const buffer = await synth(part, lang, signal);
            if (gen === generation) await play(buffer, gen);
          }).catch((err) => { if (!signal.aborted) console.warn("Frase non sintetizzata:", err); });
        },
        async close() {
          try { await chain; } finally { if (gen === generation) quiet(); }
          return !signal.aborted;
        },
        stop() {
          if (gen !== generation) return false;
          stop();
          return true;
        },
      };
    }

    function stop() {
      generation++;
      if (pendingAudio) pendingAudio.abort();
      pendingAudio = null;
      try { source && source.stop(); } catch (e) {}
      silence();
      quiet();
    }

    let pcmPending = 0;

    function serverStream() {
      const { gen, signal } = beginAudio();
      pcmPending = 0;
      ensure();
      active = true;
      if (D.avatar && D.avatar.face) D.avatar.face.realAudio = true;
      cancelAnimationFrame(raf); animate();
      let chain = Promise.resolve();
      return {
        add(wav, onDone) {
          if (gen !== generation) return;
          chain = chain.then(async () => {
            if (signal.aborted) return;
            const buffer = await ctx.decodeAudioData(wav);
            if (gen === generation) await play(buffer, gen);
            if (onDone && gen === generation) onDone();
          }).catch((err) => { if (!signal.aborted) console.warn("Blocco audio non riprodotto:", err); });
        },
        addPcm(bytes, rate, onDone) {
          if (gen !== generation || !bytes || bytes.byteLength < 2 || bytes.byteLength % 2) return;
          const samples = new Int16Array(bytes.buffer, bytes.byteOffset, bytes.byteLength >> 1);
          const buffer = ctx.createBuffer(1, samples.length, rate);
          const channel = buffer.getChannelData(0);
          for (let i = 0; i < samples.length; i++) channel[i] = samples[i] / 32768;
          const node = ctx.createBufferSource();
          node.buffer = buffer;
          node.connect(analyser);
          const at = Math.max(nextTime, ctx.currentTime + 0.02);
          nextTime = at + buffer.duration;
          scheduled.add(node);
          pcmPending++;
          node.onended = () => {
            scheduled.delete(node);
            pcmPending--;
            if (onDone && gen === generation) onDone();
          };
          node.start(at);
        },
        async close() {
          try {
            await chain;
            while (pcmPending > 0 && gen === generation) await new Promise((r) => setTimeout(r, 20));
          } finally { if (gen === generation) quiet(); }
        },
      };
    }

    function setVolume(v) { volume = Math.max(0, Math.min(1, v)); if (gain) gain.gain.setTargetAtTime(volume, ctx.currentTime, 0.2); }

    return { speak, stream, serverStream, stop, setVolume, isSpeaking: () => active };
  })();

  function systemSpeak(text, lang, onStart) {
    if (!("speechSynthesis" in window)) return false;
    const it = speechSynthesis.getVoices().find((v) => v.lang && v.lang.toLowerCase().startsWith(lang || "it"));
    if (!it) return false;
    const u = new SpeechSynthesisUtterance(text.replace(/[*#_`]/g, ""));
    u.voice = it; u.lang = it.lang; u.rate = 1.0;
    u.onstart = () => {
      if (onStart) onStart("system_started");
      if (D.avatar) D.avatar.setSpeaking(true, 1);
    };
    u.onend = u.onerror = () => D.avatar && D.avatar.setSpeaking(false);
    speechSynthesis.cancel(); speechSynthesis.speak(u);
    return true;
  }

  function mouthOnly(text) {
    if (!D.avatar) return;
    D.avatar.setSpeaking(true, 1);
    setTimeout(() => D.avatar.setSpeaking(false), Math.min(12000, 60 * text.length));
  }

  D.speak = async (text, lang, onStart) => {
    D.Ear.speaking(true);
    if (D.avatar && D.avatar.direct) D.avatar.direct(text || "");
    try {
      if (!D.voiceOn || !text) { mouthOnly(text || ""); return; }
      try { await Voice.speak(text, lang, onStart); }
      catch (err) {
        console.warn("Voce neurale non disponibile:", err);
        if (!systemSpeak(text, lang, onStart)) mouthOnly(text);
      }
    } finally {
      setTimeout(() => { D.Ear.speaking(false); if (D.lastVoice) { D.lastVoice = false; D.Ear.followup(); } }, 350);
    }
  };

  D.speakStream = (lang) => {
    D.Ear.speaking(true);
    const server = D.DuplexVoice && D.DuplexVoice.connected();
    const live = D.voiceOn && !server ? Voice.stream(lang) : null;
    return {
      add(text) { if (live) live.add(text); },
      stop() {
        if (live && live.stop()) {
          D.lastVoice = false;
          D.Ear.speaking(false);
        }
      },
      async close(fullText) {
        try {
          if (live) return await live.close();
          else mouthOnly(fullText || "");
          return true;
        } finally {
          setTimeout(() => { D.Ear.speaking(false); if (D.lastVoice) { D.lastVoice = false; D.Ear.followup(); } }, 350);
        }
      },
    };
  };

  D.setVoiceVolume = (v) => Voice.setVolume(v);
  D.voiceServerStream = () => Voice.serverStream();
  D.voiceStop = () => Voice.stop();

  D.hush = () => {
    if (D.DuplexVoice) D.DuplexVoice.cut();
    D.lastVoice = false;
    Voice.stop();
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    D.Ear.speaking(false);
  };

  D.isSpeaking = () => Voice.isSpeaking() || ("speechSynthesis" in window && speechSynthesis.speaking);

  const VOICE_KEY = "nuxiva-voice-replies";

  D.setVoiceOn = (on) => {
    D.voiceOn = !!on;
    $("btn-voice").classList.toggle("on", D.voiceOn);
    $("btn-voice").setAttribute("aria-pressed", String(D.voiceOn));
    document.body.classList.toggle("voice-muted", !D.voiceOn);
    if ($("voice-replies")) $("voice-replies").checked = D.voiceOn;
    try { localStorage.setItem(VOICE_KEY, D.voiceOn ? "1" : "0"); } catch (_) {}
    if (!D.voiceOn) { Voice.stop(); if ("speechSynthesis" in window) speechSynthesis.cancel(); }
  };

  D.startVoiceToggle = () => {
    let stored = null;
    try { stored = localStorage.getItem(VOICE_KEY); } catch (_) {}
    D.setVoiceOn(stored !== "0");
    $("btn-voice").addEventListener("click", () => {
      if (D.isFamilyNear && !D.isFamilyNear()) return;
      D.setVoiceOn(!D.voiceOn);
    });
  };
})();
