import {
  KEY_PATTERN,
  LOCALE_PATTERN,
  MAX_KEY_LENGTH,
  MAX_PARAMS_LENGTH,
  MAX_SCOPE_LENGTH,
  PARAM_PATTERN,
  SCOPE_PATTERN,
  TOKEN_PATTERN,
} from "./contracts.js";

const PRIMITIVES = new Set(["string", "number", "boolean"]);

export function validLocale(value) {
  if (typeof value !== "string") return null;
  const clean = value.trim();
  return LOCALE_PATTERN.test(clean) ? clean : null;
}

export function validScope(value) {
  if (typeof value !== "string") return null;
  const clean = value.trim().replace(/^\/+|\/+$/g, "");
  return clean.length <= MAX_SCOPE_LENGTH && SCOPE_PATTERN.test(clean) ? clean : null;
}

export function validKey(value) {
  return typeof value === "string" && value.length <= MAX_KEY_LENGTH && KEY_PATTERN.test(value) ? value : null;
}

export function cleanParams(candidate) {
  const params = Object.create(null);
  if (candidate === null || typeof candidate !== "object" || Array.isArray(candidate)) return null;
  for (const [name, value] of Object.entries(candidate)) {
    if (!PARAM_PATTERN.test(name) || !PRIMITIVES.has(typeof value)) return null;
    params[name] = String(value);
  }
  return params;
}

export function decodeParams(raw) {
  if (typeof raw !== "string" || raw.length > MAX_PARAMS_LENGTH) return null;
  try {
    return cleanParams(JSON.parse(raw));
  } catch (error) {
    if (error instanceof SyntaxError) return null;
    throw error;
  }
}

export function interpolate(template, params, onMissing) {
  return template.replace(TOKEN_PATTERN, (_, token) => {
    if (Object.hasOwn(params, token)) return params[token];
    onMissing(token);
    return "";
  });
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
