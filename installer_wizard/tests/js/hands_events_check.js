const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const dispatched = [];
const window = {
  innerWidth: 1000, innerHeight: 500, NuxivaDisplay: {},
  dispatchEvent: (e) => dispatched.push(e),
};
class CustomEvent { constructor(type, init) { this.type = type; this.detail = init.detail; } }
class WheelEvent { constructor(type, init) { this.type = type; Object.assign(this, init); } }
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../web/display/hands_events.js"), "utf8"), { window, CustomEvent, WheelEvent });

const calls = [];
const st = { x: 0, y: 0, pinch: false, duo: null, spread: null };
const handle = window.NuxivaHandsEvents.create({
  state: st,
  press: (x, y) => calls.push(["press", x, y]),
  drag: (x, y) => calls.push(["drag", x, y]),
  release: (x, y) => calls.push(["release", x, y]),
  pointAt: () => ({ closest: () => null }),
  emit: (phase) => { calls.push(["emit", phase]); return false; },
  spread: (el, span) => calls.push(["spread", Number(span.toFixed(3))]),
  showCursor: () => calls.push(["show"]),
  hideCursor: () => calls.push(["hide"]),
});

handle({ type: "pointer", phase: "down", x: 0.5, y: 0.5 });
handle({ type: "pointer", phase: "drag", x: 0.6, y: 0.5 });
handle({ type: "pointer", phase: "up", x: 0.6, y: 0.5 });
handle({ type: "pointer", phase: "hidden", x: 0.6, y: 0.5 });
assert.deepStrictEqual(calls.filter((c) => c[0] !== "show").map((c) => c[0]), ["press", "drag", "release", "hide"]);
assert.deepStrictEqual(calls[0], ["press", 500, 250]);
assert.strictEqual(st.pinch, false);

calls.length = 0;
handle({ type: "duo", phase: "start", x: 0.5, y: 0.5 });
handle({ type: "duo", phase: "update", x: 0.5, y: 0.5, scale: 1.2, rotate: 0, pan_x: 0, pan_y: 0 });
handle({ type: "duo", phase: "update", x: 0.5, y: 0.5, scale: 1.5, rotate: 0, pan_x: 0, pan_y: 0 });
handle({ type: "duo", phase: "end", x: 0.5, y: 0.5 });
assert.deepStrictEqual(calls, [["emit", "start"], ["emit", "update"], ["spread", 1.2], ["emit", "update"], ["spread", 1.8], ["emit", "end"]]);
assert.strictEqual(st.duo, null);

handle({ type: "action", action: "media.next", gesture: "swipe.right" });
handle({ type: "gesture", gesture: "pose.fist" });
assert.deepStrictEqual(dispatched.map((e) => e.type), ["nuxiva-hand-action", "nuxiva-hand-gesture"]);
assert.strictEqual(dispatched[0].detail.action, "media.next");
console.log("ok");
