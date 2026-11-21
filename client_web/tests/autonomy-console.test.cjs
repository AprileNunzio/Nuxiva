const { readFileSync } = require('node:fs');
const { join, resolve } = require('node:path');
const assert = require('node:assert/strict');

const featureDir = resolve(__dirname, '../src/features/autonomy_console');
const indexPath = join(featureDir, 'index.ts');
const viewPath = join(featureDir, 'AutonomyConsoleView.tsx');
const apiPath = join(featureDir, 'autonomyApi.ts');

const indexContent = readFileSync(indexPath, 'utf8');
const viewContent = readFileSync(viewPath, 'utf8');
const apiContent = readFileSync(apiPath, 'utf8');

assert.ok(indexContent.includes('AutonomyConsoleView'));
assert.ok(indexContent.includes('fetchAutonomySnapshot'));
assert.ok(indexContent.includes('submitEpistemicDecision'));
assert.ok(viewContent.split('\n').length < 500);
assert.ok(apiContent.includes('sanitizeToken'));

const requiredKeys = [
  'autonomy.console.title',
  'autonomy.console.confidence_label',
  'autonomy.console.questions_section',
  'autonomy.console.questions_empty',
  'autonomy.console.voi_label',
  'autonomy.console.forge_section',
  'autonomy.console.forge_empty',
  'autonomy.console.tests_passed',
  'autonomy.console.shortcuts_section',
  'autonomy.console.shortcuts_empty',
  'autonomy.console.zero_token_badge',
  'autonomy.console.hits_label',
  'autonomy.scope.architecture',
  'autonomy.scope.data_model',
  'autonomy.scope.security_policy',
  'autonomy.scope.payment_and_compliance',
  'autonomy.scope.user_experience',
  'autonomy.scope.integration_contract',
  'autonomy.status.proposed',
  'autonomy.status.active',
  'autonomy.status.quarantined',
  'autonomy.status.revoked',
];

const locales = ['it', 'en', 'es', 'fr'];
for (const locale of locales) {
  const langPath = join(featureDir, 'language', `${locale}.json`);
  const dict = JSON.parse(readFileSync(langPath, 'utf8'));
  for (const key of requiredKeys) {
    assert.ok(
      typeof dict[key] === 'string' && dict[key].length > 0,
      `Missing autonomy_console key ${key} in ${locale}.json`
    );
  }
}

console.log('Autonomy Console feature & i18n test passed.');
