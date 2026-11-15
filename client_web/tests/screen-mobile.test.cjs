const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../installer_wizard/web/screen/mobile.js'), 'utf8');
const sandbox = { window: {} };
sandbox.window.window = sandbox.window;
vm.runInNewContext(source, sandbox);
const mobile = sandbox.window.NuxivaScreenMobile;

assert.equal(mobile.active, false);
assert.equal(mobile.decide({ width: 390, height: 844, widgets: false }), 'core-full');
assert.equal(mobile.decide({ width: 390, height: 844, widgets: true }), 'flow');
assert.equal(mobile.decide({ width: 820, height: 1180, widgets: true }), 'core-dock');
assert.equal(mobile.decide({ width: 820, height: 600, widgets: true }), 'flow');
assert.equal(mobile.decide({ width: 820, height: 1180, widgets: false }), 'core-full');
assert.equal(mobile.SIZES['core-full'], 0);
assert.ok(Object.isFrozen(mobile));
console.log('screen-mobile ok');
