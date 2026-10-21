const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, { style: {}, classList: { remove() {}, add() {}, toggle() {} } });
  return elements.get(id);
};
const scene = { setMode() {}, brain: { select() {} } };
const D = { $: element, mode: 'face', look: { mode: 'full' }, scene, avatar: scene, refreshBrain() {} };
const ThoughtCore = class { setMode() {} };
const context = { window: { NuxivaDisplay: D }, NuxivaAvatar: { ThoughtCore },
  document: { body: { classList: { remove() {}, add() {} } } } };
vm.runInNewContext(readFileSync(resolve(__dirname, '../../installer_wizard/web/display/look.js'), 'utf8'), context);
D.applyLookVisibility(true);
assert.equal(element('scene').style.display, 'block', 'display settings preserve the initialized 3D scene');
assert.equal(element('core').style.display, 'none');
D.applyLookVisibility(false);
assert.ok(D.avatar instanceof ThoughtCore, 'hiding the hologram initializes the lightweight assistant');
assert.equal(element('core').style.display, 'block');
D.setMode('brain');
assert.equal(element('scene').style.display, 'block', 'brain remains visible independently of avatar preference');
D.setMode('face');
assert.equal(element('core').style.display, 'block');
D.applyLookVisibility(true);
assert.equal(D.avatar, scene);
assert.equal(element('scene').style.display, 'block');
console.log('Display look: initialized 3D scene, lightweight fallback and brain visibility passed.');
