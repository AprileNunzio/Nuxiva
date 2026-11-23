(() => {
  const EDITABLE = new Set(["INPUT", "TEXTAREA", "SELECT"]);
  const NATIVE_ACTIVATION = new Set(["BUTTON", "A", "SUMMARY"]);

  const KEYS = Object.freeze({
    galaxy: Object.freeze({ ArrowRight: "next", ArrowLeft: "prev", Enter: "open", Escape: "close" }),
    project: Object.freeze({ ArrowRight: "next", ArrowLeft: "prev", Escape: "back", Backspace: "back", p: "toggle", P: "toggle" }),
  });

  const GESTURES = Object.freeze({
    galaxy: Object.freeze({ "swipe.left": "next", "swipe.right": "prev", "swipe.up": "open", "swipe.down": "close" }),
    project: Object.freeze({ "swipe.left": "next", "swipe.right": "prev", "swipe.down": "back" }),
  });

  const lookup = (table, key) => (typeof key === "string" && Object.hasOwn(table, key) ? table[key] : null);
  const scope = (focused) => (focused ? "project" : "galaxy");

  function typing(target) {
    return Boolean(target) && (EDITABLE.has(target.tagName) || target.isContentEditable === true);
  }

  function fromKey(event, focused) {
    if (!event || event.defaultPrevented || event.isComposing) return null;
    if (event.ctrlKey || event.metaKey || event.altKey) return null;
    if (typing(event.target)) return null;
    if (event.key === "Enter" && event.target && NATIVE_ACTIVATION.has(event.target.tagName)) return null;
    return lookup(KEYS[scope(focused)], event.key);
  }

  function fromGesture(name, focused) {
    return lookup(GESTURES[scope(focused)], name);
  }

  const api = Object.freeze({ fromKey, fromGesture, typing });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.NuxivaAgencyInput = api;
})();
