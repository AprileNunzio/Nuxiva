import { EVENT, MAX_REPORTS } from "./contracts.js";

export class I18nErrorBoundary {
  constructor(target = window, sink = console) {
    this._target = target;
    this._sink = sink;
    this._seen = new Set();
  }

  report(code, context = {}, level = "error") {
    const fingerprint = `${code}|${JSON.stringify(context)}`;
    if (this._seen.has(fingerprint)) return;
    if (this._seen.size >= MAX_REPORTS) this._seen.clear();
    this._seen.add(fingerprint);
    const detail = Object.freeze({ code, level, context: Object.freeze({ ...context }), timestamp: new Date().toISOString() });
    (level === "warn" ? this._sink.warn : this._sink.error).call(this._sink, "[i18n]", code, detail.context);
    this._target.dispatchEvent(new CustomEvent(EVENT.error, { detail }));
  }

  guard(promise, code, context = {}) {
    return Promise.resolve(promise).catch((error) => {
      this.report(code, { ...context, message: String(error && error.message ? error.message : error) });
      return null;
    });
  }
}
