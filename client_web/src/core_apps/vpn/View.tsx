import React, { useState } from 'react';
import { Copy, Network, Plug, PlugZap, Trash2, UserPlus } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { addPeer, connectProfile, deleteProfile, disconnectProfile } from './api';
import { CreateProfile } from './components/CreateProfile';
import { PeerResult, VpnOverview } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/vpn');
  const { data, error, loading, reload } = useResource<VpnOverview>('/api/vpn', 6000);
  const { busy, run } = useAction(reload);
  const [peerName, setPeerName] = useState('');
  const [issued, setIssued] = useState<PeerResult | null>(null);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const connected = data.profiles.filter((profile) => profile.status.connected).length;

  const issue = async (id: string) => {
    if (!peerName.trim()) {
      return;
    }
    const out = await run(() => addPeer(id, peerName.trim()), 'vpn_peer_failed');
    if (out) {
      setIssued(out);
      setPeerName('');
    }
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_profiles')} value={data.profiles.length} />
        <Stat label={t('stat_connected')} value={connected} tone="emerald" />
        <Stat label={t('stat_tools')} value={`${Object.values(data.tools).filter(Boolean).length}/${Object.keys(data.tools).length}`} tone="amber" />
      </StatRow>
      {data.guard_error ? <Pill tone="rose">{data.guard_error}</Pill> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel title={t('profiles_title')} icon={<Network className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
          {data.profiles.length === 0 ? (
            <Empty>{t('profiles_empty')}</Empty>
          ) : (
            <List>
              {data.profiles.map((profile) => (
                <Row
                  key={profile.id}
                  actions={
                    <>
                      {profile.status.connected ? (
                        <Btn tone="amber" busy={busy} onClick={() => void run(() => disconnectProfile(profile.id), 'vpn_disconnect_failed')}>
                          <PlugZap className="h-3.5 w-3.5" aria-hidden="true" />
                          {t('disconnect')}
                        </Btn>
                      ) : (
                        <Btn tone="emerald" busy={busy} onClick={() => void run(() => connectProfile(profile.id), 'vpn_connect_failed')}>
                          <Plug className="h-3.5 w-3.5" aria-hidden="true" />
                          {t('connect')}
                        </Btn>
                      )}
                      <Btn tone="rose" busy={busy} onClick={() => void run(() => deleteProfile(profile.id), 'vpn_delete_failed')} title={t('delete')}>
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                    </>
                  }
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <b>{profile.name}</b>
                    <Pill>{profile.kind}</Pill>
                    <Pill tone={profile.role === 'server' ? 'purple' : 'slate'}>{profile.role}</Pill>
                    <Pill tone={profile.status.connected ? 'emerald' : 'slate'}>{profile.status.connected ? t('state_connected') : t('state_disconnected')}</Pill>
                  </div>
                  {profile.status.error ? <p className="mt-1 text-xs text-rose-300">{profile.status.error}</p> : null}
                  {profile.kind === 'wireguard' && profile.role === 'server' ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <input className={`${inputClass} max-w-xs`} value={peerName} maxLength={32} onChange={(event) => setPeerName(event.target.value)} placeholder={t('peer_placeholder')} aria-label={t('peer_placeholder')} />
                      <Btn busy={busy} onClick={() => void issue(profile.id)}>
                        <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
                        {t('peer_add')}
                      </Btn>
                    </div>
                  ) : null}
                </Row>
              ))}
            </List>
          )}
          {issued ? (
            <div className="mt-4 rounded-xl border border-emerald-500/40 bg-emerald-500/5 p-3">
              <div className="mb-2 flex items-center justify-between gap-2 text-xs font-semibold text-emerald-200">
                <span>{t('peer_ready', { name: issued.peer.name })}</span>
                <Btn tone="slate" onClick={() => void navigator.clipboard.writeText(issued.config)}>
                  <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                  {t('copy')}
                </Btn>
              </div>
              <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-all font-mono text-[11px] text-slate-300">{issued.config}</pre>
              <p className="mt-2 text-[11px] text-amber-300">{t('peer_once')}</p>
            </div>
          ) : null}
        </Panel>
        <CreateProfile tools={data.tools} busy={busy} t={t} run={run} />
      </div>
    </AppFrame>
  );
};

export default View;
