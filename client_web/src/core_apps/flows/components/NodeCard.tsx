import React from 'react';
import { Lock } from 'lucide-react';
import { Pill, inputClass } from '../../shared/kit';
import { FlowNode } from '../types';

interface NodeCardProps {
  readonly node: FlowNode;
  readonly picked: string;
  readonly changed: boolean;
  readonly disabled: boolean;
  readonly t: (key: string) => string;
  readonly onPick: (algorithm: string) => void;
}

export const NodeCard: React.FC<NodeCardProps> = ({ node, picked, changed, disabled, t, onPick }) => {
  const algorithm = node.algorithms.find((item) => item.id === picked) ?? node.algorithms.find((item) => item.default);

  return (
    <li className={`rounded-xl border p-3 ${changed ? 'border-amber-500/50 bg-amber-500/5' : 'border-slate-800 bg-slate-950/60'}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-lg" aria-hidden="true">
          {node.glyph}
        </span>
        <b className="text-sm text-slate-100">{node.label}</b>
        {node.locked ? (
          <Pill tone="rose">
            <Lock className="mr-1 inline h-3 w-3" aria-hidden="true" />
            {t('locked')}
          </Pill>
        ) : null}
        {changed ? <Pill tone="amber">{t('changed')}</Pill> : null}
      </div>
      <p className="mt-1 text-xs text-slate-400">{node.description}</p>
      {node.editable ? (
        <select className={`${inputClass} mt-2`} value={algorithm?.id ?? ''} disabled={disabled} aria-label={node.label} onChange={(event) => onPick(event.target.value)}>
          {node.algorithms
            .filter((item) => item.available)
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
        </select>
      ) : (
        <p className="mt-2 text-xs text-slate-300">{algorithm?.name}</p>
      )}
      {algorithm ? <p className="mt-1 text-xs text-slate-500">{algorithm.description}</p> : null}
    </li>
  );
};
