import React, { useState } from 'react';
import { Btn, inputClass } from '../../shared/kit';

interface Props {
  readonly projectId: string;
  readonly busy: boolean;
  readonly t: (key: string) => string;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

export const DeleteConfirm: React.FC<Props> = ({ projectId, busy, t, onConfirm, onCancel }) => {
  const [typed, setTyped] = useState('');
  return (
    <div role="alertdialog" aria-label={t('delete_title')} className="flex flex-col gap-2 rounded-2xl bg-error/10 p-3">
      <p className="text-sm font-semibold text-error">{t('delete_title')}</p>
      <p className="text-xs text-on-surface-variant">{t('delete_hint')}</p>
      <code className="w-fit rounded-lg bg-surface-container px-2 py-0.5 text-xs">{projectId}</code>
      <input
        className={inputClass}
        value={typed}
        autoComplete="off"
        spellCheck={false}
        aria-label={t('delete_input')}
        onChange={(event) => setTyped(event.target.value)}
      />
      <div className="flex gap-2">
        <Btn tone="rose" busy={busy} disabled={typed !== projectId} onClick={onConfirm}>
          {t('delete_confirm')}
        </Btn>
        <Btn tone="slate" onClick={onCancel}>
          {t('cancel')}
        </Btn>
      </div>
    </div>
  );
};
