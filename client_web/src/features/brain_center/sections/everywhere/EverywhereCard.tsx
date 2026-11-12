import React, { useState } from 'react';
import { Layers, Wand2 } from 'lucide-react';
import { ConfirmDialog } from '../../../../shared/ui/ConfirmDialog';
import { applyEverywhere } from '../../core/presetsApi';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { Button, Card, FLUID } from '../../ui/primitives';
import { ModelPicker } from '../../ui/ModelPicker';

const KEY = 'everywhere';

export const EverywhereCard: React.FC = () => {
  const { t } = useSectionText('everywhere');
  const base = useBrainText();
  const { pool, commit, action } = useBrain();
  const [picking, setPicking] = useState(false);
  const [model, setModel] = useState<string | null>(null);
  const [keep, setKeep] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const label = model ? pool.find((r) => r.ref === model)?.model ?? model : '';

  const apply = async () => {
    if (!model) return;
    const done = await commit(KEY, 'brain_everywhere_failed', () => applyEverywhere(model, keep));
    setConfirming(false);
    if (done) setModel(null);
  };

  const option = (value: boolean, title: string, hint: string) => (
    <label className={`flex cursor-pointer gap-3 rounded-lg border p-3 transition ${keep === value ? 'border-blue-400 bg-blue-50/60' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
      <input type="radio" name="brain-everywhere-mode" checked={keep === value} onChange={() => setKeep(value)} className="mt-0.5 h-4 w-4 accent-blue-600" />
      <span className="min-w-0">
        <span className="block text-sm font-medium text-slate-900">{title}</span>
        <span className="block text-xs text-slate-500">{hint}</span>
      </span>
    </label>
  );

  return (
    <Card title={t('title')} description={t('hint')}>
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button icon={Layers} disabled={action.busy !== null} onClick={() => setPicking(true)}>
            {model ? t('change') : t('pick')}
          </Button>
          {model && <span className="min-w-0 truncate font-mono text-xs text-slate-700">{label}</span>}
        </div>
        {model && (
          <>
            <div className={`grid gap-2 ${FLUID.md}`}>
              {option(false, t('only'), t('only_hint'))}
              {option(true, t('keep'), t('keep_hint'))}
            </div>
            <div>
              <Button variant="primary" icon={Wand2} busy={action.busy === KEY} disabled={action.busy !== null} onClick={() => setConfirming(true)}>
                {t('apply')}
              </Button>
            </div>
          </>
        )}
      </div>
      {picking && (
        <ModelPicker
          title={t('pick')}
          pool={pool}
          exclude={[]}
          onPick={(ref) => {
            setModel(ref);
            setPicking(false);
          }}
          onClose={() => setPicking(false)}
        />
      )}
      {confirming && model && (
        <ConfirmDialog
          title={t('confirm_title', { model: label })}
          body={t(keep ? 'confirm_keep' : 'confirm_only')}
          confirmLabel={t('apply')}
          cancelLabel={base.t('cancel')}
          pending={action.busy === KEY}
          tone="neutral"
          onConfirm={() => void apply()}
          onCancel={() => setConfirming(false)}
        />
      )}
    </Card>
  );
};
