import React from 'react';
import { Cpu } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { EdgeTarget, LinkNode } from '../data/linkApi';
import { useLinkI18n } from '../scope';

const TARGET_TONE: Readonly<Record<EdgeTarget, string>> = {
  edge: 'border-emerald-400/50 bg-emerald-400/10 text-emerald-200',
  server: 'border-cyan-400/40 bg-cyan-400/5 text-cyan-200',
  unavailable: 'border-slate-700 bg-slate-900 text-slate-500',
};

export const EdgePanel: React.FC<{ readonly node: LinkNode }> = ({ node }) => {
  const { t } = useLinkI18n();
  if (!node.soc && node.accelerators.length === 0 && node.offload.length === 0) {
    return null;
  }
  return (
    <Panel title={t('edge_title')}>
      {node.soc && (
        <p className="flex items-center gap-2 text-sm text-slate-200">
          <Cpu className="h-4 w-4 shrink-0 text-cyan-300" aria-hidden="true" />
          <span className="truncate">{node.soc}</span>
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {node.accelerators.length === 0 ? (
          <span className="text-xs text-slate-500">{t('edge_no_accelerator')}</span>
        ) : (
          node.accelerators.map((acc) => (
            <span
              key={acc.id}
              title={t(acc.ready ? 'edge_ready' : 'edge_missing_runtime')}
              className={`rounded-full border px-2 py-0.5 text-[11px] ${
                acc.ready ? 'border-emerald-400/50 text-emerald-200' : 'border-amber-400/50 text-amber-200'
              }`}
            >
              {acc.vendor} · {acc.kind.toUpperCase()} · {t(acc.ready ? 'edge_ready' : 'edge_missing_runtime')}
            </span>
          ))
        )}
      </div>
      {node.offload.length > 0 && (
        <ul className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {node.offload.map((step) => (
            <li key={step.task} className={`flex min-w-0 items-center justify-between gap-2 rounded-xl border px-3 py-2 ${TARGET_TONE[step.target]}`}>
              <span className="truncate text-xs">{t(`edge_task_${step.task}`)}</span>
              <span className="shrink-0 font-mono text-[11px]">
                {step.target === 'edge' ? t('edge_target_edge', { backend: step.backend ?? 'cpu' }) : t(`edge_target_${step.target}`)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
};
