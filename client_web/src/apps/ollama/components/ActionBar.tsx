import React from 'react';
import { RotateCcw, Save, Wrench } from 'lucide-react';

interface ActionBarProps {
  saving: boolean;
  onSave: () => void;
  onResetAuto: () => void;
  onRestart: () => void;
  t: (key: string) => string;
}

export const ActionBar: React.FC<ActionBarProps> = ({ saving, onSave, onResetAuto, onRestart, t }) => {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onResetAuto}
          disabled={saving}
          className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-secondary/80 hover:bg-secondary text-secondary-foreground border border-border transition-all active:scale-95 disabled:opacity-50"
          title={t('btn_reset_auto_tooltip')}
        >
          <Wrench className="w-4 h-4 text-primary" />
          <span>{t('btn_reset_auto')}</span>
        </button>

        <button
          type="button"
          onClick={onRestart}
          disabled={saving}
          className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-background hover:bg-muted text-muted-foreground hover:text-foreground border border-border transition-all active:scale-95 disabled:opacity-50"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>{t('btn_restart')}</span>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm transition-all active:scale-95 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          <span>{saving ? t('btn_saving') : t('btn_save_apply')}</span>
        </button>
      </div>
    </div>
  );
};
