import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Plus, Trash2, XCircle } from 'lucide-react';
import { Btn, Panel, Pill, inputClass } from '../../shared/kit';
import { ConnectionForm, HomeConnection, ProbeResult, loadConnection, saveConnection, testConnection } from '../connectionApi';

interface Props {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onSaved: () => void;
}

const MAX_URLS = 6;

export const ConnectionPanel: React.FC<Props> = ({ t, onSaved }) => {
  const [current, setCurrent] = useState<HomeConnection | null>(null);
  const [urls, setUrls] = useState<string[]>(['']);
  const [token, setToken] = useState('');
  const [clearToken, setClearToken] = useState(false);
  const [verifySsl, setVerifySsl] = useState(true);
  const [results, setResults] = useState<readonly ProbeResult[]>([]);
  const [busy, setBusy] = useState<'' | 'test' | 'save'>('');
  const [message, setMessage] = useState<{ readonly tone: 'ok' | 'error'; readonly text: string } | null>(null);

  const apply = useCallback((data: HomeConnection) => {
    setCurrent(data);
    setUrls(data.urls.length > 0 ? [...data.urls] : ['']);
    setVerifySsl(data.verifySsl);
    setToken('');
    setClearToken(false);
  }, []);

  useEffect(() => {
    let alive = true;
    loadConnection()
      .then((data) => alive && apply(data))
      .catch(() => alive && setMessage({ tone: 'error', text: t('conn_load_failed') }));
    return () => {
      alive = false;
    };
  }, [apply, t]);

  const form = (): ConnectionForm => ({ urls, token, clearToken, verifySsl });
  const setUrl = (index: number, value: string) => setUrls((rows) => rows.map((row, i) => (i === index ? value : row)));
  const removeUrl = (index: number) => setUrls((rows) => (rows.length === 1 ? [''] : rows.filter((_, i) => i !== index)));
  const suggest = (value: string) =>
    setUrls((rows) => {
      const base = rows.filter((row) => row.trim());
      return base.includes(value) || base.length >= MAX_URLS ? rows : [...base, value];
    });

  const run = async (kind: 'test' | 'save') => {
    setBusy(kind);
    setMessage(null);
    try {
      if (kind === 'test') {
        const found = await testConnection(form());
        setResults(found);
        setMessage(found.some((item) => item.ok) ? { tone: 'ok', text: t('conn_test_ok') } : { tone: 'error', text: t('conn_test_none') });
      } else {
        apply(await saveConnection(form()));
        setResults([]);
        setMessage({ tone: 'ok', text: t('conn_saved') });
        onSaved();
      }
    } catch (error) {
      setMessage({ tone: 'error', text: error instanceof Error ? error.message : t('conn_failed') });
    } finally {
      setBusy('');
    }
  };

  const tone = current?.status === 'online' ? 'emerald' : current?.status === 'connecting' ? 'amber' : 'rose';
  const suggestions = (current?.suggestions ?? []).filter((item) => !urls.includes(item));

  return (
    <Panel title={t('conn_title')} actions={current ? <Pill tone={tone}>{t(`conn_status_${current.status}`)}</Pill> : null}>
      <div className="space-y-4">
        <p className="text-xs text-slate-400">{t('conn_intro')}</p>
        {current?.status === 'online' ? (
          <p className="text-xs text-emerald-300">{t('conn_active', { url: current.activeUrl, version: current.version })}</p>
        ) : current?.error ? (
          <p className="text-xs text-rose-300">{current.error}</p>
        ) : null}

        <div className="space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('conn_addresses')}</div>
          {urls.map((value, index) => (
            <div key={index} className="flex items-center gap-2">
              <input
                className={inputClass}
                value={value}
                maxLength={200}
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
                placeholder={index === 0 ? t('conn_placeholder_main') : t('conn_placeholder_alt')}
                aria-label={index === 0 ? t('conn_main') : t('conn_alt', { n: index })}
                onChange={(event) => setUrl(index, event.target.value)}
              />
              <Pill tone={index === 0 ? 'cyan' : 'slate'}>{index === 0 ? t('conn_main') : t('conn_alt', { n: index })}</Pill>
              <Btn tone="slate" onClick={() => removeUrl(index)} title={t('conn_remove')}>
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
            </div>
          ))}
          <div className="flex flex-wrap items-center gap-2">
            <Btn tone="slate" disabled={urls.length >= MAX_URLS} onClick={() => setUrls((rows) => [...rows, ''])}>
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              {t('conn_add')}
            </Btn>
            {suggestions.map((item) => (
              <button key={item} type="button" className="rounded-lg border border-cyan-700/50 px-2 py-1 font-mono text-[11px] text-cyan-300 hover:bg-cyan-950/40" onClick={() => suggest(item)}>
                + {item}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-slate-500">{t('conn_addresses_hint')}</p>
        </div>

        <div className="space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('conn_token')}</div>
          <input
            className={inputClass}
            type="password"
            value={token}
            maxLength={2000}
            autoComplete="off"
            spellCheck={false}
            placeholder={current?.tokenSet ? t('conn_token_saved') : t('conn_token_placeholder')}
            aria-label={t('conn_token')}
            onChange={(event) => setToken(event.target.value)}
          />
          {current?.tokenSet ? (
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <input type="checkbox" checked={clearToken} onChange={(event) => setClearToken(event.target.checked)} />
              {t('conn_token_clear')}
            </label>
          ) : null}
          <details className="text-xs text-slate-400">
            <summary className="cursor-pointer text-cyan-300">{t('conn_token_how')}</summary>
            <ol className="mt-2 list-decimal space-y-1 pl-5">
              <li>{t('conn_step_1')}</li>
              <li>{t('conn_step_2')}</li>
              <li>{t('conn_step_3')}</li>
              <li>{t('conn_step_4')}</li>
            </ol>
          </details>
        </div>

        <label className="flex items-start gap-2 text-xs text-slate-300">
          <input className="mt-0.5" type="checkbox" checked={verifySsl} onChange={(event) => setVerifySsl(event.target.checked)} />
          <span>
            {t('conn_verify')}
            <span className="block text-[11px] text-slate-500">{t('conn_verify_hint')}</span>
          </span>
        </label>

        <div className="flex flex-wrap gap-2">
          <Btn tone="slate" busy={busy === 'test'} disabled={busy !== ''} onClick={() => void run('test')}>
            {t('conn_test')}
          </Btn>
          <Btn tone="emerald" busy={busy === 'save'} disabled={busy !== ''} onClick={() => void run('save')}>
            {t('conn_save')}
          </Btn>
        </div>

        {message ? (
          <p className={`text-xs ${message.tone === 'ok' ? 'text-emerald-300' : 'text-rose-300'}`} role="status">
            {message.text}
          </p>
        ) : null}

        {results.length > 0 ? (
          <ul className="space-y-1.5">
            {results.map((item) => (
              <li key={item.url} className="flex items-start gap-2 rounded-xl border border-slate-800 bg-slate-950/60 p-2.5 text-xs">
                {item.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" aria-hidden="true" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" aria-hidden="true" />}
                <div className="min-w-0">
                  <div className="truncate font-mono text-slate-200">{item.url}</div>
                  <div className={item.ok ? 'text-emerald-300' : 'text-rose-300'}>
                    {item.ok ? t('conn_result_ok', { version: item.version, name: item.name || '—', ms: item.ms }) : item.message || t(`conn_state_${item.state}`)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </Panel>
  );
};
