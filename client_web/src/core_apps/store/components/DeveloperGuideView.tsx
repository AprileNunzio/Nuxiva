import React, { useState } from 'react';
import { GuideNavHeader } from './developer_guide/GuideNavHeader';
import { GuideOverviewSection } from './developer_guide/GuideOverviewSection';
import { GuideStepsSection } from './developer_guide/GuideStepsSection';
import { GuideManifestSection } from './developer_guide/GuideManifestSection';
import { GuideCodeTemplatesSection } from './developer_guide/GuideCodeTemplatesSection';
import { GuideBestPracticesSection } from './developer_guide/GuideBestPracticesSection';
import type { GuideSubTab } from './developer_guide/types';

interface DeveloperGuideViewProps {
  t: (key: string, params?: Record<string, any>) => string;
}

export const DeveloperGuideView: React.FC<DeveloperGuideViewProps> = ({ t }) => {
  const [activeSubTab, setActiveSubTab] = useState<GuideSubTab>('overview');

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <GuideNavHeader
        t={t}
        activeSubTab={activeSubTab}
        onSelectSubTab={setActiveSubTab}
      />

      {activeSubTab === 'overview' && <GuideOverviewSection t={t} />}
      {activeSubTab === 'steps' && <GuideStepsSection t={t} />}
      {activeSubTab === 'manifest' && <GuideManifestSection t={t} />}
      {activeSubTab === 'code' && <GuideCodeTemplatesSection t={t} />}
      {activeSubTab === 'best_practices' && <GuideBestPracticesSection t={t} />}
    </div>
  );
};
