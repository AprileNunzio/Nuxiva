import React from 'react';
import { Volume2 } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { AudioChannelPanel } from '../shared/components/AudioChannelPanel';
import { DeviceInventory } from '../shared/components/DeviceInventory';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { SettingsPanel } from '../shared/components/SettingsPanel';
import { useLocalAudio } from '../shared/hooks/useLocalAudio';
import { useNodeSettings } from '../shared/hooks/useNodeSettings';
import { usePairedNode } from '../shared/hooks/usePairedNode';
import { SoundTestPanel } from './components/SoundTestPanel';
import { VOICE_SPECS, useAudioI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = useAudioI18n();
  const local = scope === 'local';
  const audio = useLocalAudio(local);
  const settings = useNodeSettings(nodeId, scope, VOICE_SPECS);
  const { node } = usePairedNode(nodeId, scope);

  return (
    <ModuleFrame icon={Volume2} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope !== 'mesh' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="flex min-w-0 flex-col gap-4">
            {local && <AudioChannelPanel side="output" audio={audio} t={t} />}
            {scope === 'paired' && (
              <>
                <Notice tone="info">{t('notice_paired')}</Notice>
                <DeviceInventory title={t('inventory_title')} devices={node?.hardware?.audioOut ?? []} emptyLabel={t('inventory_empty')} />
              </>
            )}
            {local && <SoundTestPanel />}
          </div>
          <SettingsPanel title={t('voice_title')} specs={VOICE_SPECS} state={settings} t={t} />
        </div>
      )}
    </ModuleFrame>
  );
};

export default View;
