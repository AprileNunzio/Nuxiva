import React, { useState } from 'react';
import { Download, Network } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { updateAllNodes, updateNode } from '../api';
import { RolloutNode } from '../types';
import { buttonClass, formatDateTime, panelClass, useUpdaterI18n } from '../scope';

interface RolloutPanelProps {
  readonly nodes: readonly RolloutNode[];
  readonly onChanged: () => void;
}

type Target = { readonly kind: 'all' } | { readonly kind: 'one'; readonly node: RolloutNode };

export const RolloutPanel: React.FC<RolloutPanelProps> = ({ nodes, onChanged }) => {
  const { t, lang } = useUpdaterI18n();
  const [target, setTarget] = useState<Target | null>(null);
  const [pending, setPending] = useState(false);

  const confirm = async () => {
    if (!target) {
      return;
    }
    setPending(true);
    try {
      await (target.kind === 'all' ? updateAllNodes() : updateNode(target.node.id));
      onChanged();
    } catch (cause) {
      reportError('updater_nodes_failed', cause);
    } finally {
      setPending(false);
      setTarget(null);
    }
  };

  return (
    <section className={panelClass} aria-labelledby="upd-rollout-title">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="upd-rollout-title" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
          <Network className="h-4 w-4 text-cyan-700" aria-hidden="true" />
          {t('rollout_title', { count: nodes.length })}
        </h2>
        <button
          type="button"
          onClick={() => setTarget({ kind: 'all' })}
          disabled={nodes.length === 0}
          className={`${buttonClass} border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 hover:border-cyan-300`}
        >
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          {t('rollout_all')}
        </button>
      </div>
      {nodes.length === 0 ? (
        <p className="text-sm text-slate-500">{t('rollout_empty')}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {nodes.map((node) => (
            <li key={node.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <span className={`h-2 w-2 rounded-full ${node.online ? 'bg-emerald-400' : 'bg-slate-600'}`} aria-hidden="true" />
                  <span className="truncate">{node.name}</span>
                </p>
                <p className="text-xs text-slate-500">
                  {[
                    node.version ? t('rollout_version', { version: node.version }) : t('rollout_version_unknown'),
                    node.online ? t('rollout_online') : t('rollout_offline', { when: formatDateTime(node.last_seen, lang) ?? t('never') }),
                    node.room,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </p>
              </div>
              {node.update_queued ? (
                <span className="rounded-full border border-amber-300 px-2.5 py-1 text-[11px] font-semibold text-amber-800">{t('rollout_queued')}</span>
              ) : (
                <button
                  type="button"
                  onClick={() => setTarget({ kind: 'one', node })}
                  className={`${buttonClass} border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:border-cyan-300`}
                >
                  {t('rollout_one')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {target && (
        <ConfirmDialog
          title={target.kind === 'all' ? t('confirm_nodes_all_title', { count: nodes.length }) : t('confirm_node_title', { name: target.node.name })}
          body={t('confirm_nodes_body')}
          confirmLabel={t('rollout_confirm')}
          cancelLabel={t('cancel')}
          pending={pending}
          tone="neutral"
          onConfirm={confirm}
          onCancel={() => setTarget(null)}
        />
      )}
    </section>
  );
};
