import React, { useState } from 'react';
import { AlertCircle, Brain, CheckCircle2, Minimize2, Sparkles } from 'lucide-react';
import { triggerMissionCompression } from '../api';
import { secondaryBtnClass, useAutonomousI18n } from '../scope';
import { Mission } from '../types';

interface Props {
  mission: Mission;
  onUpdate: (updated: Mission) => void;
}

export const MissionMemoryCard: React.FC<Props> = ({ mission, onUpdate }) => {
  const { t } = useAutonomousI18n();
  const [compressing, setCompressing] = useState(false);
  const memory = mission.memory;

  async function handleCompressNow() {
    setCompressing(true);
    try {
      const res = await triggerMissionCompression(mission.id);
      if (res.memory) {
        onUpdate({
          ...mission,
          memory: res.memory,
        });
      }
    } finally {
      setCompressing(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-indigo-900/40 bg-gradient-to-br from-indigo-950/30 via-slate-900/40 to-slate-950/60 p-5 backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-indigo-500/10 p-2.5 text-indigo-400">
            <Brain className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-indigo-200">
              {t('episodic_memory_title')}
            </h3>
            <span className="text-[11px] text-slate-400">
              {t('memory_cycles_count', { count: memory?.compression_count || 0 })}
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void handleCompressNow()}
          disabled={compressing}
          className={secondaryBtnClass}
        >
          <Minimize2 className={`h-4 w-4 ${compressing ? 'animate-spin' : ''}`} />
          {t('compress_memory_now')}
        </button>
      </div>

      {memory?.summary && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-300">
          <span className="font-semibold text-slate-400">{t('memory_summary_label')}:</span>{' '}
          {memory.summary}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-rose-950/30 bg-rose-950/10 p-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-rose-300">
            <AlertCircle className="h-4 w-4" />
            {t('lessons_learned_title')}
          </div>
          {memory?.lessons_learned && memory.lessons_learned.length > 0 ? (
            <ul className="flex flex-col gap-1.5 text-xs text-slate-300">
              {memory.lessons_learned.map((rule, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span className="font-bold text-rose-400">•</span>
                  <span>{rule}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs italic text-slate-500">{t('no_lessons_yet')}</p>
          )}
        </div>

        <div className="rounded-xl border border-emerald-950/30 bg-emerald-950/10 p-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-emerald-300">
            <CheckCircle2 className="h-4 w-4" />
            {t('key_decisions_title')}
          </div>
          {memory?.key_decisions && memory.key_decisions.length > 0 ? (
            <ul className="flex flex-col gap-1.5 text-xs text-slate-300">
              {memory.key_decisions.map((decision, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span className="font-bold text-emerald-400">✓</span>
                  <span>{decision}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs italic text-slate-500">{t('no_decisions_yet')}</p>
          )}
        </div>
      </div>
    </div>
  );
};
