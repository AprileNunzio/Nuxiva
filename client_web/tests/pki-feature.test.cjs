const { readFileSync } = require('node:fs');
const { join, resolve } = require('node:path');
const assert = require('node:assert/strict');

const pkiDir = resolve(__dirname, '../src/features/pki');
const indexPath = join(pkiDir, 'index.ts');
const indexContent = readFileSync(indexPath, 'utf8');

assert.ok(indexContent.includes('PkiManagerView'));
assert.ok(indexContent.includes('fetchPkiStatus'));
assert.ok(indexContent.includes('generateEnterpriseCertificate'));
assert.ok(indexContent.includes('downloadClientBundle'));

const requiredKeys = [
  'title',
  'subtitle',
  'ca_card_title',
  'ca_active',
  'ca_subject',
  'ca_fingerprint',
  'ca_expires',
  'download_ca_crt',
  'download_ca_pem',
  'server_card_title',
  'server_active',
  'server_expires',
  'sans_title',
  'tailscale_detected',
  'vpn_detected',
  'lan_detected',
  'configure_title',
  'opt_tailscale',
  'opt_vpn',
  'opt_lan',
  'custom_dns_label',
  'custom_ips_label',
  'btn_generate',
  'btn_generating',
  'client_title',
  'client_identity_label',
  'client_password_label',
  'btn_download_client',
  'success_msg',
  'error_msg',
];

const locales = ['it', 'en', 'es', 'fr'];
for (const locale of locales) {
  const langPath = join(pkiDir, 'language', `${locale}.json`);
  const data = JSON.parse(readFileSync(langPath, 'utf8'));
  const dict = data.dictionary || data;
  for (const key of requiredKeys) {
    assert.ok(
      typeof dict[key] === 'string' && dict[key].length > 0,
      `Missing PKI key ${key} in ${locale}.json`
    );
  }

  const optionsLangPath = resolve(__dirname, `../src/core_apps/options/language/${locale}.json`);
  const optData = JSON.parse(readFileSync(optionsLangPath, 'utf8'));
  const optDict = optData.dictionary || optData;
  assert.ok(
    typeof optDict.tab_certificates === 'string' && optDict.tab_certificates.length > 0,
    `Missing tab_certificates in options/${locale}.json`
  );
}

console.log('Enterprise PKI feature & translations test passed.');
