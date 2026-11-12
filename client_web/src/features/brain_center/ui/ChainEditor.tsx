import React, { useState } from 'react';
import { ArrowDown, ArrowUp, CircleDot, Plus, X } from 'lucide-react';
import { addItem, moveItem, removeItem } from '../core/chain';
import { useBrainText } from '../core/i18n';
import { MAX_CHAIN } from '../core/parse';
import { BrainRef } from '../core/types';
import { ModelPicker } from './ModelPicker';
import { Badge, Button, IconButton } from './primitives';

interface ChainEditorProps {
  readonly chain: readonly string[];
  readonly pool: readonly BrainRef[];
  readonly known: ReadonlyMap<string, BrainRef>;
  readonly onChange: (chain: string[]) => void;
  readonly pickerTitle: string;
}

export const ChainEditor: React.FC<ChainEditorProps> = ({ chain, pool, known, onChange, pickerTitle }) => {
  const { t } = useBrainText();
  const [picking, setPicking] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      {chain.length > 0 && (
        <ol className="flex flex-col gap-1.5" aria-label={t('chain_label')}>
          {chain.map((ref, index) => {
            const info = known.get(ref);
            return (
              <li key={ref} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 py-1 pl-3 pr-1">
                <CircleDot className={`h-3.5 w-3.5 shrink-0 ${info?.available === false ? 'text-rose-500' : 'text-emerald-600'}`} aria-label={t(info?.available === false ? 'unavailable' : 'available')} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-slate-900">{info?.model ?? ref}</span>
                  <span className="block truncate text-[11px] text-slate-500">
                    {index === 0 ? t('chain_primary') : t('chain_backup', { n: index })} · {info?.provider || t(`origin_${info?.origin ?? 'local'}`)}
                  </span>
                </span>
                {index === 0 && <Badge tone="info">{t('chain_first')}</Badge>}
                <IconButton icon={ArrowUp} label={t('move_up')} disabled={index === 0} onClick={() => onChange(moveItem(chain, index, -1))} />
                <IconButton icon={ArrowDown} label={t('move_down')} disabled={index === chain.length - 1} onClick={() => onChange(moveItem(chain, index, 1))} />
                <IconButton icon={X} tone="danger" label={t('remove')} onClick={() => onChange(removeItem(chain, ref))} />
              </li>
            );
          })}
        </ol>
      )}
      <div>
        <Button compact icon={Plus} disabled={chain.length >= MAX_CHAIN} onClick={() => setPicking(true)}>
          {chain.length === 0 ? t('chain_choose') : t('chain_add_backup')}
        </Button>
      </div>
      {picking && (
        <ModelPicker
          title={pickerTitle}
          pool={pool}
          exclude={chain}
          onClose={() => setPicking(false)}
          onPick={(ref) => {
            onChange(addItem(chain, ref));
            setPicking(false);
          }}
        />
      )}
    </div>
  );
};
