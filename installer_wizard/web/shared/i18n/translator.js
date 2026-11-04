import { ATTR, MARKUP_TAGS } from "./contracts.js";
import { cleanParams, escapeHtml, interpolate, validKey } from "./sanitizer.js";

const NO_PARAMS = Object.freeze(Object.create(null));

export function render(bundle, key, params, report) {
  const template = bundle.dictionary.get(key);
  if (template === undefined) {
    report("MISSING_TRANSLATION_KEY", { scope: bundle.scope, locale: bundle.locale, key }, "warn");
    return null;
  }
  return interpolate(template, params || NO_PARAMS, (token) => {
    report("MISSING_TRANSLATION_PARAM", { scope: bundle.scope, key, token }, "warn");
  });
}

export function markup(key, params = {}, tag = "span") {
  if (!validKey(key)) throw new TypeError(`Invalid i18n key: ${String(key)}`);
  if (!MARKUP_TAGS.includes(tag)) throw new TypeError(`Tag not allowed for i18n markup: ${String(tag)}`);
  const clean = cleanParams(params);
  if (!clean) throw new TypeError(`Invalid i18n params for ${key}`);
  const encoded = Object.keys(clean).length ? ` ${ATTR.params}="${escapeHtml(JSON.stringify(clean))}"` : "";
  return `<${tag} ${ATTR.text}="${escapeHtml(key)}"${encoded}></${tag}>`;
}

export function toParams(params) {
  if (params === undefined) return NO_PARAMS;
  const clean = cleanParams(params);
  if (!clean) throw new TypeError("Invalid i18n params");
  return clean;
}
