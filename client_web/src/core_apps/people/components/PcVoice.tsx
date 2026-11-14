import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, Loader2, Mic, Square } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { DeviceAccess } from '../devices/DeviceAccess';
import { EnrollEvent, VoiceEnrollment } from '../devices/earEnroll';
import { useMediaAccess } from '../devices/useMediaAccess';
import { chipClass, primaryClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly samples: number;
  readonly onSaved: () => void;
}

const TARGET = 5;
const SENTENCES = 6;
type Phase = 'idle' | 'connecting' | 'recording' | 'unavailable' | 'closed' | 'done';

export const PcVoice: React.FC<Props> = ({ slug, samples, onSaved }) => {
  const { t } = usePeopleI18n();
  const access = useMediaAccess('microphone');
  const session = useRef<VoiceEnrollment | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [count, setCount] = useState(samples);
  const [level, setLevel] = useState(0);
  const [missed, setMissed] = useState(false);
  const [sentence, setSentence] = useState(1);
  const latest = useRef(samples);

  useEffect(() => () => session.current?.stop(), []);
  useEffect(() => {
    latest.current = samples;
    setCount(samples);
  }, [samples]);

  const handle = (event: EnrollEvent) => {
    if (event.type === 'level') {
      setLevel(event.value);
    } else if (event.type === 'progress') {
      if (event.count > latest.current) {
        setSentence((s) => (s % SENTENCES) + 1);
      }
      latest.current = event.count;
      setCount(event.count);
      setMissed(!event.ok);
    } else if (event.type === 'unavailable') {
      setPhase('unavailable');
    } else if (event.type === 'done') {
      setPhase(event.count >= TARGET ? 'done' : 'idle');
      onSaved();
    } else {
      setPhase((p) => (p === 'recording' || p === 'connecting' ? 'closed' : p));
    }
  };

  const start = async () => {
    const stream = access.stream ?? (await access.request());
    if (!stream) {
      return;
    }
    setPhase('connecting');
    const next = new VoiceEnrollment(slug, stream, handle);
    session.current = next;
    try {
      await next.start();
      setPhase('recording');
    } catch (cause: unknown) {
      next.stop();
      setPhase('closed');
      reportError('people_voice_failed', cause);
    }
  };

  const stop = () => {
    session.current?.stop();
    session.current = null;
    access.release();
  };

  const recording = phase === 'recording';
  const pct = Math.min(100, Math.round((count / TARGET) * 100));
  return (
    <section aria-labelledby="pc-voice-title" className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 cq-xl:col-span-2">
      <h3 id="pc-voice-title" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
        <Mic className="h-4 w-4 text-teal-600" aria-hidden="true" />
        {t('pc_voice_title')}
      </h3>
      <p className="text-xs text-slate-500">{t('pc_voice_hint', { n: TARGET })}</p>
      {!recording && (
        <DeviceAccess kind="microphone" state={access.state} devices={access.devices} deviceId={access.deviceId} active={access.stream !== null}
          onRequest={(id) => void access.request(id)} onRelease={access.release} toggle={false} />
      )}
      <div className="flex flex-col gap-1">
        <span className="flex justify-between text-xs text-slate-600">
          {t('pc_voice_progress', { count: Math.min(count, TARGET), total: TARGET })}
          {count >= TARGET && <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-label={t('pc_voice_done')} />}
        </span>
        <div className="h-1.5 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
          <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 transition-[width]" style={{ width: `${pct}%` }} />
        </div>
      </div>
      {recording && (
        <div className="flex flex-col gap-2 rounded-xl border border-teal-300 bg-white p-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-teal-700">{t('pc_voice_read', { n: sentence, total: SENTENCES })}</p>
          <p className="text-base font-medium text-slate-900" aria-live="polite">{t(`pc_voice_sentence_${sentence}`)}</p>
          <div className="h-1 overflow-hidden rounded-full bg-slate-200" aria-label={t('pc_voice_level')}>
            <div className="h-full bg-teal-500 transition-[width] duration-100" style={{ width: `${Math.round(level * 100)}%` }} />
          </div>
          {missed && <p className="text-xs text-amber-800">{t('pc_voice_missed')}</p>}
        </div>
      )}
      {(phase === 'unavailable' || phase === 'closed' || phase === 'done') && (
        <p role="status" className={`text-xs ${phase === 'done' ? 'text-emerald-700' : 'text-amber-800'}`}>{t(`pc_voice_${phase}`)}</p>
      )}
      <div className="flex flex-wrap gap-2">
        {recording || phase === 'connecting' ? (
          <button type="button" onClick={stop} className={`${chipClass} border-rose-300 py-2 text-rose-800`}>
            {phase === 'connecting' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Square className="h-3.5 w-3.5" aria-hidden="true" />}
            {t('pc_voice_stop')}
          </button>
        ) : (
          <button type="button" disabled={access.state === 'insecure' || access.state === 'unsupported'} onClick={() => void start()} className={primaryClass}>
            <Mic className="h-4 w-4" aria-hidden="true" />
            {t('pc_voice_start')}
          </button>
        )}
      </div>
    </section>
  );
};
