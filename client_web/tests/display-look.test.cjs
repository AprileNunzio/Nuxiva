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
const context = {
  window: { NuxivaDisplay: D },
  NuxivaAvatar: { ThoughtCore },
  document: { body: { classList: { remove() {}, add() {} } } },
};

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

let lastFaceOptions = null;
const NuxivaScene = class {
  constructor(canvas, handlers) {
    lastFaceOptions = handlers.faceOptions;
    this.setMode = () => {};
    this.setWeather = () => {};
    this.frames = 60;
  }
};
context.Nuxiva3D = { NuxivaScene };
context.document.head = { appendChild(el) { if (el.onload) el.onload(); } };
context.document.createElement = () => ({});
context.document.documentElement = { style: { setProperty() {}, removeProperty() {} } };
context.NuxivaAvatar.choose = () => ({ mode: 'full', reason: ['auto', {}], info: {} });
context.NuxivaAvatar.watchFps = () => {};

(async () => {
  D.FACE = { color: '#29e0ff', style: 'character', model: '/vendor/Michelle.glb' };
  D.startLook();
  await new Promise(r => setImmediate(r));
  assert.ok(lastFaceOptions, 'faceOptions passed to scene');
  assert.equal(lastFaceOptions.style, 'character');
  assert.equal(lastFaceOptions.character, '/vendor/Michelle.glb');
  assert.equal(lastFaceOptions.customModel, null);

  D.FACE = { color: '#ff00aa', style: 'character', model: '/api/avatars/serve/Hero/hero.glb', custom_model: '/api/avatars/serve/Hero/hero.glb' };
  D.startLook();
  await new Promise(r => setImmediate(r));
  assert.equal(lastFaceOptions.character, '/api/avatars/serve/Hero/hero.glb');
  assert.equal(lastFaceOptions.customModel, '/api/avatars/serve/Hero/hero.glb');

  D.FACE = { color: '#00ffcc', style: 'hologram', model: '/api/avatars/serve/Holo/head.glb', custom_model: '/api/avatars/serve/Holo/head.glb' };
  D.startLook();
  await new Promise(r => setImmediate(r));
  assert.equal(lastFaceOptions.character, undefined);
  assert.equal(lastFaceOptions.model, '/api/avatars/serve/Holo/head.glb');
  assert.equal(lastFaceOptions.customModel, '/api/avatars/serve/Holo/head.glb');

  console.log('Display look: initialized 3D scene, lightweight fallback and brain visibility passed.');
})().catch(err => {
  console.error(err);
  process.exit(1);
});
