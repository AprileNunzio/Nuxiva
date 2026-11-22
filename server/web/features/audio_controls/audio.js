export function downsampleToPcm16Base64(floatChunks, inputSampleRate, targetRate = 16000) {
  let totalLen = 0;
  for (const c of floatChunks) totalLen += c.length;
  if (totalLen === 0) return null;

  const merged = new Float32Array(totalLen);
  let offset = 0;
  for (const c of floatChunks) {
    merged.set(c, offset);
    offset += c.length;
  }

  let resampled = merged;
  if (inputSampleRate && inputSampleRate !== targetRate) {
    const ratio = inputSampleRate / targetRate;
    const outLen = Math.max(1, Math.floor(merged.length / ratio));
    resampled = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const idx = Math.min(merged.length - 1, Math.floor(i * ratio));
      resampled[i] = merged[idx];
    }
  }

  // Keep at most the latest 2.5 seconds to stay lightweight
  const maxSamples = Math.floor(targetRate * 2.5);
  if (resampled.length > maxSamples) {
    resampled = resampled.subarray(resampled.length - maxSamples);
  }

  const pcm16 = new Int16Array(resampled.length);
  for (let i = 0; i < resampled.length; i++) {
    const s = Math.max(-1, Math.min(1, resampled[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  const bytes = new Uint8Array(pcm16.buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

export function cleanTextForBrowserSpeech(text) {
  if (!text) return "";
  return text
    .replace(/\[reaction:[a-zA-Z0-9_\-]+\]/gi, "")
    .replace(/\[[^\]]+\]/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export class AudioControlsManager {
  constructor(
    micBtnId = "btn-mic",
    speakerBtnId = "btn-speaker",
    inputTargetId = "query-input",
    options = {}
  ) {
    this.micBtn = document.getElementById(micBtnId);
    this.speakerBtn = document.getElementById(speakerBtnId);
    this.inputTarget = document.getElementById(inputTargetId);
    this.submitBtnId = options.submitBtnId || "submit-btn";
    this.onSpeechComplete = options.onSpeechComplete || null;
    this.isRecording = false;
    this.isSpeakerMuted = false;
    this.recognition = null;
    this.audioContext = null;
    this._mediaStream = null;
    this._processor = null;
    this._sourceNode = null;
    this._pcmChunks = [];
    this._captureSampleRate = 16000;
    this._lastCapturedPcm16B64 = null;
    this._currentAudio = null;
    this.init();
  }

  init() {
    this.setupSpeechRecognition();
    if (this.micBtn) {
      this.micBtn.addEventListener("click", () => this.toggleMicrophone());
    }
    if (this.speakerBtn) {
      this.speakerBtn.addEventListener("click", () => this.toggleSpeaker());
    }
  }

  async _startRawAudioCapture() {
    this._pcmChunks = [];
    this._lastCapturedPcm16B64 = null;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return;
    }
    try {
      this._mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: false },
      });
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioCtx();
      this._captureSampleRate = this.audioContext.sampleRate || 16000;
      this._sourceNode = this.audioContext.createMediaStreamSource(this._mediaStream);
      this._processor = this.audioContext.createScriptProcessor(4096, 1, 1);
      this._processor.onaudioprocess = (event) => {
        if (!this.isRecording) return;
        const channel = event.inputBuffer.getChannelData(0);
        this._pcmChunks.push(new Float32Array(channel));
        // Keep rolling buffer bounded (~3s)
        if (this._pcmChunks.length > 48) {
          this._pcmChunks.shift();
        }
      };
      this._sourceNode.connect(this._processor);
      this._processor.connect(this.audioContext.destination);
    } catch (_) {
      // Fallback gracefully to SpeechRecognition only if raw mic permission is unavailable
    }
  }

  _stopRawAudioCapture() {
    if (this._pcmChunks.length > 0) {
      this._lastCapturedPcm16B64 = downsampleToPcm16Base64(
        this._pcmChunks,
        this._captureSampleRate,
        16000
      );
    }
    this._pcmChunks = [];
    try {
      if (this._processor) {
        this._processor.disconnect();
        this._processor = null;
      }
      if (this._sourceNode) {
        this._sourceNode.disconnect();
        this._sourceNode = null;
      }
      if (this._mediaStream) {
        this._mediaStream.getTracks().forEach((track) => track.stop());
        this._mediaStream = null;
      }
      if (this.audioContext && this.audioContext.state !== "closed") {
        this.audioContext.close().catch(() => {});
        this.audioContext = null;
      }
    } catch (_) {}
  }

  consumeCapturedPcm16B64() {
    const payload = this._lastCapturedPcm16B64;
    this._lastCapturedPcm16B64 = null;
    return payload;
  }

  setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.lang = "it-IT";

      this.recognition.onstart = () => {
        this.isRecording = true;
        this.updateMicUI();
      };

      this.recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        if (this.inputTarget) {
          this.inputTarget.value = transcript;
        }
      };

      this.recognition.onend = () => {
        this.isRecording = false;
        this._stopRawAudioCapture();
        this.updateMicUI();
        const text = this.inputTarget ? this.inputTarget.value.trim() : "";
        if (text.length > 0) {
          if (typeof this.onSpeechComplete === "function") {
            this.onSpeechComplete(text, this.consumeCapturedPcm16B64());
          } else {
            const submitBtn = document.getElementById(this.submitBtnId);
            if (submitBtn) submitBtn.click();
          }
        }
      };

      this.recognition.onerror = () => {
        this.isRecording = false;
        this._stopRawAudioCapture();
        this.updateMicUI();
      };
    }
  }

  async toggleMicrophone() {
    if (!this.recognition) {
      const statusEl = document.getElementById("mic-status-label");
      if (statusEl) statusEl.textContent = "Web Speech non supportato";
      return;
    }

    if (this.isRecording) {
      this.recognition.stop();
    } else {
      await this._startRawAudioCapture();
      try {
        this.recognition.start();
      } catch (_) {
        this._stopRawAudioCapture();
      }
    }
  }

  updateMicUI() {
    const statusEl = document.getElementById("mic-status-label");
    if (!this.micBtn) return;
    if (this.isRecording) {
      this.micBtn.classList.add("recording");
      this.micBtn.innerHTML = `<span>&#128308;</span><span>In ascolto...</span>`;
      if (statusEl) statusEl.textContent = "Microfono attivo – Parla o sussurra ora";
    } else {
      this.micBtn.classList.remove("recording");
      this.micBtn.innerHTML = `<span>&#127908;</span><span>Voce</span>`;
      if (statusEl) statusEl.textContent = "In attesa di comando vocale";
    }
  }

  toggleSpeaker() {
    this.isSpeakerMuted = !this.isSpeakerMuted;
    const statusEl = document.getElementById("speaker-status-label");
    if (!this.speakerBtn) return;

    if (this.isSpeakerMuted) {
      this.speakerBtn.style.borderColor = "#64748b";
      this.speakerBtn.style.color = "#64748b";
      this.speakerBtn.innerHTML = `<span>&#128263;</span><span>Altoparlante Disattivo</span>`;
      if (statusEl) statusEl.textContent = "Sintesi vocale disattivata";
    } else {
      this.speakerBtn.style.borderColor = "#00f0ff";
      this.speakerBtn.style.color = "#00f0ff";
      this.speakerBtn.innerHTML = `<span>&#128266;</span><span>Altoparlante Attivo</span>`;
      if (statusEl) statusEl.textContent = "Audio vocale abilitato";
    }
  }

  async speak(text, modulation = null, userId = null) {
    if (this.isSpeakerMuted || !text) return;
    const mod = modulation || {};
    const whisperMode = Boolean(mod.whisper_mode);
    const volumeDb = typeof mod.volume_db === "number" ? mod.volume_db : 0.0;
    const speed = typeof mod.speed === "number" ? mod.speed : 1.0;
    const pitchShift = typeof mod.pitch_shift === "number" ? mod.pitch_shift : 0.0;

    // 1. Prova prima la sintesi server-side modulata (Piper + DSP whisper/volume)
    try {
      const res = await fetch("/api/v1/tts/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          speed: speed,
          user_id: userId,
          volume_db: volumeDb,
          pitch_shift: pitchShift,
          whisper_mode: whisperMode,
        }),
      });
      if (res.ok) {
        const wavBlob = await res.blob();
        if (wavBlob.size > 44) {
          if (this._currentAudio) {
            this._currentAudio.pause();
          }
          const url = URL.createObjectURL(wavBlob);
          const audio = new Audio(url);
          this._currentAudio = audio;
          audio.onended = () => URL.revokeObjectURL(url);
          await audio.play();
          return;
        }
      }
    } catch (_) {}

    // 2. Fallback naturale su Web SpeechSynthesis modulato dinamicamente
    const clean = cleanTextForBrowserSpeech(text);
    if (!clean || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "it-IT";
    utterance.rate = Math.max(0.65, Math.min(1.4, whisperMode ? Math.min(speed, 0.86) : speed));
    const linearGain = Math.pow(10, volumeDb / 20);
    utterance.volume = Math.max(0.18, Math.min(1.0, whisperMode ? Math.min(linearGain, 0.35) : linearGain));
    utterance.pitch = Math.max(0.6, Math.min(1.4, 1.0 + pitchShift * 0.05));
    window.speechSynthesis.speak(utterance);
  }
}
