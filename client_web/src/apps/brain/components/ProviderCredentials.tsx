import React, { useEffect, useState } from 'react';
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, PlugZap, Save, XCircle } from 'lucide-react';
import { LlmProvider } from '../types';
import { sendJson } from '../../shared/http';

export interface CredentialsDraft {
  readonly key?: string;
  readonly baseUrl?: string;
}

interface Props {
  readonly provider: LlmProvider;
  readonly onSave: (providerId: string, draft: CredentialsDraft) => Promise<boolean>;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

type Outcome = { readonly ok: boolean; readonly text: string } | null;

const remoteId = (id: string): string => (id === 'google' ? 'gemini' : id);
const ENDPOINT = /^https?:\/\/[^\s/$.?#][^\s]*$/i;

export const ProviderCredentials: React.FC<Props> = ({ provider, onSave, t }) => {
  const [key, setKey] = useState('');
  const [endpoint, setEndpoint] = useState(provider.endpointUrl ?? '');
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState<'save' | 'test' | null>(null);
  const [outcome, setOutcome] = useState<Outcome>(null);

  useEffect(() => {
    setKey('');
    setEndpoint(provider.endpointUrl ?? '');
    setOutcome(null);
    setReveal(false);
  }, [provider.id, provider.endpointUrl]);

  const endpointValid = endpoint.trim() === '' || ENDPOINT.test(endpoint.trim());
  const keyChanged = key.trim() !== '';
  const endpointChanged = endpoint.trim() !== (provider.endpointUrl ?? '');
  const canSave = busy === null && endpointValid && (keyChanged || endpointChanged);

  const save = async () => {
    setBusy('save');
    setOutcome(null);
    const ok = await onSave(provider.id, {
      ...(keyChanged ? { key: key.trim() } : {}),
      ...(endpointChanged ? { baseUrl: endpoint.trim() } : {}),
    });
    setBusy(null);
    if (ok) setKey('');
    setOutcome({ ok, text: t(ok ? 'credentials_saved' : 'credentials_save_failed') });
  };

  const test = async () => {
    setBusy('test');
    setOutcome(null);
    try {
      const model = provider.models[0]?.name ?? '';
      const result = await sendJson<{ ok?: boolean; error?: string; ms?: number }>(`/api/cloud/${remoteId(provider.id)}/test`, 'POST', model ? { model } : {});
      setOutcome({ ok: result.ok === true, text: result.ok === true ? t('credentials_test_ok') : `${t('credentials_test_failed')} ${String(result.error ?? '').slice(0, 160)}`.trim() });
    } catch {
      setOutcome({ ok: false, text: t('credentials_test_failed') });
    } finally {
      setBusy(null);
    }
  };

  return (
    <form
      className="space-y-4 rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 via-white to-white p-4 sm:p-5 shadow-xs"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSave) void save();
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
          <KeyRound className="h-4 w-4 text-amber-700" aria-hidden="true" />
          {t('credentials_for')} {provider.name}
        </h3>
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${provider.isConfigured ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : 'border-slate-300 text-slate-600'}`}>
          {t(provider.isConfigured ? 'credentials_configured' : 'credentials_missing')}
        </span>
      </div>
      <label className="block space-y-1.5">
        <span className="text-xs font-semibold text-slate-700">{t('credentials_key')}</span>
        <span className="relative block">
          <input
            type={reveal ? 'text' : 'password'}
            autoComplete="off"
            spellCheck={false}
            maxLength={600}
            value={key}
            onChange={(event) => {
              setKey(event.target.value);
              setOutcome(null);
            }}
            placeholder={provider.isConfigured ? t('credentials_key_keep') : t('credentials_key_placeholder')}
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-3.5 pr-11 font-mono text-sm text-slate-900 outline-none transition placeholder:text-slate-500 focus:border-amber-300 focus-visible:ring-2 focus-visible:ring-amber-300"
          />
          <button
            type="button"
            onClick={() => setReveal((value) => !value)}
            aria-label={t(reveal ? 'credentials_hide' : 'credentials_show')}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-600 transition hover:text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300"
          >
            {reveal ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
          </button>
        </span>
      </label>
      <label className="block space-y-1.5">
        <span className="text-xs font-semibold text-slate-700">{t('credentials_endpoint')}</span>
        <input
          type="url"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          maxLength={300}
          value={endpoint}
          onChange={(event) => {
            setEndpoint(event.target.value);
            setOutcome(null);
          }}
          placeholder={provider.defaultEndpoint || 'https://…'}
          aria-invalid={!endpointValid}
          className={`w-full rounded-xl border bg-white px-3.5 py-2.5 font-mono text-sm text-slate-900 outline-none transition placeholder:text-slate-500 focus-visible:ring-2 ${
            endpointValid ? 'border-slate-300 focus:border-amber-300 focus-visible:ring-amber-300' : 'border-rose-300 focus-visible:ring-rose-300'
          }`}
        />
        <span className="block text-[11px] text-slate-500">{t(endpointValid ? 'credentials_endpoint_hint' : 'credentials_endpoint_invalid')}</span>
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={!canSave}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 px-4 py-2 text-sm font-bold text-white shadow-xs transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-200"
        >
          {busy === 'save' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
          {t('credentials_save')}
        </button>
        <button
          type="button"
          disabled={busy !== null || !provider.isConfigured}
          onClick={() => void test()}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-900 transition hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300"
        >
          {busy === 'test' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <PlugZap className="h-4 w-4" aria-hidden="true" />}
          {t('credentials_test')}
        </button>
      </div>
      {outcome && (
        <p role="status" className={`flex items-start gap-2 rounded-xl border px-3 py-2 text-xs font-semibold ${outcome.ok ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : 'border-rose-300 bg-rose-50 text-rose-800'}`}>
          {outcome.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
          <span>{outcome.text}</span>
        </p>
      )}
    </form>
  );
};
