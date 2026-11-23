const assert = require("assert");
const input = require("../../web/display/agency/input.js");

const key = (k, extra = {}) => ({ key: k, target: { tagName: "BODY" }, ...extra });

assert.strictEqual(input.fromKey(key("ArrowRight"), false), "next");
assert.strictEqual(input.fromKey(key("ArrowLeft"), false), "prev");
assert.strictEqual(input.fromKey(key("Enter"), false), "open");
assert.strictEqual(input.fromKey(key("Escape"), false), "close");
assert.strictEqual(input.fromKey(key("Escape"), true), "back");
assert.strictEqual(input.fromKey(key("Backspace"), true), "back");
assert.strictEqual(input.fromKey(key("p"), true), "toggle");
assert.strictEqual(input.fromKey(key("P"), true), "toggle");
assert.strictEqual(input.fromKey(key("ArrowRight"), true), "next");
assert.strictEqual(input.fromKey(key("ArrowLeft"), true), "prev");
assert.strictEqual(input.fromKey(key("p"), false), null);
assert.strictEqual(input.fromKey(key("x"), true), null);

for (const tagName of ["INPUT", "TEXTAREA", "SELECT"]) {
  for (const k of ["p", "Backspace", "Enter", "ArrowLeft", "Escape"]) {
    assert.strictEqual(input.fromKey({ key: k, target: { tagName } }, true), null, `${tagName} ${k}`);
  }
}
assert.strictEqual(input.fromKey({ key: "p", target: { tagName: "DIV", isContentEditable: true } }, true), null);

for (const modifier of ["ctrlKey", "metaKey", "altKey"]) {
  assert.strictEqual(input.fromKey(key("p", { [modifier]: true }), true), null);
}
assert.strictEqual(input.fromKey(key("p", { isComposing: true }), true), null);
assert.strictEqual(input.fromKey(key("p", { defaultPrevented: true }), true), null);
assert.strictEqual(input.fromKey({ key: "Enter", target: { tagName: "BUTTON" } }, false), null);
assert.strictEqual(input.fromKey({ key: "Enter", target: { tagName: "A" } }, false), null);

for (const hostile of ["constructor", "__proto__", "toString", "hasOwnProperty", undefined, null, 7]) {
  assert.strictEqual(input.fromKey(key(hostile), true), null);
  assert.strictEqual(input.fromKey(key(hostile), false), null);
  assert.strictEqual(input.fromGesture(hostile, true), null);
}
assert.strictEqual(input.fromKey(null, true), null);

assert.strictEqual(input.fromGesture("swipe.left", false), "next");
assert.strictEqual(input.fromGesture("swipe.right", true), "prev");
assert.strictEqual(input.fromGesture("swipe.up", false), "open");
assert.strictEqual(input.fromGesture("swipe.up", true), null);
assert.strictEqual(input.fromGesture("swipe.down", false), "close");
assert.strictEqual(input.fromGesture("swipe.down", true), "back");

const keyboardReach = (focused) => {
  const names = ["ArrowRight", "ArrowLeft", "Enter", "Escape", "Backspace", "p"];
  return new Set(names.map((n) => input.fromKey(key(n), focused)).filter(Boolean));
};
const gestures = ["swipe.left", "swipe.right", "swipe.up", "swipe.down"];
for (const focused of [false, true]) {
  const reach = keyboardReach(focused);
  for (const g of gestures) {
    const action = input.fromGesture(g, focused);
    if (action) assert.ok(reach.has(action), `gesture action ${action} has no keyboard path (focused=${focused})`);
  }
}
