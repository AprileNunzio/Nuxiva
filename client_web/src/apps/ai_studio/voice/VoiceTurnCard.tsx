import React, { useState } from 'react';
import { useStudioI18n } from '../scope';
import { Markdown } from '../components/Markdown';
import { VoiceAudioPlayer } from './VoiceAudioPlayer';
import { VoiceReview } from './VoiceReview';
import { deleteVoiceTurn } from './api';
import type { VoiceHeard, VoiceTurn } from './types';

interface VoiceTurnCardProps {
  turn: VoiceTurn;
  onHeardChange: (heard: VoiceHeard) => void;
  onDeleted: () => void;
  onContinue: (turn: VoiceTurn) => void;
}

const Label: React.FC<{ icon: string; text: string }> = ({ icon, text }) => (
  <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
    <span aria-hidden>{icon}</span>
    <span>{text}</span>
  </span>
);

const Pill: React.FC<{ children: React.ReactNode; tone?: string }> = ({ children, tone = 'border-slate-700 text-slate-400' }) => (
  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-mono ${tone}`}>{children}</span>
);

export const VoiceTurnCard: React.FC<VoiceTurnCardProps> = ({ turn, onHeardChange, onDeleted, onContinue }) => {
  const { t } = useStudioI18n();
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const heard = turn.heard;
  const speaker = turn.speaker || heard?.speaker || '';
  const time = new Date(turn.at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  const remove = async () => {
    if (!confirm) {
      setConfirm(true);
      return;
    }
    try {
      await deleteVoiceTurn(turn.id);
      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setConfirm(false);
    }
  };

  return (
    <article className="shrink-0 group rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-lg shadow-black/20 overflow-hidden">
      <header className="flex flex-wrap items-center gap-1.5 px-3 py-2 border-b border-slate-800/80 bg-slate-950/40">
        <span className="font-mono text-[11px] text-slate-400">{time}</span>
        <Pill tone={turn.channel === 'voice' ? 'border-cyan-500/50 text-cyan-300' : 'border-violet-500/50 text-violet-300'}>
          {turn.channel === 'voice' ? `🎙 ${t('voice_channel_voice')}` : `⌨ ${t('voice_channel_text')}`}
        </Pill>
        <Pill>{`${t('voice_speaker')}: ${speaker || t('voice_unknown_speaker')}`}</Pill>
        {heard && heard.score > 0 && <Pill>{`${t('voice_confidence')} ${Math.round(heard.score * 100)}%`}</Pill>}
        {turn.elapsed_ms > 0 && <Pill>{`${t('voice_latency')} ${(turn.elapsed_ms / 1000).toFixed(1)}s`}</Pill>}
        {heard?.verdict === 'ok' && <Pill tone="border-emerald-500/50 text-emerald-300">{t('voice_reviewed_ok')}</Pill>}
        {heard?.verdict === 'wrong' && <Pill tone="border-rose-500/50 text-rose-300">{t('voice_reviewed_wrong')}</Pill>}
      </header>

      <div className="grid gap-3 p-3 cq-xl:grid-cols-2">
        <section className="flex flex-col gap-2">
          <Label icon="🗣" text={t('voice_said')} />
          <p className="rounded-xl rounded-tl-xs bg-gradient-to-r from-cyan-600 to-blue-600 text-white text-sm px-3 py-2 whitespace-pre-wrap break-words">{turn.said}</p>

          {turn.channel === 'voice' && (
            <div className="flex flex-col gap-1.5 rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2">
              <Label icon="👂" text={t('voice_heard')} />
              {heard ? (
                <>
                  <p className="text-xs text-slate-200 whitespace-pre-wrap break-words">« {heard.text} »</p>
                  <VoiceAudioPlayer turnId={turn.id} available={heard.audio} duration={heard.dur} />
                  {heard.ms > 0 && <span className="text-[10px] font-mono text-slate-500">{`${t('voice_stt')} ${heard.ms} ms`}</span>}
                </>
              ) : (
                <span className="text-[11px] text-slate-500 italic">{t('voice_no_audio')}</span>
              )}
            </div>
          )}

          <div className="flex flex-col gap-1.5 rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2">
            <Label icon="🧠" text={t('voice_understood')} />
            {turn.directed ? (
              <>
                <p className="text-xs text-slate-200 whitespace-pre-wrap break-words">
                  {turn.resolved || <span className="italic text-slate-500">{t('voice_same_text')}</span>}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {turn.intent && <Pill tone="border-amber-500/50 text-amber-300">{`${t('voice_intent')}: ${turn.intent}`}</Pill>}
                  {turn.agent && <Pill>{`${t('voice_agent')}: ${turn.agent}`}</Pill>}
                </div>
              </>
            ) : (
              <p className="text-xs text-amber-300/90">{t('voice_ignored')}{turn.reason ? ` · ${turn.reason}` : ''}</p>
            )}
          </div>
        </section>

        <section className="flex flex-col gap-2 min-w-0">
          <Label icon="✦" text={t('voice_reply')} />
          <div className="rounded-xl rounded-tr-xs border border-slate-800 bg-slate-900/90 text-slate-100 text-sm px-3 py-2 min-w-0 break-words">
            {turn.reply ? <Markdown source={turn.reply} /> : <span className="italic text-slate-500">—</span>}
          </div>
          {heard ? (
            <VoiceReview turnId={turn.id} heard={heard} onSaved={onHeardChange} />
          ) : (
            turn.channel === 'voice' && <span className="text-[10px] text-slate-500">{t('voice_no_review')}</span>
          )}
        </section>
      </div>

      <footer className="flex flex-wrap items-center justify-end gap-1.5 px-3 py-2 border-t border-slate-800/60 bg-slate-950/30">
        {error && <span className="mr-auto text-[11px] text-rose-400">{error}</span>}
        <button type="button" onClick={() => void navigator.clipboard.writeText(`${turn.said}\n\n${turn.reply}`)} className="px-2 py-1 rounded-lg text-[11px] text-slate-400 hover:text-white hover:bg-slate-800">
          {t('voice_copy')}
        </button>
        <button type="button" onClick={() => onContinue(turn)} className="px-2 py-1 rounded-lg text-[11px] text-cyan-300 hover:text-white hover:bg-cyan-900/50">
          {t('voice_continue_chat')}
        </button>
        <button
          type="button"
          onClick={remove}
          onBlur={() => setConfirm(false)}
          className={`px-2 py-1 rounded-lg text-[11px] ${confirm ? 'bg-rose-600 text-white' : 'text-rose-400 hover:text-white hover:bg-rose-900/50'}`}
        >
          {confirm ? t('voice_delete_confirm') : t('voice_delete')}
        </button>
      </footer>
    </article>
  );
};
