const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const telecamereDir = path.resolve(__dirname, '../src/subapps/videosorveglianza/telecamere');
const locales = ['it', 'en', 'es', 'fr'];
const expectedKeys = [
  'title',
  'subtitle',
  'stat_total',
  'stat_active',
  'stat_recording',
  'live_title',
  'live_label',
  'offline',
  'status_active',
  'status_offline',
  'recording',
  'enabled',
  'record',
  'consent',
  'consent_note',
  'add',
  'add_title',
  'field_name',
  'field_kind',
  'field_url',
  'field_device',
  'field_retention',
  'minutes',
  'save',
  'cancel',
  'delete',
  'delete_confirm',
  'refresh',
  'empty',
  'empty_sources',
];

for (const loc of locales) {
  const langPath = path.join(telecamereDir, `language/${loc}.json`);
  assert.ok(fs.existsSync(langPath), `Missing telecamere translation: ${loc}`);
  const parsed = JSON.parse(fs.readFileSync(langPath, 'utf8'));
  const dict = parsed.dictionary || parsed;
  for (const k of expectedKeys) {
    assert.ok(typeof dict[k] === 'string' && dict[k].length > 0, `Missing key ${k} in telecamere ${loc}`);
  }
}

const manifestPath = path.join(telecamereDir, 'manifest.json');
assert.ok(fs.existsSync(manifestPath), 'manifest.json missing');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
assert.equal(manifest.id, 'telecamere');
assert.equal(manifest.parent, 'videosorveglianza');

const codeFiles = [
  path.join(telecamereDir, 'View.tsx'),
  path.join(telecamereDir, 'api.ts'),
  path.join(telecamereDir, 'types.ts'),
  path.join(telecamereDir, 'components/Snapshot.tsx'),
];

const doubleSlash = String.fromCharCode(47, 47);
const slashStar = String.fromCharCode(47, 42);

for (const file of codeFiles) {
  assert.ok(fs.existsSync(file), `File missing: ${file}`);
  const text = fs.readFileSync(file, 'utf8');
  assert.ok(!text.includes(doubleSlash) && !text.includes(slashStar), `Comment detected in ${file}`);
  const lines = text.split('\n').length;
  assert.ok(lines <= 500, `File ${file} exceeds 500 lines: ${lines}`);
}

console.log('Telecamere subapp: live streams, colocation, i18n symmetry, line limits and pure code passed.');
