import React, { useState } from 'react';
import { useStudioI18n } from '../scope';
import { sendVoiceFeedback } from './api';
import type { VoiceHeard, VoiceVerdict } from './types';

interface VoiceReviewProps {
  turnId: string;
  heard: VoiceHeard;
  onSaved: (heard: VoiceHeard) => void;
}

export const VoiceReview: React.FC<VoiceReviewProps> = ({ turnId, heard, onSaved }) => {
  const { t } = useStudioI18n();
  const [verdict, setVerdict] = useState<VoiceVerdict>(heard.verdict);
  const [correction, setCorrection] = useState(heard.correction);
  const [note, setNote] = useState(heard.note);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const submit = async (next: VoiceVerdict) => {
    setVerdict(next);
    if (next === 'wrong' && !correction.trim() && !note.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const fix = next === 'wrong' ? correction.trim() : '';
      await sendVoiceFeedback(turnId, next, fix, note.trim());
      onSaved({ ...heard, verdict: next, correction: fix, note: note.trim(), applied: false });
      setMessage(t('voice_feedback_saved'));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const chip = (value: VoiceVerdict, label: string, tone: string) => (
    <button
      type="button"
      disabled={busy}
      onClick={() => submit(value)}
      aria-pressed={verdict === value}
      className={`px-2.5 py-1 rounded-full border text-[11px] font-medium transition-colors ${verdict === value ? tone : 'border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500'}`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col gap-2 pt-2 border-t border-slate-800/80">
      <div className="flex flex-wrap items-center gap-2">
        {chip('ok', `✓ ${t('voice_verdict_ok')}`, 'border-emerald-500/60 bg-emerald-500/15 text-emerald-300')}
        {chip('wrong', `✕ ${t('voice_verdict_wrong')}`, 'border-rose-500/60 bg-rose-500/15 text-rose-300')}
        {heard.applied && <span className="text-[10px] text-emerald-400/80">{t('voice_feedback_applied')}</span>}
      </div>
      {verdict === 'wrong' && (
        <div className="flex flex-col gap-1.5">
          <input
            value={correction}
            maxLength={2000}
            onChange={(e) => setCorrection(e.target.value)}
            placeholder={t('voice_correction')}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-rose-500/70"
          />
          <input
            value={note}
            maxLength={600}
            onChange={(e) => setNote(e.target.value)}
            placeholder={t('voice_note')}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-slate-500"
          />
          <button
            type="button"
            disabled={busy || (!correction.trim() && !note.trim())}
            onClick={() => submit('wrong')}
            className="self-end px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[11px] font-semibold disabled:opacity-40"
          >
            {t('voice_send_feedback')}
          </button>
        </div>
      )}
      {message && <span className="text-[11px] text-slate-400" role="status">{message}</span>}
    </div>
  );
};
