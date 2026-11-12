import React, { FormEvent, useEffect, useState } from 'react';
import { CheckCircle2, PlugZap, Plus, Server, Trash2, XCircle } from 'lucide-react';
import { ConfirmDialog } from '../../../../shared/ui/ConfirmDialog';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { useBrainText, useSectionText } from '../../core/i18n';
import { SERVICE_URL } from '../../core/parse';
import { addServer, fetchServers, removeServer, testServer } from '../../core/providersApi';
import { useBrain } from '../../core/useBrainStore';
import { NewServer, ServerFlavor } from '../../core/types';
import { Badge, Button, Card, FLUID, IconButton, Row, fieldClass } from '../../ui/primitives';

const EMPTY: NewServer = { name: '', flavor: 'openai', url: '', key: '' };
const FLAVORS: readonly ServerFlavor[] = ['openai', 'ollama'];

export const ServersCard: React.FC = () => {
  const { t } = useSectionText('providers');
  const base = useBrainText();
  const { run, action, version } = useBrain();
  const servers = usePolled(fetchServers, 'brain_servers_unavailable', true, 30000);
  const [draft, setDraft] = useState<NewServer>(EMPTY);
  const [probe, setProbe] = useState<{ ok: boolean; count: number } | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const { refresh } = servers;
  useEffect(() => {
    if (version > 0) refresh();
  }, [version, refresh]);

  const busy = action.busy !== null;
  const valid = draft.name.trim() !== '' && SERVICE_URL.test(draft.url.trim());
  const update = (patch: Partial<NewServer>) => {
    setDraft({ ...draft, ...patch });
    setProbe(null);
  };

  const tryServer = async () => {
    const outcome = await action.run('server:test', () => testServer(draft), 'brain_server_failed');
    if (outcome) setProbe(outcome);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const done = await run('server:add', 'brain_server_failed', async () => {
      await addServer(draft);
      return true;
    });
    if (done) {
      setDraft(EMPTY);
      setProbe(null);
    }
  };

  const confirmRemove = async () => {
    if (!removing) return;
    await run(`server:remove:${removing}`, 'brain_server_failed', async () => {
      await removeServer(removing);
      return true;
    });
    setRemoving(null);
  };

  return (
    <Card title={t('servers_title')} description={t('servers_hint')} flush>
      <div className={`grid ${FLUID.md}`}>
      {(servers.data ?? []).map((server) => (
        <Row
          key={server.id}
          icon={Server}
          title={<>{server.name}<Badge tone={server.online ? 'success' : 'danger'}>{t(server.online ? 'online' : 'offline')}</Badge></>}
          description={`${t(`flavor_${server.flavor}`)} · ${server.url} · ${t('server_models', { count: server.models.length })}`}
          trailing={<IconButton icon={Trash2} tone="danger" label={t('server_remove')} disabled={busy} onClick={() => setRemoving(server.id)} />}
        />
      ))}
      </div>
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3 bg-slate-50 px-4 py-4 sm:px-5">
        <p className="text-sm font-medium text-slate-900">{t('add_title')}</p>
        <p className="-mt-2 text-xs text-slate-500">{t('add_hint')}</p>
        <div className={`grid gap-3 ${FLUID.xs}`}>
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
            {t('server_name')}
            <input value={draft.name} maxLength={40} onChange={(e) => update({ name: e.target.value })} className={fieldClass} />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
            {t('server_flavor')}
            <select value={draft.flavor} onChange={(e) => update({ flavor: FLAVORS.find((f) => f === e.target.value) ?? 'openai' })} className={fieldClass}>
              {FLAVORS.map((flavor) => (
                <option key={flavor} value={flavor}>{t(`flavor_${flavor}`)}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
            {t('server_url')}
            <input type="url" inputMode="url" value={draft.url} maxLength={300} placeholder={t(`url_example_${draft.flavor}`)} onChange={(e) => update({ url: e.target.value.trim() })} className={`${fieldClass} font-mono text-xs`} />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
            {t('key_optional')}
            <input type="password" autoComplete="new-password" spellCheck={false} value={draft.key} maxLength={512} onChange={(e) => update({ key: e.target.value.trim() })} className={`${fieldClass} font-mono text-xs`} />
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button icon={PlugZap} busy={action.busy === 'server:test'} disabled={busy || !valid} onClick={() => void tryServer()}>
            {t('test')}
          </Button>
          <Button type="submit" variant="primary" icon={Plus} busy={action.busy === 'server:add'} disabled={busy || !valid}>
            {t('server_add')}
          </Button>
          {probe && (
            <span role="status" className={`flex items-center gap-1.5 text-xs ${probe.ok ? 'text-emerald-700' : 'text-rose-700'}`}>
              {probe.ok ? <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> : <XCircle className="h-3.5 w-3.5" aria-hidden="true" />}
              {probe.ok ? t('probe_ok', { count: probe.count }) : t('probe_failed')}
            </span>
          )}
        </div>
      </form>
      {removing && (
        <ConfirmDialog
          title={t('server_remove_title')}
          body={t('server_remove_body')}
          confirmLabel={t('server_remove')}
          cancelLabel={base.t('cancel')}
          pending={action.busy === `server:remove:${removing}`}
          tone="danger"
          onConfirm={() => void confirmRemove()}
          onCancel={() => setRemoving(null)}
        />
      )}
    </Card>
  );
};
