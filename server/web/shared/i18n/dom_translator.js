export function applyDomTranslations(dictionary, root = document) {
  if (!dictionary || typeof dictionary !== "object") return;

  const elements = root.querySelectorAll("[data-i18n]");
  elements.forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key) return;

    const val = resolveTranslationKey(dictionary, key);
    if (val !== undefined && val !== null) {
      if (el.tagName === "INPUT" && (el.type === "button" || el.type === "submit")) {
        el.value = val;
      } else {
        el.textContent = val;
      }
    }
  });

  const placeholders = root.querySelectorAll("[data-i18n-placeholder]");
  placeholders.forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (!key) return;

    const val = resolveTranslationKey(dictionary, key);
    if (val !== undefined && val !== null) {
      el.placeholder = val;
    }
  });
}

function resolveTranslationKey(dict, path) {
  if (dict[path] !== undefined) return dict[path];
  const parts = path.split(".");
  let cur = dict;
  for (const part of parts) {
    if (cur === undefined || cur === null || typeof cur !== "object") return undefined;
    cur = cur[part];
  }
  return cur;
}
