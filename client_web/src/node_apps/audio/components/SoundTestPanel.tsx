import React, { useEffect, useState } from 'react';
import { Loader2, Play } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { SystemSound, fetchSounds, playSound } from '../../shared/data/soundsApi';
import { useAudioI18n } from '../scope';

export const SoundTestPanel: React.FC = () => {
  const { t } = useAudioI18n();
  const [sounds, setSounds] = useState<readonly SystemSound[]>([]);
  const [selected, setSelected] = useState('');
  const [playing, setPlaying] = useState(false);
  const [result, setResult] = useState<'ok' | 'failed' | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchSounds(controller.signal)
      .then((list) => {
        setSounds(list);
        setSelected((current) => current || list[0]?.name || '');
      })
      .catch((cause: unknown) => !controller.signal.aborted && reportError('node_sounds_unavailable', cause));
    return () => controller.abort();
  }, []);

  const play = async () => {
    setPlaying(true);
    setResult(null);
    try {
      await playSound(selected);
      setResult('ok');
    } catch (cause) {
      reportError('node_sound_play_failed', cause);
      setResult('failed');
    } finally {
      setPlaying(false);
    }
  };

  return (
    <Panel title={t('test_title')}>
      <p className="mb-3 text-xs text-slate-500">{t('test_hint')}</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <select
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
          aria-label={t('test_sound')}
          className="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white focus:border-cyan-400 focus:outline-none"
        >
          {sounds.map((sound) => (
            <option key={sound.name} value={sound.name}>
              {sound.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={play}
          disabled={!selected || playing}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
        >
          {playing ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
          {t('test_play')}
        </button>
      </div>
      {result && (
        <p role="status" className={`mt-2 text-xs ${result === 'ok' ? 'text-emerald-300' : 'text-rose-300'}`}>
          {t(result === 'ok' ? 'test_ok' : 'test_failed')}
        </p>
      )}
    </Panel>
  );
};
