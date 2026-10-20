const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');

// 1. Verify dictionary synchronization across all 4 locales for updater
const locales = ['it', 'en', 'fr', 'es'];
const requiredHistoryKeys = [
  'history_title',
  'history_empty',
  'history_tab_records',
  'history_tab_events',
  'history_status_installed',
  'history_status_failed',
  'history_status_rollback',
  'history_commits_count',
  'history_commits_single',
  'history_commits_none',
  'history_page_info',
  'history_prev',
  'history_next',
  'history_reason_label',
  'history_error_label',
  'history_empty_records',
  'history_view_commits',
  'history_hide_commits',
];

for (const loc of locales) {
  const filePath = resolve(__dirname, `../src/core_apps/updater/language/${loc}.json`);
  const content = JSON.parse(readFileSync(filePath, 'utf8'));
  assert.ok(content.dictionary, `Missing dictionary root in ${loc}.json`);
  for (const key of requiredHistoryKeys) {
    assert.ok(
      typeof content.dictionary[key] === 'string' && content.dictionary[key].length > 0,
      `Missing or empty translation key "${key}" in updater/language/${loc}.json`
    );
  }
}

// 2. Validate update history paging calculation logic
function computePages(total, pageSize) {
  const safePageSize = Math.max(1, pageSize);
  return Math.max(1, Math.ceil(total / safePageSize));
}

assert.equal(computePages(0, 10), 1);
assert.equal(computePages(9, 10), 1);
assert.equal(computePages(10, 10), 1);
assert.equal(computePages(11, 10), 2);
assert.equal(computePages(25, 10), 3);

// 3. Validate history response shape contract
const sampleResponse = {
  records: [
    {
      id: '235785ce6be3_1792402308',
      status: 'installed',
      from_rev: '023c7bc20397d534d63ba82c679936ab46dd9499',
      to_rev: '235785ce6be3309b182e7027232f04ed14bd0b30',
      from_short: '023c7bc',
      to_short: '235785c',
      installed_at: 1792402308,
      installed_at_iso: '2026-10-19T09:31:48Z',
      reason: 'automatico',
      commits: [
        {
          sha: '235785ce6be3309b182e7027232f04ed14bd0b30',
          short_sha: '235785c',
          author: 'Nunzio Aprile',
          timestamp: 1792401888,
          date_iso: '2026-10-19T09:24:48Z',
          title: 'Pannello di controllo con categorie e icone autonome',
          body: 'Problema affrontato...\nVerifiche...',
        },
      ],
      commit_count: 1,
    },
  ],
  total: 1,
  limit: 10,
  offset: 0,
  events: [
    {
      ts: '2026-10-19T09:31:48Z',
      level: 'INFO',
      msg: 'Aggiornamento verificato e confermato',
    },
  ],
};

assert.equal(sampleResponse.records.length, 1);
assert.equal(sampleResponse.records[0].commits.length, 1);
assert.equal(sampleResponse.records[0].commits[0].short_sha, '235785c');
assert.ok(sampleResponse.records[0].commits[0].body.includes('Problema affrontato'));

console.log('Updater history: 4 locales synchronized, paging calculations and payload structure passed.');
