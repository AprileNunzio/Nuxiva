import React, { FormEvent, useState } from 'react';
import { CheckCircle2, ChevronDown, ExternalLink, KeyRound, PlugZap, Trash2, XCircle } from 'lucide-react';
import { SERVICE_URL } from '../../core/parse';
import { useBrainText, useSectionText } from '../../core/i18n';
import { removeProviderKey, testProvider, updateProvider } from '../../core/providersApi';
import { useBrain } from '../../core/useBrainStore';
import { CloudProvider, ProviderChange, ProviderTest } from '../../core/types';
import { Badge, Button, Switch, fieldClass } from '../../ui/primitives';

const SECRET = /^[\x21-\x7e]{8,512}$/;

export const ProviderItem: React.FC<{ readonly provider: CloudProvider }> = ({ provider }) => {
  const { t } = useSectionText('providers');
  const base = useBrainText();
  const { run, action } = useBrain();
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState('');
  const [url, setUrl] = useState(provider.baseUrl);
  const [test, setTest] = useState<ProviderTest | null>(null);
  const busy = action.busy !== null;
  const keyValid = key === '' || SECRET.test(key);
  const urlValid = url === '' || SERVICE_URL.test(url);
  const id = `provider:${provider.id}`;

  const apply = async (task: () => Promise<void>) => {
    const done = await run(id, 'brain_provider_failed', async () => {
      await task();
      return true;
    });
    if (done) {
      setKey('');
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const change: ProviderChange = { ...(key ? { key } : {}), ...(provider.needsUrl || url !== provider.baseUrl ? { base_url: url } : {}) };
    if (Object.keys(change).length > 0 && keyValid && urlValid) {
      void apply(() => updateProvider(provider.id, change));
    }
  };

  const runTest = async () => {
    const outcome = await action.run(`test:${provider.id}`, () => testProvider(provider.id), 'brain_provider_test_failed');
    if (outcome) setTest(outcome);
  };

  const status = provider.configured ? (
    <Badge tone="success">{t('ready')}</Badge>
  ) : provider.hasKey ? (
    <Badge tone="warning">{t('disabled')}</Badge>
  ) : (
    <Badge>{t('not_configured')}</Badge>
  );

  return (
    <li className="border-b border-slate-100 last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500/40 sm:px-5"
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm font-semibold uppercase text-slate-600" aria-hidden="true">
          {provider.name.slice(0, 2)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-slate-900">{provider.name}</span>
          <span className="block truncate text-xs text-slate-500">{provider.hasKey ? t('key_hint', { hint: provider.keyHint || '••••' }) : t('key_missing')}</span>
        </span>
        {status}
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
      {open && (
        <form onSubmit={submit} className="flex flex-col gap-3 bg-slate-50 px-4 py-4 sm:px-5">
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
            {t(provider.keyOptional ? 'key_optional' : 'key')}
            <input
              type="password"
              autoComplete="new-password"
              spellCheck={false}
              maxLength={512}
              value={key}
              placeholder={provider.hasKey ? t('key_replace') : t('key_placeholder')}
              onChange={(e) => setKey(e.target.value.trim())}
              aria-invalid={!keyValid}
              className={`${fieldClass} font-mono text-xs ${keyValid ? '' : 'border-rose-400'}`}
            />
            <span className="font-normal text-slate-500">{t('key_safety')}</span>
          </label>
          {(provider.needsUrl || provider.baseUrl) && (
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
              {t('url')}
              <input
                type="url"
                maxLength={300}
                value={url}
                onChange={(e) => setUrl(e.target.value.trim())}
                aria-invalid={!urlValid}
                className={`${fieldClass} font-mono text-xs ${urlValid ? '' : 'border-rose-400'}`}
              />
            </label>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <Button type="submit" variant="primary" icon={KeyRound} busy={action.busy === id} disabled={busy || !keyValid || !urlValid || (!key && url === provider.baseUrl && !provider.needsUrl)}>
              {base.t('save')}
            </Button>
            <Button icon={PlugZap} busy={action.busy === `test:${provider.id}`} disabled={busy || !provider.configured} onClick={() => void runTest()}>
              {t('test')}
            </Button>
            {provider.hasKey && (
              <Button variant="danger" icon={Trash2} disabled={busy} onClick={() => void apply(() => removeProviderKey(provider.id))}>
                {t('remove_key')}
              </Button>
            )}
            {provider.hasKey && (
              <span className="flex items-center gap-2 text-xs text-slate-600">
                <Switch checked={provider.enabled} label={t('enabled')} disabled={busy} onChange={(enabled) => void apply(() => updateProvider(provider.id, { enabled }))} />
                {t('enabled')}
              </span>
            )}
            {provider.keyUrl && (
              <a href={provider.keyUrl} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-blue-700 hover:underline">
                {t('get_key')}
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </a>
            )}
          </div>
          {test && (
            <p role="status" className={`flex items-start gap-1.5 text-xs ${test.ok ? 'text-emerald-700' : 'text-rose-700'}`}>
              {test.ok ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" /> : <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
              {test.ok ? t('test_ok', { ms: Math.round(test.ms) }) : t('test_failed', { detail: test.detail })}
            </p>
          )}
        </form>
      )}
    </li>
  );
};
