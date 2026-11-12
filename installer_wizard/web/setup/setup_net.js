(() => {
  "use strict";

  const CODE_KEY = "nuxiva_setup_code";
  const listeners = new Set();
  let waitingForCode = null;

  class SetupError extends Error {
    constructor(status, detail) {
      super(detail || `HTTP ${status}`);
      this.status = status;
    }
  }

  function storedCode() {
    try {
      return sessionStorage.getItem(CODE_KEY) || "";
    } catch (error) {
      console.warn("setup: codice non leggibile dalla sessione", error);
      return "";
    }
  }

  function storeCode(code) {
    try {
      sessionStorage.setItem(CODE_KEY, code);
    } catch (error) {
      console.warn("setup: codice non salvato nella sessione", error);
    }
  }

  function notify(state) {
    listeners.forEach((fn) => fn(state));
  }

  async function detail(response) {
    try {
      const body = await response.json();
      return typeof body.detail === "string" ? body.detail.slice(0, 300) : "";
    } catch (error) {
      return "";
    }
  }

  function askCode(message) {
    if (waitingForCode) return waitingForCode;
    const overlay = document.getElementById("code-overlay");
    const form = document.getElementById("code-form");
    const input = document.getElementById("code-input");
    const error = document.getElementById("code-error");
    error.hidden = !message;
    error.textContent = message || "";
    overlay.hidden = false;
    input.value = "";
    input.focus();
    waitingForCode = new Promise((resolve) => {
      form.onsubmit = (event) => {
        event.preventDefault();
        const code = input.value.trim();
        if (!/^\d{6}$/.test(code)) return;
        storeCode(code);
        overlay.hidden = true;
        waitingForCode = null;
        resolve(code);
      };
    });
    return waitingForCode;
  }

  async function request(path, options = {}, retry = true) {
    const headers = { "X-Nuxiva-Request": "1", ...(options.headers || {}) };
    if (options.json !== undefined) headers["Content-Type"] = "application/json";
    const code = storedCode();
    if (code) headers["X-Nuxiva-Setup-Code"] = code;
    const started = performance.now();
    let response;
    try {
      response = await fetch(path, {
        method: options.method || "GET",
        headers,
        body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error"
      });
    } catch (error) {
      notify({ online: false });
      throw new SetupError(0, error.message);
    }
    notify({ online: true, ms: Math.round(performance.now() - started) });
    if (response.status === 403 && retry && (options.method || "GET") !== "GET") {
      const why = await detail(response);
      if (/codice/i.test(why) || !code) {
        await askCode(code ? why : "");
        return request(path, options, false);
      }
      throw new SetupError(403, why);
    }
    if (!response.ok) throw new SetupError(response.status, await detail(response));
    return response;
  }

  async function json(path, options) {
    return (await request(path, options)).json();
  }

  window.SetupNet = Object.freeze({
    request,
    json,
    askCode,
    SetupError,
    onStatus: (fn) => listeners.add(fn)
  });
})();
