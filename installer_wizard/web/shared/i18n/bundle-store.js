import { FAILURE_TTL_MS, REQUEST_TIMEOUT_MS } from "./contracts.js";
import { validKey } from "./sanitizer.js";

function normalize(payload, scope, locale) {
  if (!payload || typeof payload !== "object") return null;
  const { meta, dictionary } = payload;
  if (!meta || meta.scope !== scope || !dictionary || typeof dictionary !== "object") return null;
  const entries = new Map();
  for (const [key, value] of Object.entries(dictionary)) {
    if (!validKey(key) || typeof value !== "string") return null;
    entries.set(key, value);
  }
  const fallbackKeys = Array.isArray(meta.fallback_keys) ? meta.fallback_keys.filter((key) => validKey(key)) : [];
  return Object.freeze({
    scope,
    locale,
    direction: meta.direction === "rtl" ? "rtl" : "ltr",
    dictionary: entries,
    fallbackKeys: Object.freeze(fallbackKeys),
  });
}

export class BundleStore {
  constructor({ endpoint, boundary, fetcher = (...args) => window.fetch(...args), now = () => Date.now() }) {
    this._endpoint = endpoint;
    this._boundary = boundary;
    this._fetch = fetcher;
    this._now = now;
    this._ready = new Map();
    this._failed = new Map();
    this._inflight = new Map();
    if (typeof window !== "undefined" && window.NUXIVA_I18N_BUNDLE && typeof window.NUXIVA_I18N_BUNDLE === "object") {
      const b = window.NUXIVA_I18N_BUNDLE;
      if (b.meta && b.meta.scope && b.meta.locale) {
        const norm = normalize(b, b.meta.scope, b.meta.locale);
        if (norm) this._ready.set(`${b.meta.scope}::${b.meta.locale}`, norm);
      }
    }
  }

  peek(scope, locale) {
    return this._ready.get(`${scope}::${locale}`) || null;
  }

  load(scope, locale) {
    const key = `${scope}::${locale}`;
    if (this._ready.has(key)) return Promise.resolve(this._ready.get(key));
    if ((this._failed.get(key) || 0) > this._now()) return Promise.resolve(null);
    if (this._inflight.has(key)) return this._inflight.get(key);
    const pending = this._request(scope, locale, key).finally(() => this._inflight.delete(key));
    this._inflight.set(key, pending);
    return pending;
  }

  async _request(scope, locale, key) {
    const url = `${this._endpoint}?scope=${encodeURIComponent(scope)}&locale=${encodeURIComponent(locale)}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    let response;
    try {
      response = await this._fetch(url, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-cache",
        redirect: "error",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
    } catch (error) {
      return this._fail(key, "BUNDLE_NETWORK_FAILURE", { scope, locale, message: String(error) });
    } finally {
      clearTimeout(timer);
    }
    if (!response.ok) return this._fail(key, "BUNDLE_HTTP_ERROR", { scope, locale, status: response.status });
    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      return this._fail(key, "BUNDLE_MALFORMED", { scope, locale, message: String(error) });
    }
    const bundle = normalize(payload, scope, locale);
    if (!bundle) return this._fail(key, "BUNDLE_SCHEMA_VIOLATION", { scope, locale });
    if (bundle.fallbackKeys.length) {
      this._boundary.report("BUNDLE_FALLBACK_KEYS", { scope, locale, total: bundle.fallbackKeys.length, sample: bundle.fallbackKeys.slice(0, 10) }, "warn");
    }
    this._failed.delete(key);
    this._ready.set(key, bundle);
    return bundle;
  }

  _fail(key, code, context) {
    this._failed.set(key, this._now() + FAILURE_TTL_MS);
    this._boundary.report(code, context);
    return null;
  }
}
