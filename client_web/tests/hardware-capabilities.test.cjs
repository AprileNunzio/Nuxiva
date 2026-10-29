const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync(path.join(__dirname, '../src/app_shell/hardware/capabilities.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const context = { exports: {} };
vm.runInNewContext(compiled, context);
const parse = context.exports.parseHardwareCapabilities;

const result = parse({ capabilities: { 'network.wifi': ['usb:device'], 'compute.accelerator': [] } });
assert.equal(result['network.wifi'][0], 'usb:device');
assert.equal(result['compute.accelerator'].length, 0);
assert.equal(Object.getPrototypeOf(result), null);

for (const value of [null, {}, { capabilities: [] }, { capabilities: { wifi: ['device'] } },
  { capabilities: { 'network.wifi': [42] } }, { capabilities: { 'network.wifi': [''] } },
  JSON.parse('{"capabilities":{"__proto__":["device"]}}')]) {
  assert.throws(() => parse(value), /invalid_hardware_capabilities/);
}

const devices = ['first'];
const snapshot = parse({ capabilities: { 'network.wifi': devices } });
devices.push('second');
assert.equal(snapshot['network.wifi'].length, 1);
console.log('Hardware capability validation and isolated snapshots passed.');
