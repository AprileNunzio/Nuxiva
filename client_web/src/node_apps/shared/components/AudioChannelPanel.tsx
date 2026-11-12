import React from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import { AudioDevice, AudioSide } from '../data/localAudioApi';
import { LocalAudioController } from '../hooks/useLocalAudio';
import { Panel } from './ModuleFrame';

type Translate = (key: string, params?: Record<string, string | number>) => string;

interface AudioChannelPanelProps {
  readonly side: AudioSide;
  readonly audio: LocalAudioController;
  readonly t: Translate;
}

export const AudioChannelPanel: React.FC<AudioChannelPanelProps> = ({ side, audio, t }) => {
  const state = audio.state;
  if (!state) {
    return null;
  }
  const channel = state[side];
  const list: readonly AudioDevice[] = side === 'output' ? state.outputs : state.inputs;
  const id = `audio-${side}`;
  return (
    <Panel title={t('channel_title')}>
      {!state.available ? (
        <p className="text-sm text-amber-200">{t('channel_unavailable', { error: state.error ?? '' })}</p>
      ) : (
        <div className="flex flex-col gap-3">
          <label htmlFor={`${id}-device`} className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
            {t('channel_device')}
          </label>
          <select
            id={`${id}-device`}
            value={channel.device ?? ''}
            disabled={audio.busy}
            onChange={(event) => audio.apply(side, { device: event.target.value })}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white focus:border-cyan-400 focus:outline-none"
          >
            {list.length === 0 && <option value="">{t('channel_none')}</option>}
            {list.map((device) => (
              <option key={device.name} value={device.name}>
                {device.label}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => audio.apply(side, { muted: !channel.muted })}
              aria-pressed={channel.muted}
              aria-label={t(channel.muted ? 'channel_unmute' : 'channel_mute')}
              className={`rounded-xl border p-2.5 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                channel.muted ? 'border-rose-400/50 bg-rose-500/15 text-rose-200' : 'border-slate-700 bg-slate-900 text-cyan-200'
              }`}
            >
              {channel.muted ? <VolumeX className="h-4 w-4" aria-hidden="true" /> : <Volume2 className="h-4 w-4" aria-hidden="true" />}
            </button>
            <input
              type="range"
              min={0}
              max={150}
              step={1}
              value={channel.volume}
              onChange={(event) => audio.apply(side, { volume: Number(event.target.value) })}
              aria-label={t('channel_volume')}
              aria-valuetext={`${channel.volume}%`}
              className="flex-1 cursor-pointer accent-cyan-400"
            />
            <span className="w-12 text-right font-mono text-sm text-cyan-100">{channel.volume}%</span>
          </div>
          {channel.volume > 100 && <p className="text-xs text-amber-200">{t('channel_boost_warning')}</p>}
        </div>
      )}
    </Panel>
  );
};
