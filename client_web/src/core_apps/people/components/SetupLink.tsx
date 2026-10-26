import React from 'react';
import { Settings } from 'lucide-react';
import { useOSApp } from '../../../app_shell/window_manager/WindowContext';
import { chipClass, usePeopleI18n } from '../scope';

interface Props {
  readonly feature: 'google' | 'telegram';
  readonly hint: string;
}

export const SetupLink: React.FC<Props> = ({ feature, hint }) => {
  const { t } = usePeopleI18n();
  const { openApp } = useOSApp();
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900" role="status">
      <p>{hint}</p>
      <button type="button" onClick={() => openApp({ appId: 'feature_settings', instanceKey: feature })} className={`${chipClass} self-start border-amber-400 bg-white px-3 py-2 text-amber-900`}>
        <Settings className="h-4 w-4" aria-hidden="true" />
        {t('open_control_panel')}
      </button>
    </div>
  );
};
