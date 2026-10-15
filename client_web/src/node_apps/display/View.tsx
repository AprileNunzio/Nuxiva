import React from 'react';
import { MonitorPlay } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { SettingsPanel } from '../shared/components/SettingsPanel';
import { useNodeSettings } from '../shared/hooks/useNodeSettings';
import { AvatarLibraryPanel } from './components/AvatarLibraryPanel';
import { ScreensPanel } from './components/ScreensPanel';
import { useAvatars } from './hooks/useAvatars';
import { useScreens } from './hooks/useScreens';
import { APPEARANCE_SPECS, KIOSK_SPECS, useDisplayI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = useDisplayI18n();
  const local = scope === 'local';
  const screens = useScreens(local);
  const avatars = useAvatars(local);
  const appearance = useNodeSettings(nodeId, scope, APPEARANCE_SPECS);
  const kiosk = useNodeSettings(nodeId, scope, KIOSK_SPECS);

  return (
    <ModuleFrame icon={MonitorPlay} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && <Notice tone="info">{t('notice_paired')}</Notice>}
      {scope !== 'mesh' && (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="flex min-w-0 flex-col gap-4">
            {local && <ScreensPanel state={screens} />}
            <SettingsPanel title={t('appearance_title')} specs={APPEARANCE_SPECS} state={appearance} t={t} />
          </div>
          <div className="flex min-w-0 flex-col gap-4">
            {local && <AvatarLibraryPanel handle={avatars} />}
            <SettingsPanel title={t('kiosk_title')} specs={KIOSK_SPECS} state={kiosk} t={t} />
          </div>
        </div>
      )}
    </ModuleFrame>
  );
};

export default View;
