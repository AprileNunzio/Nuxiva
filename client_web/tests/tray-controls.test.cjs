const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const netDir = path.resolve(__dirname, '../src/app_shell/tray/network');
const bleDir = path.resolve(__dirname, '../src/app_shell/tray/bluetooth');

const locales = ['it', 'en', 'es', 'fr'];
const netKeys = ['title', 'wifi', 'interfaces', 'connect', 'disconnect', 'wifi_enabled', 'wifi_disabled'];
const bleKeys = ['title', 'turn_on', 'turn_off', 'connected', 'connect', 'disconnect', 'pair', 'forget'];

for (const loc of locales) {
  const netPath = path.join(netDir, `language/${loc}.json`);
  assert.ok(fs.existsSync(netPath), `Missing network translation: ${loc}`);
  const netJson = JSON.parse(fs.readFileSync(netPath, 'utf8'));
  for (const k of netKeys) {
    assert.ok(typeof netJson[k] === 'string' && netJson[k].length > 0, `Missing key ${k} in network ${loc}`);
  }

  const blePath = path.join(bleDir, `language/${loc}.json`);
  assert.ok(fs.existsSync(blePath), `Missing bluetooth translation: ${loc}`);
  const bleJson = JSON.parse(fs.readFileSync(blePath, 'utf8'));
  for (const k of bleKeys) {
    assert.ok(typeof bleJson[k] === 'string' && bleJson[k].length > 0, `Missing key ${k} in bluetooth ${loc}`);
  }
}

const checkFiles = [
  path.join(netDir, 'NetworkFlyout.tsx'),
  path.join(netDir, 'useNetworkState.ts'),
  path.join(netDir, 'types.ts'),
  path.join(bleDir, 'BluetoothFlyout.tsx'),
  path.join(bleDir, 'useBluetoothState.ts'),
  path.join(bleDir, 'types.ts'),
];

const doubleSlash = String.fromCharCode(47, 47);
const slashStar = String.fromCharCode(47, 42);

for (const file of checkFiles) {
  assert.ok(fs.existsSync(file), `File missing: ${file}`);
  const text = fs.readFileSync(file, 'utf8');
  assert.ok(!text.includes(doubleSlash) && !text.includes(slashStar), `Comment detected in ${file}`);
}

console.log('Tray network and bluetooth controls: dictionaries, keys, interfaces and pure code passed.');
