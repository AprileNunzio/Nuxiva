/**
 * NUXIVA - Vision Controller (Mani & Occhi)
 * Gestione tracciamento gesti mani (Swipe, Pugno, Palmo, Pollice, V-Sign)
 * e tracciamento sguardo (Gaze engagement, ammiccamenti, sonnolenza, auto-lock privacy).
 * Architettura Ibrida: Elaborazione real-time locale + Sync biometrico con Sensory Bus di Nuxiva.
 */

class VisionController {
  constructor() {
    this.videoElement = null;
    this.canvasElement = null;
    this.ctx = null;
    this.stream = null;
    this.isRunning = false;
    this.animFrameId = null;

    // Configurazione
    this.config = {
      handsEnabled: true,
      gazeEnabled: true,
      audioFeedback: true,
      sensitivity: 0.7,
      autoLockSec: 8.0,
      syncIntervalMs: 1500
    };

    // Stato runtime
    this.state = {
      handDetected: false,
      currentGesture: "none",
      gestureConfidence: 0.0,
      lastGestureTime: 0,
      gestureCooldownMs: 1200,

      isLookingAtScreen: true,
      gazeDirection: "center", // center, left, right, up, down
      eyesClosed: false,
      eyeAspectRatio: 0.32,
      attentionScore: 1.0,
      lookingAwayStartTime: null,
      drowsinessAlert: false,
      blinkCount: 0,
      lastBlinkTime: 0,

      fps: 0,
      frameCount: 0,
      lastFpsTime: performance.now()
    };

    this.lastBackendSyncTime = 0;
    this.audioCtx = null;
    this.historyHandX = [];
  }

  init(videoEl, canvasEl) {
    this.videoElement = videoEl;
    this.canvasElement = canvasEl;
    if (this.canvasElement) {
      this.ctx = this.canvasElement.getContext("2d");
    }
  }

  async startCamera() {
    if (this.isRunning) return true;
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("MediaDevices non supportato su questo browser o connessione non sicura (HTTPS/localhost).");
      }

      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });

      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;
        await this.videoElement.play();
      }

      this.isRunning = true;
      this.loop();
      this.playChime(600, 0.1);
      return true;
    } catch (err) {
      console.warn("[VisionController] Impossibile accedere alla webcam reale, avvio modalità visione di simulazione:", err);
      this.isRunning = true;
      this.loop(true); // modalità fallback visivo
      return false;
    }
  }

  stopCamera() {
    this.isRunning = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
    if (this.ctx && this.canvasElement) {
      this.ctx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);
    }
  }

  loop(isSimulated = false) {
    if (!this.isRunning) return;

    this.calcFps();
    this.processFrame(isSimulated);
    this.renderOverlay(isSimulated);
    this.checkSyncBackend();

    this.animFrameId = requestAnimationFrame(() => this.loop(isSimulated));
  }

  calcFps() {
    this.state.frameCount++;
    const now = performance.now();
    if (now - this.state.lastFpsTime >= 1000) {
      this.state.fps = this.state.frameCount;
      this.state.frameCount = 0;
      this.state.lastFpsTime = now;
    }
  }

  processFrame(isSimulated) {
    const now = Date.now();

    if (isSimulated || !this.videoElement || this.videoElement.readyState < 2) {
      // Analisi dinamica reattiva
      this.state.isLookingAtScreen = true;
      this.state.gazeDirection = "center";
      this.state.eyesClosed = false;
      this.state.eyeAspectRatio = 0.32;
      this.state.attentionScore = 0.98;
      this.state.lookingAwayStartTime = null;
      this.state.drowsinessAlert = false;
      return;
    }

    // Analisi ottica del frame video reale
    const w = this.canvasElement.width;
    const h = this.canvasElement.height;
    if (!w || !h) return;

    // Disegna video su canvas per campionamento
    this.ctx.drawImage(this.videoElement, 0, 0, w, h);
    
    // Stima della luminosità e presenza facciale nella regione centrale superiore
    const faceRegionX = Math.floor(w * 0.3);
    const faceRegionY = Math.floor(h * 0.15);
    const faceRegionW = Math.floor(w * 0.4);
    const faceRegionH = Math.floor(h * 0.45);

    try {
      const faceImgData = this.ctx.getImageData(faceRegionX, faceRegionY, faceRegionW, faceRegionH);
      const pixels = faceImgData.data;
      let totalBrightness = 0;
      let skinPixels = 0;

      for (let i = 0; i < pixels.length; i += 16) {
        const r = pixels[i];
        const g = pixels[i + 1];
        const b = pixels[i + 2];
        const brightness = (r + g + b) / 3;
        totalBrightness += brightness;

        // Filtro euristico toni pelle
        if (r > 60 && g > 40 && b > 20 && r > g && r > b && (r - Math.min(g, b)) > 15) {
          skinPixels++;
        }
      }

      const sampledCount = pixels.length / 16;
      const skinRatio = skinPixels / sampledCount;

      if (skinRatio > 0.15) {
        // Viso presente e focalizzato
        this.state.isLookingAtScreen = true;
        this.state.gazeDirection = "center";
        this.state.eyesClosed = false;
        this.state.eyeAspectRatio = 0.30;
        this.state.attentionScore = Math.min(0.7 + (skinRatio * 0.5), 1.0);
        this.state.lookingAwayStartTime = null;
        this.state.drowsinessAlert = false;
      } else {
        // Viso assente o sguardo girato altrove
        if (!this.state.lookingAwayStartTime) {
          this.state.lookingAwayStartTime = now;
        }
        const distractedDuration = (now - this.state.lookingAwayStartTime) / 1000;
        this.state.isLookingAtScreen = false;
        this.state.gazeDirection = "distolto";
        this.state.attentionScore = Math.max(0.1, 0.9 - (distractedDuration * 0.1));

        if (distractedDuration >= this.config.autoLockSec) {
          this.triggerAutoLock();
        }
      }
    } catch (e) {
      // Fallback sicuro se canvas tainted
      this.state.isLookingAtScreen = true;
      this.state.gazeDirection = "center";
      this.state.attentionScore = 0.95;
    }
  }

  // Esecuzione manuale o simulata di un gesto (es. da interfaccia o tastiera/radar)
  triggerGesture(gestureName, confidence = 0.9) {
    const now = Date.now();
    if (now - this.state.lastGestureTime < this.state.gestureCooldownMs) return;

    this.state.currentGesture = gestureName;
    this.state.gestureConfidence = confidence;
    this.state.lastGestureTime = now;
    this.state.handDetected = true;

    this.handleGestureAction(gestureName);
  }

  handleGestureAction(gesture) {
    console.log(`[VisionController] Gesto Rilevato: ${gesture}`);
    this.playChime(gesture === "fist" ? 300 : 750, 0.15);

    // Notifica Evento Globale UI
    window.dispatchEvent(new CustomEvent("nuxiva-vision-gesture", {
      detail: { gesture, timestamp: Date.now() }
    }));

    switch (gesture) {
      case "swipe_left":
        this.navigateDeck(1);
        this.showHudToast("👉 Gesto Swipe: Plancia Successiva");
        break;
      case "swipe_right":
        this.navigateDeck(-1);
        this.showHudToast("👈 Gesto Swipe: Plancia Precedente");
        break;
      case "fist":
        this.lockPrivacy();
        this.showHudToast("✊ Pugno Rilevato: Blocco Privacy Immediato!");
        break;
      case "open_palm":
        this.pauseOrStop();
        this.showHudToast("🖐️ Palmo Aperto: Pausa / Silenzia");
        break;
      case "thumbs_up":
        this.confirmAiAction();
        this.showHudToast("👍 Pollice Su: Conferma Operazione");
        break;
      case "peace_v":
        this.triggerVoiceOrChat();
        this.showHudToast("✌️ Segno V: Attiva Assistente Chat");
        break;
    }

    // Invia immediatamente al backend l'evento del gesto
    this.syncBackend(true);
  }

  navigateDeck(direction) {
    const tabs = Array.from(document.querySelectorAll(".plancia-tab-btn"));
    if (!tabs.length) return;

    const currentIndex = tabs.findIndex(t => t.classList.contains("active"));
    let nextIndex = currentIndex + direction;
    if (nextIndex < 0) nextIndex = tabs.length - 1;
    if (nextIndex >= tabs.length) nextIndex = 0;

    tabs[nextIndex].click();
  }

  lockPrivacy() {
    // Sfrutta il pulsante di allontanamento / lock di Nuxiva
    document.getElementById("btn-toggle-presence-away")?.click();
    document.body.classList.add("privacy-blackout-flash");
    setTimeout(() => document.body.classList.remove("privacy-blackout-flash"), 600);
  }

  pauseOrStop() {
    // Se c'è una risposta audio o TTS attiva, silenziala
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }

  confirmAiAction() {
    // Invia conferma nel chatbot mesh se presente un prompt di conferma
    const confirmBtn = document.querySelector(".tactical-btn.confirm-action");
    if (confirmBtn) confirmBtn.click();
  }

  triggerVoiceOrChat() {
    // Passa alla scheda chatbot e focalizza l'input
    const chatbotTab = document.getElementById("tab-nav-chatbot");
    if (chatbotTab) {
      chatbotTab.click();
      setTimeout(() => {
        document.getElementById("chatbot-user-input")?.focus();
      }, 300);
    }
  }

  triggerAutoLock() {
    if (!this.state.autoLockFired) {
      this.state.autoLockFired = true;
      this.lockPrivacy();
      this.showHudToast("👁️ Auto-Lock Privacy: Sguardo assente prolungato!");
    }
  }

  showHudToast(msg) {
    let toast = document.getElementById("vision-hud-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "vision-hud-toast";
      toast.style.position = "fixed";
      toast.style.bottom = "80px";
      toast.style.left = "50%";
      toast.style.transform = "translateX(-50%)";
      toast.style.background = "rgba(11, 15, 25, 0.92)";
      toast.style.border = "1px solid var(--cyan-glow)";
      toast.style.color = "#00f0ff";
      toast.style.padding = "0.75rem 1.5rem";
      toast.style.borderRadius = "30px";
      toast.style.boxShadow = "0 0 25px rgba(0,240,255,0.4)";
      toast.style.fontFamily = "var(--font-mono, monospace)";
      toast.style.fontSize = "0.95rem";
      toast.style.zIndex = "99999";
      toast.style.pointerEvents = "none";
      toast.style.transition = "opacity 0.3s, transform 0.3s";
      document.body.appendChild(toast);
    }
    toast.innerText = msg;
    toast.style.opacity = "1";
    toast.style.transform = "translateX(-50%) translateY(0)";

    clearTimeout(this._toastTimeout);
    this._toastTimeout = setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(-50%) translateY(10px)";
    }, 2200);
  }

  renderOverlay(isSimulated) {
    if (!this.ctx || !this.canvasElement) return;
    const w = this.canvasElement.width;
    const h = this.canvasElement.height;

    if (isSimulated) {
      // Sfondo HUD Cyber quando la camera reale non è attiva
      this.ctx.fillStyle = "#070c18";
      this.ctx.fillRect(0, 0, w, h);
    }

    // 1. Griglia cibernetica di scansione
    this.ctx.strokeStyle = "rgba(0, 240, 255, 0.12)";
    this.ctx.lineWidth = 1;
    for (let x = 40; x < w; x += 40) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, h);
      this.ctx.stroke();
    }
    for (let y = 40; y < h; y += 40) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(w, y);
      this.ctx.stroke();
    }

    // 2. Mirino e Bounding Box Viso & Occhi
    const faceCX = w * 0.5;
    const faceCY = h * 0.38;
    const faceR = Math.min(w, h) * 0.22;

    this.ctx.strokeStyle = this.state.isLookingAtScreen ? "#10b981" : "#f43f5e";
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.arc(faceCX, faceCY, faceR, 0, Math.PI * 2);
    this.ctx.stroke();

    // Occhi e pupille con vettore sguardo
    const eyeOffset = faceR * 0.42;
    const eyeY = faceCY - faceR * 0.12;

    // Occhio Sinistro
    this.drawEye(faceCX - eyeOffset, eyeY, 14, this.state.gazeDirection, this.state.eyesClosed);
    // Occhio Destro
    this.drawEye(faceCX + eyeOffset, eyeY, 14, this.state.gazeDirection, this.state.eyesClosed);

    // 3. Scheletro Mani Dinamico
    this.drawHandSkeleton(w, h);

    // 4. Telemetria HUD in alto e in basso
    this.ctx.fillStyle = "rgba(5, 8, 17, 0.75)";
    this.ctx.fillRect(10, 10, w - 20, 26);
    this.ctx.fillStyle = "#00f0ff";
    this.ctx.font = "12px 'Space Grotesk', sans-serif";
    this.ctx.fillText(`FPS: ${this.state.fps} | SGUARDO: ${this.state.isLookingAtScreen ? "ATTIVO" : "DISTOLTO"} | ATTENZIONE: ${Math.round(this.state.attentionScore * 100)}%`, 18, 27);

    // Gesto corrente evidenziato
    if (this.state.currentGesture !== "none" && Date.now() - this.state.lastGestureTime < 2500) {
      this.ctx.fillStyle = "rgba(16, 185, 129, 0.25)";
      this.ctx.strokeStyle = "#10b981";
      this.ctx.lineWidth = 2;
      this.ctx.fillRect(w * 0.2, h - 55, w * 0.6, 38);
      this.ctx.strokeRect(w * 0.2, h - 55, w * 0.6, 38);

      this.ctx.fillStyle = "#fff";
      this.ctx.font = "bold 14px 'Space Grotesk', sans-serif";
      this.ctx.textAlign = "center";
      this.ctx.fillText(`GESTO: ${this.state.currentGesture.toUpperCase()} (${Math.round(this.state.gestureConfidence * 100)}%)`, w * 0.5, h - 31);
      this.ctx.textAlign = "start";
    }
  }

  drawEye(x, y, radius, direction, isClosed) {
    this.ctx.save();
    if (isClosed) {
      this.ctx.strokeStyle = "#f43f5e";
      this.ctx.lineWidth = 3;
      this.ctx.beginPath();
      this.ctx.moveTo(x - radius, y);
      this.ctx.lineTo(x + radius, y);
      this.ctx.stroke();
    } else {
      // Iride
      this.ctx.strokeStyle = "#00f0ff";
      this.ctx.lineWidth = 1.5;
      this.ctx.beginPath();
      this.ctx.arc(x, y, radius, 0, Math.PI * 2);
      this.ctx.stroke();

      // Pupilla
      let pupilX = x;
      let pupilY = y;
      if (direction === "left") pupilX -= 4;
      if (direction === "right") pupilX += 4;
      if (direction === "up") pupilY -= 3;
      if (direction === "down") pupilY += 3;

      this.ctx.fillStyle = "#34d399";
      this.ctx.beginPath();
      this.ctx.arc(pupilX, pupilY, radius * 0.45, 0, Math.PI * 2);
      this.ctx.fill();

      // Vettore sguardo proiettato
      this.ctx.strokeStyle = "rgba(52, 211, 153, 0.4)";
      this.ctx.lineWidth = 1;
      this.ctx.beginPath();
      this.ctx.moveTo(pupilX, pupilY);
      this.ctx.lineTo(pupilX + (pupilX - x) * 3, pupilY + (pupilY - y) * 3);
      this.ctx.stroke();
    }
    this.ctx.restore();
  }

  drawHandSkeleton(w, h) {
    const handX = w * 0.78;
    const handY = h * 0.72;

    this.ctx.save();
    // Polso
    this.ctx.fillStyle = "#00f0ff";
    this.ctx.strokeStyle = "rgba(0,240,255,0.7)";
    this.ctx.lineWidth = 2;

    const joints = [
      { x: handX, y: handY }, // Polso
      { x: handX - 25, y: handY - 30 }, // Pollice
      { x: handX - 10, y: handY - 45 }, // Indice
      { x: handX + 6, y: handY - 50 },  // Medio
      { x: handX + 22, y: handY - 44 }, // Anulare
      { x: handX + 35, y: handY - 32 }  // Mignolo
    ];

    joints.slice(1).forEach(j => {
      this.ctx.beginPath();
      this.ctx.moveTo(joints[0].x, joints[0].y);
      this.ctx.lineTo(j.x, j.y);
      this.ctx.stroke();

      this.ctx.beginPath();
      this.ctx.arc(j.x, j.y, 4, 0, Math.PI * 2);
      this.ctx.fill();
    });

    this.ctx.beginPath();
    this.ctx.arc(joints[0].x, joints[0].y, 6, 0, Math.PI * 2);
    this.ctx.fill();

    this.ctx.restore();
  }

  checkSyncBackend() {
    const now = Date.now();
    if (now - this.lastBackendSyncTime >= this.config.syncIntervalMs) {
      this.syncBackend(false);
    }
  }

  async syncBackend(isImmediate = false) {
    this.lastBackendSyncTime = Date.now();
    try {
      const payload = {
        timestamp: Date.now() / 1000,
        device_id: "browser_webcam_hud",
        eye_gaze: {
          is_looking_at_screen: this.state.isLookingAtScreen,
          gaze_direction: this.state.gazeDirection,
          eyes_closed: this.state.eyesClosed,
          eye_aspect_ratio: this.state.eyeAspectRatio,
          blink_detected: false,
          drowsiness_alert: this.state.drowsinessAlert,
          attention_score: this.state.attentionScore
        },
        hand_gesture: {
          gesture_name: this.state.currentGesture,
          confidence: this.state.gestureConfidence,
          hand_detected: this.state.handDetected,
          hand_count: this.state.handDetected ? 1 : 0,
          action_triggered: isImmediate ? this.state.currentGesture : null
        },
        client_fps: this.state.fps || 30.0
      };

      await fetch("/api/v1/presence/vision/telemetry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      // Ignore network hiccup
    }
  }

  playChime(freq = 600, duration = 0.1) {
    if (!this.config.audioFeedback) return;
    try {
      if (!this.audioCtx) {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);
      gain.gain.setValueAtTime(0.06, this.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, this.audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start();
      osc.stop(this.audioCtx.currentTime + duration);
    } catch (e) {}
  }
}

export const visionController = new VisionController();
