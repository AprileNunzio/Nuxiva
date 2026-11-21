const { readFileSync } = require('node:fs');
const { join, resolve } = require('node:path');
const assert = require('node:assert/strict');

const optionsDir = resolve(__dirname, '../src/core_apps/options');
const statePath = join(optionsDir, 'optionsState.ts');
const stateContent = readFileSync(statePath, 'utf8');

assert.ok(stateContent.includes("id: 'display_remote_kiosk'"));
assert.ok(stateContent.includes("category: 'display'"));
assert.ok(stateContent.includes('enabled: false'));
assert.ok(stateContent.includes('defaultEnabled: false'));
assert.ok(stateContent.includes('syncRemoteKioskBackend'));

const requiredKeys = [
  'opt_remote_kiosk_title',
  'opt_remote_kiosk_desc',
  'advisory_title',
  'advisory_subtitle',
  'advisory_security_badge',
  'advisory_desc',
  'advisory_media_notice',
  'advisory_disable_btn',
  'advisory_enable_btn',
  'advisory_review_btn',
];

const locales = ['it', 'en', 'es', 'fr'];
for (const locale of locales) {
  const langPath = join(optionsDir, 'language', `${locale}.json`);
  const data = JSON.parse(readFileSync(langPath, 'utf8'));
  const dict = data.dictionary || data;
  for (const key of requiredKeys) {
    assert.ok(
      typeof dict[key] === 'string' && dict[key].length > 0,
      `Missing translation key ${key} in ${locale}.json`
    );
  }
}

const featureDir = resolve(__dirname, '../src/features/remote_kiosk');
const featureIndexPath = join(featureDir, 'index.ts');
const featureIndexContent = readFileSync(featureIndexPath, 'utf8');

assert.ok(featureIndexContent.includes('RemoteKioskGlobalPrompt'));
assert.ok(featureIndexContent.includes('RemoteKioskAdvisoryModal'));
assert.ok(featureIndexContent.includes('shouldShowRemoteKioskAdvisory'));
assert.ok(featureIndexContent.includes('saveRemoteKioskAdvisoryAck'));

const featureRequiredKeys = [
  'advisory_title',
  'advisory_subtitle',
  'advisory_security_badge',
  'advisory_desc',
  'advisory_media_notice',
  'advisory_disable_btn',
  'advisory_enable_btn',
  'advisory_close',
];

for (const locale of locales) {
  const langPath = join(featureDir, 'language', `${locale}.json`);
  const data = JSON.parse(readFileSync(langPath, 'utf8'));
  const dict = data.dictionary || data;
  for (const key of featureRequiredKeys) {
    assert.ok(
      typeof dict[key] === 'string' && dict[key].length > 0,
      `Missing feature translation key ${key} in ${locale}.json`
    );
  }
}

console.log('Remote kiosk options & advisory test passed.');
