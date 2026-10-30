import React, { useEffect, useState } from 'react';
import { ChevronDown, Save } from 'lucide-react';
import { sameChain } from '../../core/chain';
import { saveFunction } from '../../core/functionsApi';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { AssignmentMode, BrainRef, FunctionRow } from '../../core/types';
import { ChainEditor } from '../../ui/ChainEditor';
import { Badge, Button, fieldClass } from '../../ui/primitives';

const MODES: readonly AssignmentMode[] = ['inherit', 'first', 'only'];

interface FunctionItemProps {
  readonly row: FunctionRow;
  readonly label: string;
  readonly known: ReadonlyMap<string, BrainRef>;
  readonly onSaved: (rows: FunctionRow[]) => void;
}

export const FunctionItem: React.FC<FunctionItemProps> = ({ row, label, known, onSaved }) => {
  const { t } = useSectionText('functions');
  const base = useBrainText();
  const { pool, run, action } = useBrain();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<AssignmentMode>(row.mode);
  const [order, setOrder] = useState<string[]>([...row.order]);
  const savedKey = `${row.mode}|${row.order.join(',')}`;
  useEffect(() => {
    setMode(row.mode);
    setOrder([...row.order]);
  }, [savedKey]);

  const dirty = mode !== row.mode || !sameChain(order, row.order);
  const key = `fn:${row.id}`;
  const active = row.chain[0] ?? null;

  const save = async () => {
    const result = await run(key, 'brain_function_failed', () => saveFunction(row.id, mode, mode === 'inherit' ? [] : order));
    if (result) onSaved(result);
  };

  return (
    <li className="border-b border-slate-100 last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500/40 sm:px-5"
      >
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-slate-900">{label}</span>
          <span className="block truncate text-xs text-slate-500">
            {row.mode === 'inherit' ? t('inherits', { context: base.t(`role_${row.role}`) }) : t('own_chain')} · {active ? active.model : base.t('none_available')}
          </span>
        </span>
        {row.mode !== 'inherit' && <Badge tone="info">{base.t('mode_custom')}</Badge>}
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
      {open && (
        <div className="flex flex-col gap-3 bg-slate-50 px-4 py-4 sm:px-5">
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-700 sm:max-w-sm">
            {t('mode_label')}
            <select value={mode} onChange={(e) => setMode(MODES.find((m) => m === e.target.value) ?? 'inherit')} className={fieldClass}>
              {MODES.map((m) => (
                <option key={m} value={m}>{t(`mode_${m}`, { context: base.t(`role_${row.role}`) })}</option>
              ))}
            </select>
          </label>
          {mode !== 'inherit' && <ChainEditor chain={order} pool={pool} known={known} onChange={setOrder} pickerTitle={t('picker_title', { name: label })} />}
          {dirty && (
            <div className="flex flex-wrap justify-end gap-2">
              <Button disabled={action.busy !== null} onClick={() => { setMode(row.mode); setOrder([...row.order]); }}>
                {base.t('cancel')}
              </Button>
              <Button variant="primary" icon={Save} busy={action.busy === key} disabled={action.busy !== null || (mode !== 'inherit' && order.length === 0)} onClick={() => void save()}>
                {base.t('save')}
              </Button>
            </div>
          )}
        </div>
      )}
    </li>
  );
};
