import React from 'react';
import { Mic } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { AudioChannelPanel } from '../shared/components/AudioChannelPanel';
import { DeviceInventory } from '../shared/components/DeviceInventory';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { SettingsPanel } from '../shared/components/SettingsPanel';
import { useLocalAudio } from '../shared/hooks/useLocalAudio';
import { useNodeSettings } from '../shared/hooks/useNodeSettings';
import { usePairedNode } from '../shared/hooks/usePairedNode';
import { MicTestPanel } from './components/MicTestPanel';
import { WakeWordPanel } from './components/WakeWordPanel';
import { EAR_SPECS, EQ_SPECS, useMicI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = useMicI18n();
  const local = scope === 'local';
  const audio = useLocalAudio(local);
  const settings = useNodeSettings(nodeId, scope, EAR_SPECS);
  const equalizer = useNodeSettings(nodeId, scope, EQ_SPECS);
  const { node } = usePairedNode(nodeId, scope);

  return (
    <ModuleFrame icon={Mic} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope !== 'mesh' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="flex min-w-0 flex-col gap-4">
            <WakeWordPanel />
            {local && <AudioChannelPanel side="input" audio={audio} t={t} />}
            {local && <MicTestPanel ear={settings.values} eq={equalizer.values} />}
            {scope === 'paired' && (
              <>
                <Notice tone="info">{t('notice_paired')}</Notice>
                <DeviceInventory title={t('inventory_title')} devices={node?.hardware?.audioIn ?? []} emptyLabel={t('inventory_empty')} />
              </>
            )}
          </div>
          <div className="flex min-w-0 flex-col gap-4">
            <SettingsPanel title={t('ear_title')} specs={EAR_SPECS} state={settings} t={t} />
            <SettingsPanel title={t('eq_title')} specs={EQ_SPECS} state={equalizer} t={t} />
          </div>
        </div>
      )}
    </ModuleFrame>
  );
};

export default View;
