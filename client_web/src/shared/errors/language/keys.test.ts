import { describe, expect, it } from 'vitest';
import it_ from './it.json';
import en from './en.json';
import fr from './fr.json';
import es from './es.json';

const dictionaries: Record<string, Record<string, string>> = { it: it_.dictionary, en: en.dictionary, fr: fr.dictionary, es: es.dictionary };
const kinds = ['unreachable', 'offline', 'timeout', 'http', 'invalid_response', 'application'];
const http = ['400', '401', '403', '404', '409', '413', '429', '500', '503', 'other'];
const required = [
  'error_unknown_code',
  'error_server_unreachable',
  'copy_details',
  'copied',
  ...kinds.map((k) => `outcome_${k}`),
  ...kinds.filter((k) => k !== 'http').map((k) => `hint_${k}`),
  ...http.map((s) => `hint_http_${s}`),
  ...['what_to_do', 'request', 'outcome', 'server_code', 'server_message', 'duration', 'duration_value', 'internal_code', 'time', 'raw'].map((d) => `detail_${d}`),
  ...['down_title', 'offline_title', 'restored_title', 'down_body', 'offline_body', 'restored_body', 'retry_in', 'checking', 'retry_now', 'last_probe', 'server_phase', 'failed_calls'].map((c) => `connectivity_${c}`),
  ...['forbidden', 'unsupported', 'adapter_missing', 'service_failed', 'unavailable', 'reset_failed'].map((b) => `error_node_bluetooth_${b}`),
];

describe('error dictionaries', () => {
  it.each(Object.keys(dictionaries))('%s has every diagnostic key', (lang) => {
    const missing = required.filter((key) => typeof dictionaries[lang][key] !== 'string' || !dictionaries[lang][key].trim());
    expect(missing).toEqual([]);
  });

  it('all languages share the same placeholders', () => {
    const placeholders = (text: string) => (text.match(/\{[a-z_]+\}/g) ?? []).sort().join(',');
    for (const key of required) {
      const reference = placeholders(dictionaries.it[key]);
      for (const lang of Object.keys(dictionaries)) {
        expect([key, lang, placeholders(dictionaries[lang][key])]).toEqual([key, lang, reference]);
      }
    }
  });
});
