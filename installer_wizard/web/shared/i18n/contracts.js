export const ENDPOINT = "/api/i18n/bundle";
export const DEFAULT_LOCALE = "it";
export const REQUEST_TIMEOUT_MS = 8000;
export const FAILURE_TTL_MS = 30000;
export const MAX_REPORTS = 500;

export const LOCALE_PATTERN = /^[a-z]{2,3}(?:-[A-Z]{2})?$/;
export const SCOPE_PATTERN = /^[a-z][a-z0-9_]*(?:\/[a-z0-9][a-z0-9_-]*){1,6}$/;
export const KEY_PATTERN = /^[a-z0-9_]+(?:\.[a-z0-9_]+){0,7}$/;
export const PARAM_PATTERN = /^[a-zA-Z0-9_]{1,64}$/;
export const TOKEN_PATTERN = /\{\{\s*([a-zA-Z0-9_]{1,64})\s*\}\}/g;

export const MAX_SCOPE_LENGTH = 160;
export const MAX_KEY_LENGTH = 128;
export const MAX_PARAMS_LENGTH = 2048;

export const TRANSLATABLE_ATTRIBUTES = Object.freeze(["placeholder", "title", "aria-label", "aria-description", "alt"]);
export const MARKUP_TAGS = Object.freeze(["span", "strong", "em", "small", "b"]);

export const ATTR = Object.freeze({
  scope: "data-i18n-scope",
  text: "data-i18n",
  attributes: "data-i18n-attr",
  params: "data-i18n-params",
});

export const SELECTOR = Object.freeze({
  scope: `[${ATTR.scope}]`,
  node: `[${ATTR.text}],[${ATTR.attributes}]`,
});

export const EVENT = Object.freeze({
  error: "nuxiva:i18n:error",
  changed: "nuxiva:i18n:changed",
  legacy: "nuxiva-translated",
});
