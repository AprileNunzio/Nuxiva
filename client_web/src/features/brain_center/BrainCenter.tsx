import React, { useCallback, useState } from 'react';
import { useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
import { BrainStoreContext, useBrainStore } from './core/useBrainStore';
import { Shell } from './shell/Shell';
import { SectionId } from './shell/sections';
import { AdvancedSection } from './sections/advanced/AdvancedSection';
import { ContextsSection } from './sections/contexts/ContextsSection';
import { FunctionsSection } from './sections/functions/FunctionsSection';
import { LocalModelsSection } from './sections/local_models/LocalModelsSection';
import { OverviewSection } from './sections/overview/OverviewSection';
import { ProvidersSection } from './sections/providers/ProvidersSection';
import { UsageSection } from './sections/usage/UsageSection';

const SECTIONS: Readonly<Record<SectionId, React.FC<{ readonly onNavigate: (id: SectionId) => void }>>> = {
  overview: OverviewSection,
  contexts: ContextsSection,
  providers: ProvidersSection,
  local_models: LocalModelsSection,
  usage: UsageSection,
  functions: FunctionsSection,
  advanced: AdvancedSection,
};

export const BrainCenter: React.FC<{ readonly initial?: SectionId }> = ({ initial = 'overview' }) => {
  const store = useBrainStore(true);
  const [section, setSection] = useState<SectionId>(initial);
  const { refresh } = store;
  useWindowToolbar(useCallback((id: string) => id === 'refresh' && refresh(), [refresh]));
  const Active = SECTIONS[section];
  return (
    <BrainStoreContext.Provider value={store}>
      <Shell active={section} onSelect={setSection}>
        <Active onNavigate={setSection} />
      </Shell>
    </BrainStoreContext.Provider>
  );
};

export default BrainCenter;
