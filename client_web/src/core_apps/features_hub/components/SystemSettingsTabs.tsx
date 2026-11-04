import React, { useState } from 'react';
import { useResource } from '../../shared/useResource';
import { FeaturesOverview } from '../../shared/featureTypes';
import { OSFilterTabs } from '../../shared/kit';
import { overviewUrl } from '../api';
import { AgentSection } from './AgentSection';
import { RedAlertSection } from './RedAlertSection';
import { SystemSettingsView } from './SystemSettingsView';

interface SystemSettingsTabsProps {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly lang: string;
  readonly onBack: () => void;
}

export const SystemSettingsTabs: React.FC<SystemSettingsTabsProps> = ({ t, lang, onBack }) => {
  const [tab, setTab] = useState('general');
  const overview = useResource<FeaturesOverview>(overviewUrl(lang), 15000);
  const agent = overview.data?.features.find((item) => item.id === 'agent');
  const redAlert = overview.data?.features.find((item) => item.id === 'redalert');

  return (
    <div className="flex flex-col">
      <div className="px-4 pt-4 sm:px-6">
        <OSFilterTabs
          ariaLabel={t('settings_title')}
          selected={tab}
          onSelect={setTab}
          options={[
            { id: 'general', label: t('settings_tab_general') },
            { id: 'agent', label: t('settings_tab_agent') },
            { id: 'redalert', label: t('settings_tab_redalert') }
          ]}
        />
      </div>
      {tab === 'general' ? <SystemSettingsView t={t} lang={lang} onBack={onBack} /> : null}
      {tab === 'agent' && agent ? <div className="p-4 sm:p-6"><AgentSection feature={agent} t={t} onChanged={overview.reload} /></div> : null}
      {tab === 'redalert' && redAlert ? <div className="p-4 sm:p-6"><RedAlertSection feature={redAlert} t={t} onChanged={overview.reload} /></div> : null}
    </div>
  );
};
