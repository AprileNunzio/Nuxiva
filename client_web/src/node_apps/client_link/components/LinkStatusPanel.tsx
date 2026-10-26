import React, { useState } from 'react';
import { Activity, Unlink } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { Panel } from '../../shared/components/ModuleFrame';
import { LinkNode, METRICS, unpairNode } from '../data/linkApi';
import { LinksHandle, useNow } from '../hooks/useLinks';
import { duration, relativeTime, useLinkI18n } from '../scope';

const tone = (value: number, max: number): string => {
  const ratio = value / max;
  return ratio > 0.85 ? 'bg-rose-500' : ratio > 0.65 ? 'bg-amber-400' : 'bg-cyan-400';
};

export const LinkStatusPanel: React.FC<{ readonly node: LinkNode; readonly handle: LinksHandle }> = ({ node, handle }) => {
  const { t, lang } = useLinkI18n();
  const now = useNow();
  const [confirm, setConfirm] = useState(false);
  const facts: readonly (readonly [string, string | null])[] = [
    ['fact_ip', node.ip],
    ['fact_hostname', node.hostname],
    ['fact_version', node.version],
    ['fact_room', node.room],
    ['fact_paired', node.pairedAt ? relativeTime(node.pairedAt, now, lang) : null],
    ['fact_uptime', node.uptime !== null ? duration(node.uptime) : null],
  ];

  return (
    <>
      <Panel title={t('status_title')}>
        <div className="flex items-center gap-4">
          <span className="relative flex h-14 w-14 shrink-0 items-center justify-center">
            {node.online && <span className="absolute inset-0 animate-ping rounded-full border border-emerald-400/40" aria-hidden="true" />}
            <span
              className={`relative flex h-14 w-14 items-center justify-center rounded-full border ${
                node.online ? 'border-emerald-400/60 bg-emerald-400/10' : 'border-slate-700 bg-slate-900'
              }`}
            >
              <Activity className={`h-6 w-6 ${node.online ? 'text-emerald-200' : 'text-slate-500'}`} aria-hidden="true" />
            </span>
          </span>
          <div className="min-w-0">
            <p className={`text-lg font-bold ${node.online ? 'text-emerald-200' : 'text-slate-300'}`}>{t(node.online ? 'state_online' : 'state_offline')}</p>
            <p className="text-xs text-slate-400">
              {node.lastSeen ? t('last_heartbeat', { when: relativeTime(node.lastSeen, now, lang) }) : t('never_seen')}
            </p>
          </div>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {facts.map(([key, value]) => (
            <div key={key} className="min-w-0 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2">
              <dt className="text-[10px] uppercase tracking-wider text-slate-500">{t(key)}</dt>
              <dd className="truncate font-mono text-xs text-slate-200">{value ?? '—'}</dd>
            </div>
          ))}
        </dl>
        {node.queued.length > 0 && <p className="mt-3 text-xs text-amber-200">{t('queued', { list: node.queued.join(', ') })}</p>}
      </Panel>
      <Panel title={t('metrics_title')}>
        {METRICS.every((key) => node.metrics[key] === undefined) ? (
          <p className="text-sm text-slate-500">{t('metrics_empty')}</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {METRICS.map((key) => {
              const value = node.metrics[key];
              if (value === undefined) {
                return null;
              }
              return (
                <div key={key}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-slate-400">{t(`metric_${key}`)}</span>
                    <span className="font-mono text-slate-100">
                      {value}
                      {key === 'temp' ? ' °C' : '%'}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className={`h-full rounded-full ${tone(value, 100)}`} style={{ width: `${Math.min(100, value)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {node.capabilities.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {node.capabilities.map((capability) => (
              <span key={capability} className="rounded-full border border-slate-700 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                {capability}
              </span>
            ))}
          </div>
        )}
      </Panel>
      <Panel title={t('security_title')}>
        <p className="text-xs text-slate-400">{t('unpair_hint')}</p>
        <button
          type="button"
          disabled={handle.busy !== null}
          onClick={() => setConfirm(true)}
          className="mt-3 flex items-center gap-2 rounded-xl border border-rose-400/50 bg-rose-400/10 px-4 py-2 text-sm font-semibold text-rose-200 transition hover:bg-rose-400/20 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
        >
          <Unlink className="h-4 w-4" aria-hidden="true" />
          {t('unpair')}
        </button>
      </Panel>
      {confirm && (
        <ConfirmDialog
          title={t('unpair_title')}
          body={t('unpair_body', { name: node.name })}
          confirmLabel={t('unpair')}
          cancelLabel={t('cancel')}
          pending={handle.busy === 'unpair'}
          tone="danger"
          onConfirm={() => void handle.run('unpair', () => unpairNode(node.id), 'node_unpair_failed').then(() => setConfirm(false))}
          onCancel={() => setConfirm(false)}
        />
      )}
    </>
  );
};
