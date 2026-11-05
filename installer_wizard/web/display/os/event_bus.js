(() => {
  "use strict";

  class OSEventBus {
    constructor() {
      this._listeners = new Map();
    }

    on(topic, handler) {
      if (typeof handler !== "function") return () => {};
      if (!this._listeners.has(topic)) {
        this._listeners.set(topic, new Set());
      }
      this._listeners.get(topic).add(handler);
      return () => this.off(topic, handler);
    }

    off(topic, handler) {
      const set = this._listeners.get(topic);
      if (set) {
        set.delete(handler);
        if (set.size === 0) this._listeners.delete(topic);
      }
    }

    emit(topic, payload = {}) {
      const set = this._listeners.get(topic);
      if (set) {
        set.forEach((handler) => {
          try {
            handler(payload);
          } catch (err) {
            console.error(`[OSEventBus] Error in handler for ${topic}:`, err);
          }
        });
      }
    }

    clear() {
      this._listeners.clear();
    }
  }

  window.NuxivaOSEventBus = new OSEventBus();
})();
