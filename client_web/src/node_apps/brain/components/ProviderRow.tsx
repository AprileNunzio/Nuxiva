import React, { FormEvent, useState } from 'react';
import { CheckCircle2, ChevronDown, ExternalLink, KeyRound, Loader2, PlugZap, XCircle } from 'lucide-react';
import { ActionHandle } from '../../shared/hooks/useAction';
import { CloudProvider, CloudTest, ProviderChange, testProvider, updateProvider } from '../data/cloudApi';
import { chipButton, fieldClass, useBrainI18n } from '../scope';

const SECRET = /^[\x21-\x7e]{8,512}$/;
const URL_RE = /^https?:\/\/[A-Za-z0-9.\-:[\]]+(\/[A-Za-z0-9._~\-/%]*)?$/;

interface ProviderRowProps {
  readonly provider: CloudProvider;
  readonly action: ActionHandle;
  readonly onChanged: () => void;
}

export const ProviderRow: React.FC<ProviderRowProps> = ({ provider, action, onChanged }) => {
  const { t } = useBrainI18n();
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState('');
  const [url, setUrl] = useState(provider.baseUrl);
  const [test, setTest] = useState<CloudTest | null>(null);
  const busy = action.busy !== null;
  const keyValid = key === '' || SECRET.test(key);
  const urlValid = url === '' || URL_RE.test(url);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const change: ProviderChange = { ...(key ? { key } : {}), ...(provider.needsUrl || url !== provider.baseUrl ? { base_url: url } : {}) };
    if (Object.keys(change).length && keyValid && urlValid) {
      const saved = await action.run(`cloud:${provider.id}`, () => updateProvider(provider.id, change), 'node_brain_cloud_failed');
      if (saved !== undefined) {
        setKey('');
        onChanged();
      }
    }
  };

  const toggle = () =>
    void action.run(`cloud:${provider.id}`, () => updateProvider(provider.id, { enabled: !provider.enabled }), 'node_brain_cloud_failed').then(onChanged);

  const removeKey = () => void action.run(`cloud:${provider.id}`, () => updateProvider(provider.id, { key: '' }), 'node_brain_cloud_failed').then(onChanged);

  const runTest = async () => {
    const outcome = await action.run(`test:${provider.id}`, () => testProvider(provider.id), 'node_brain_cloud_test_failed');
    if (outcome) {
      setTest(outcome);
    }
  };

  return (
    <li className={`rounded-xl border ${provider.configured ? 'border-emerald-400/30' : 'border-slate-800/80'} bg-slate-950/40`}>
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="flex w-full items-center gap-3 px-3 py-2.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400">
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${provider.configured ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]' : 'bg-slate-600'}`} aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm text-slate-100">{provider.name}</span>
          <span className="block truncate text-[11px] text-slate-500">
            {provider.configured ? t('cloud_ready', { hint: provider.keyHint || '—' }) : t(provider.hasKey ? 'cloud_disabled' : 'cloud_no_key')}
          </span>
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-500 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
      {open && (
        <form onSubmit={submit} className="flex flex-col gap-2 border-t border-slate-800/80 px-3 py-3">
          {provider.notes && <p className="text-[11px] text-slate-500">{provider.notes}</p>}
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t(provider.keyOptional ? 'cloud_key_optional' : 'cloud_key')}
            <input
              type="password"
              autoComplete="off"
              spellCheck={false}
              maxLength={512}
              value={key}
              placeholder={provider.hasKey ? provider.keyHint : ''}
              onChange={(event) => setKey(event.target.value.trim())}
              className={`${fieldClass} font-mono text-xs ${keyValid ? '' : 'border-rose-400/70'}`}
            />
          </label>
          {(provider.needsUrl || provider.baseUrl) && (
            <label className="flex flex-col gap-1 text-xs text-slate-400">
              {t('cloud_url')}
              <input
                type="url"
                maxLength={300}
                value={url}
                onChange={(event) => setUrl(event.target.value.trim())}
                className={`${fieldClass} font-mono text-xs ${urlValid ? '' : 'border-rose-400/70'}`}
              />
            </label>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <button type="submit" disabled={busy || !keyValid || !urlValid || (!key && url === provider.baseUrl && !provider.needsUrl)} className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/20`}>
              {action.busy === `cloud:${provider.id}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />}
              {t('cloud_save')}
            </button>
            <button type="button" disabled={busy || !provider.configured} onClick={() => void runTest()} className={`${chipButton} border-slate-700 text-slate-200 hover:border-cyan-400/60`}>
              {action.busy === `test:${provider.id}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <PlugZap className="h-3.5 w-3.5" aria-hidden="true" />}
              {t('cloud_test')}
            </button>
            {provider.hasKey && (
              <button type="button" role="switch" aria-checked={provider.enabled} disabled={busy} onClick={toggle} className={`${chipButton} border-slate-700 text-slate-300`}>
                {t(provider.enabled ? 'cloud_disable' : 'cloud_enable')}
              </button>
            )}
            {provider.hasKey && (
              <button type="button" disabled={busy} onClick={removeKey} className={`${chipButton} border-slate-700 text-slate-400 hover:border-rose-400/60 hover:text-rose-200`}>
                {t('cloud_remove_key')}
              </button>
            )}
            {provider.keyUrl && (
              <a href={provider.keyUrl} target="_blank" rel="noopener noreferrer" className="ml-auto flex items-center gap-1 text-xs text-cyan-300 hover:underline">
                {t('cloud_get_key')}
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </a>
            )}
          </div>
          {test && (
            <p role="status" className={`flex items-start gap-1.5 text-xs ${test.ok ? 'text-emerald-300' : 'text-rose-300'}`}>
              {test.ok ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" /> : <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
              {test.ok ? t('cloud_test_ok', { ms: test.ms, reply: test.detail }) : test.detail}
            </p>
          )}
        </form>
      )}
    </li>
  );
};
