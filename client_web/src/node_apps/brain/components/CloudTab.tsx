import React, { FormEvent, useState } from 'react';
import { Loader2, PlugZap, Plus, Server, Trash2 } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { Panel } from '../../shared/components/ModuleFrame';
import { ActionHandle, usePolled } from '../../shared/hooks/useAction';
import { NewServer, addServer, fetchProviders, fetchServers, removeServer, testServer } from '../data/cloudApi';
import { chipButton, fieldClass, useBrainI18n } from '../scope';
import { ProviderRow } from './ProviderRow';

const EMPTY: NewServer = { name: '', flavor: 'ollama', url: '', key: '' };

export const CloudTab: React.FC<{ readonly action: ActionHandle; readonly onChanged: () => void }> = ({ action, onChanged }) => {
  const { t } = useBrainI18n();
  const providers = usePolled(fetchProviders, 'node_brain_cloud_unavailable', true);
  const servers = usePolled(fetchServers, 'node_brain_servers_unavailable', true, 30000);
  const [draft, setDraft] = useState<NewServer>(EMPTY);
  const [probe, setProbe] = useState<{ ok: boolean; models: string[]; error: string } | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const busy = action.busy !== null;

  const changed = () => {
    providers.refresh();
    servers.refresh();
    onChanged();
  };

  const tryServer = async () => {
    const outcome = await action.run('server:test', () => testServer(draft), 'node_brain_server_failed');
    if (outcome) {
      setProbe(outcome);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const done = await action.run('server:add', async () => {
      await addServer(draft);
      return true;
    }, 'node_brain_server_failed');
    if (done) {
      setDraft(EMPTY);
      setProbe(null);
      changed();
    }
  };

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title={t('cloud_title')}>
        <p className="mb-3 text-xs text-slate-500">{t('cloud_hint')}</p>
        {providers.data === null ? (
          <Loader2 className="h-4 w-4 animate-spin text-cyan-300" aria-label={t('loading')} />
        ) : (
          <ul className="flex flex-col gap-2">
            {providers.data.map((provider) => (
              <ProviderRow key={provider.id} provider={provider} action={action} onChanged={changed} />
            ))}
          </ul>
        )}
      </Panel>
      <Panel title={t('servers_title')}>
        <p className="mb-3 text-xs text-slate-500">{t('servers_hint')}</p>
        {servers.data && servers.data.length > 0 && (
          <ul className="mb-4 flex flex-col gap-2">
            {servers.data.map((server) => (
              <li key={server.id} className="flex items-start gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2.5">
                <Server className={`mt-0.5 h-4 w-4 shrink-0 ${server.online ? 'text-emerald-300' : 'text-rose-300'}`} aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-slate-100">{server.name}</span>
                  <span className="block truncate font-mono text-[11px] text-slate-500">
                    {server.flavor} · {server.url}
                  </span>
                  <span className={`block truncate text-[11px] ${server.online ? 'text-slate-400' : 'text-rose-300'}`}>
                    {server.online ? t('server_models', { count: server.models.length }) : server.error}
                  </span>
                </span>
                <button type="button" aria-label={t('server_remove')} disabled={busy} onClick={() => setRemoving(server.id)} className="rounded p-1 text-slate-500 hover:text-rose-300 disabled:opacity-50">
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={submit} className="grid gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t('server_name')}
            <input maxLength={40} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} className={fieldClass} />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t('server_flavor')}
            <select value={draft.flavor} onChange={(event) => setDraft({ ...draft, flavor: event.target.value === 'openai' ? 'openai' : 'ollama' })} className={fieldClass}>
              <option value="ollama">Ollama</option>
              <option value="openai">{t('server_openai')}</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
            {t('server_url')}
            <input required maxLength={300} placeholder="192.168.1.10:11434" value={draft.url} onChange={(event) => setDraft({ ...draft, url: event.target.value.trim() })} className={`${fieldClass} font-mono text-xs`} />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-400 sm:col-span-2">
            {t('server_key')}
            <input type="password" autoComplete="off" maxLength={512} value={draft.key} onChange={(event) => setDraft({ ...draft, key: event.target.value.trim() })} className={`${fieldClass} font-mono text-xs`} />
          </label>
          {probe && (
            <p role="status" className={`text-xs sm:col-span-2 ${probe.ok ? 'text-emerald-300' : 'text-rose-300'}`}>
              {probe.ok ? t('server_probe_ok', { count: probe.models.length }) : probe.error}
            </p>
          )}
          <div className="flex gap-2 sm:col-span-2">
            <button type="button" disabled={busy || !draft.url} onClick={() => void tryServer()} className={`${chipButton} border-slate-700 text-slate-200 hover:border-cyan-400/60`}>
              {action.busy === 'server:test' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <PlugZap className="h-3.5 w-3.5" aria-hidden="true" />}
              {t('server_test')}
            </button>
            <button type="submit" disabled={busy || !probe?.ok} className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/20`}>
              {action.busy === 'server:add' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Plus className="h-3.5 w-3.5" aria-hidden="true" />}
              {t('server_add')}
            </button>
          </div>
        </form>
      </Panel>
      {removing && (
        <ConfirmDialog
          title={t('server_remove_title')}
          body={t('server_remove_body')}
          confirmLabel={t('server_remove')}
          cancelLabel={t('cancel')}
          pending={busy}
          tone="danger"
          onConfirm={() => void action.run('server:remove', () => removeServer(removing), 'node_brain_server_failed').then(() => {
            setRemoving(null);
            changed();
          })}
          onCancel={() => setRemoving(null)}
        />
      )}
    </div>
  );
};
