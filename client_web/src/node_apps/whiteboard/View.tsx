import React, { useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { CheckCircle2, Save, Cpu } from 'lucide-react';

interface Props {
  nodeId?: string;
}

export const View: React.FC<Props> = ({ nodeId = 'current-node' }) => {
  const { t } = useScopedI18n('node_apps/whiteboard');
  const [saved, setSaved] = useState(false);
  const [enabled, setEnabled] = useState(true);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-xl font-mono text-slate-100">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-cyan-400 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyan-400" />
            {t('title')}
          </h2>
          <p className="text-xs text-slate-400 mt-1">{t('description')}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-emerald-400 font-semibold">{t('active')}</span>
        </div>
      </div>

      <div className="space-y-4 mb-6">
        <div className="bg-slate-950/70 p-4 rounded-lg border border-slate-800/80 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-slate-200">{t('status')}</div>
            <div className="text-xs text-slate-500">Node ID: {nodeId}</div>
          </div>
          <button
            onClick={() => setEnabled(!enabled)}
            className={`px-3 py-1 rounded text-xs font-semibold ${enabled ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-slate-800 text-slate-400'}`}
          >
            {enabled ? 'ENABLED' : 'DISABLED'}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-semibold transition"
        >
          <Save className="w-4 h-4" />
          {t('save')}
        </button>
        {saved && (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
            {t('saved')}
          </span>
        )}
      </div>
    </div>
  );
};
