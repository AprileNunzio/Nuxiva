(() => {
  "use strict";

  const TARGET_RATE = 16000;
  let shared = null;

  function available() {
    return Boolean(window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.AudioContext);
  }

  async function open() {
    if (shared) return shared;
    if (!available()) throw new Error("mic-unavailable");
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 }
    });
    const context = new AudioContext();
    if (context.state === "suspended") await context.resume();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.2;
    source.connect(analyser);
    const track = stream.getAudioTracks()[0];
    shared = { stream, context, source, analyser, label: track ? track.label : "", rate: context.sampleRate };
    return shared;
  }

  function close() {
    if (!shared) return;
    shared.stream.getTracks().forEach((track) => track.stop());
    shared.context.close().catch((error) => console.warn("setup audio: chiusura contesto", error));
    shared = null;
  }

  function rmsDb(analyser, buffer) {
    analyser.getFloatTimeDomainData(buffer);
    let sum = 0;
    for (let i = 0; i < buffer.length; i++) sum += buffer[i] * buffer[i];
    const rms = Math.sqrt(sum / buffer.length);
    return rms > 0 ? 20 * Math.log10(rms) : -140;
  }

  function percentile(values, p) {
    const sorted = [...values].sort((a, b) => a - b);
    return sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor(sorted.length * p)))];
  }

  function sampleLevels(mic, ms, onLevel) {
    const buffer = new Float32Array(mic.analyser.fftSize);
    const levels = [];
    return new Promise((resolve) => {
      const end = performance.now() + ms;
      const tick = () => {
        const db = rmsDb(mic.analyser, buffer);
        levels.push(db);
        if (onLevel) onLevel(db);
        if (performance.now() < end) setTimeout(tick, 40);
        else resolve({ low: percentile(levels, 0.5), high: percentile(levels, 0.9), count: levels.length });
      };
      tick();
    });
  }

  function downsample(chunks, inputRate) {
    const length = chunks.reduce((n, c) => n + c.length, 0);
    const input = new Float32Array(length);
    let offset = 0;
    chunks.forEach((c) => { input.set(c, offset); offset += c.length; });
    const ratio = inputRate / TARGET_RATE;
    const out = new Int16Array(Math.floor(length / ratio));
    for (let i = 0; i < out.length; i++) {
      const start = Math.floor(i * ratio);
      const stop = Math.min(length, Math.floor((i + 1) * ratio));
      let sum = 0;
      for (let j = start; j < stop; j++) sum += input[j];
      const value = Math.max(-1, Math.min(1, sum / Math.max(1, stop - start)));
      out[i] = value < 0 ? value * 0x8000 : value * 0x7fff;
    }
    return out;
  }

  function wav(samples) {
    const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
    const text = (pos, value) => [...value].forEach((ch, i) => view.setUint8(pos + i, ch.charCodeAt(0)));
    text(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    text(8, "WAVE");
    text(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, TARGET_RATE, true);
    view.setUint32(28, TARGET_RATE * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    text(36, "data");
    view.setUint32(40, samples.length * 2, true);
    samples.forEach((s, i) => view.setInt16(44 + i * 2, s, true));
    return new Blob([view.buffer], { type: "audio/wav" });
  }

  function record(mic, ms) {
    const processor = mic.context.createScriptProcessor(4096, 1, 1);
    const silent = mic.context.createGain();
    silent.gain.value = 0;
    const chunks = [];
    processor.onaudioprocess = (event) => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    mic.source.connect(processor);
    processor.connect(silent);
    silent.connect(mic.context.destination);
    return new Promise((resolve) => {
      setTimeout(() => {
        mic.source.disconnect(processor);
        processor.disconnect();
        silent.disconnect();
        resolve(wav(downsample(chunks, mic.rate)));
      }, ms);
    });
  }

  window.SetupAudio = Object.freeze({ available, open, close, sampleLevels, record });
})();
