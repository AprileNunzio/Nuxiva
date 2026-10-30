import React, { useState } from 'react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { ConfirmDialog } from '../../../../shared/ui/ConfirmDialog';
import { applyPreset, fetchPresets } from '../../core/presetsApi';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { Card } from '../../ui/primitives';

export const PresetsCard: React.FC = () => {
  const { t } = useSectionText('overview');
  const base = useBrainText();
  const { commit, action } = useBrain();
  const presets = usePolled(fetchPresets, 'brain_presets_unavailable', true, 0);
  const [pending, setPending] = useState<string | null>(null);
  const name = (id: string) => {
    const value = t(`preset_${id}`);
    return value === `preset_${id}` ? id : value;
  };
  if (!presets.data || presets.data.length === 0) {
    return null;
  }
  const confirm = async () => {
    if (!pending) return;
    await commit(`preset:${pending}`, 'brain_preset_failed', () => applyPreset(pending));
    setPending(null);
  };
  return (
    <Card title={t('presets_title')} description={t('presets_hint')}>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {presets.data.map((id) => (
          <button
            key={id}
            type="button"
            disabled={action.busy !== null}
            onClick={() => setPending(id)}
            className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-white p-3 text-left transition hover:border-blue-300 hover:bg-blue-50/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:opacity-60"
          >
            <span className="text-sm font-medium text-slate-900">{name(id)}</span>
            <span className="text-xs text-slate-500">{t(`preset_${id}_hint`)}</span>
          </button>
        ))}
      </div>
      {pending && (
        <ConfirmDialog
          title={t('preset_confirm_title', { name: name(pending) })}
          body={t('preset_confirm_body')}
          confirmLabel={t('preset_apply')}
          cancelLabel={base.t('cancel')}
          pending={action.busy === `preset:${pending}`}
          tone="neutral"
          onConfirm={() => void confirm()}
          onCancel={() => setPending(null)}
        />
      )}
    </Card>
  );
};
