import { BundleStore } from "./bundle-store.js";
import { DEFAULT_LOCALE, ENDPOINT, EVENT } from "./contracts.js";
import { DomScanner } from "./dom-scanner.js";
import { I18nErrorBoundary } from "./error-boundary.js";
import { validKey, validLocale, validScope } from "./sanitizer.js";
import { markup, render, toParams } from "./translator.js";

function initialLocale() {
  const legacy = window.NuxivaI18n && typeof window.NuxivaI18n.language === "function" ? window.NuxivaI18n.language() : null;
  return validLocale(window.NUXIVA_UI_LANG) || validLocale(legacy) || validLocale(document.documentElement.lang) || DEFAULT_LOCALE;
}

function requireScope(scope) {
  const clean = validScope(scope);
  if (!clean) throw new TypeError(`Invalid i18n scope: ${String(scope)}`);
  return clean;
}

const boundary = new I18nErrorBoundary();
const store = new BundleStore({ endpoint: ENDPOINT, boundary });
const scanner = new DomScanner({ store, boundary, locale: initialLocale() });
const report = (code, context, level) => boundary.report(code, context, level);

function t(scope, key, params) {
  const cleanScope = requireScope(scope);
  if (!validKey(key)) throw new TypeError(`Invalid i18n key: ${String(key)}`);
  const bundle = store.peek(cleanScope, scanner.locale);
  if (!bundle) {
    report("BUNDLE_NOT_PRELOADED", { scope: cleanScope, key }, "warn");
    boundary.guard(store.load(cleanScope, scanner.locale), "PRELOAD_FAILURE", { scope: cleanScope });
    return "";
  }
  return render(bundle, key, toParams(params), report) ?? "";
}

function preload(scope) {
  const cleanScope = requireScope(scope);
  return boundary.guard(store.load(cleanScope, scanner.locale), "PRELOAD_FAILURE", { scope: cleanScope });
}

document.addEventListener(EVENT.legacy, (event) => {
  boundary.guard(scanner.setLocale(event.detail), "LOCALE_SWITCH_FAILURE", { requested: String(event.detail) });
});

window.NuxivaScopedI18n = Object.freeze({
  locale: () => scanner.locale,
  setLocale: (locale) => boundary.guard(scanner.setLocale(locale), "LOCALE_SWITCH_FAILURE", { requested: String(locale) }),
  scan: (root) => boundary.guard(scanner.scan(root), "SCAN_FAILURE"),
  preload,
  t,
  markup,
});

boundary.guard(scanner.observe(document.body), "SCANNER_START_FAILURE");
