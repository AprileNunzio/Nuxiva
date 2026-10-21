import React from 'react';
import { AudioWaveform } from 'lucide-react';
import { useAssistantIdentity } from '../../../shared/identity/IdentityContext';
import { Panel } from '../../shared/components/ModuleFrame';
import { useMicI18n } from '../scope';

export const WakeWordPanel: React.FC = () => {
  const { t } = useMicI18n();
  const identity = useAssistantIdentity();
  return (
    <Panel title={t('wake_title')}>
      <div className="flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-400/40 bg-cyan-400/10">
          <AudioWaveform className="h-6 w-6 text-cyan-200" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="font-['Rajdhani'] text-2xl font-bold tracking-wide text-white">«{identity.name}»</p>
          <p className="text-xs text-slate-400">{t('wake_hint')}</p>
        </div>
      </div>
      <ul className="mt-3 flex flex-wrap gap-1.5" aria-label={t('wake_phrases')}>
        {identity.wakePhrases.map((phrase) => (
          <li key={phrase} className="rounded-full border border-slate-700 px-2.5 py-1 font-mono text-xs text-cyan-100">
            {phrase}
          </li>
        ))}
      </ul>
    </Panel>
  );
};
