import React, { useMemo } from 'react';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { BrainRef } from '../../core/types';
import { FLUID, Loading, SectionHeader } from '../../ui/primitives';
import { PRIMARY_ROLES } from '../../ui/roleIcons';
import { EverywhereCard } from '../everywhere/EverywhereCard';
import { ContextCard } from './ContextCard';
import { RouteTester } from './RouteTester';
import { RoutingCard } from './RoutingCard';

export const ContextsSection: React.FC = () => {
  const { t } = useSectionText('contexts');
  const base = useBrainText();
  const { overview, pool } = useBrain();
  const known = useMemo(() => {
    const map = new Map<string, BrainRef>();
    pool.forEach((item) => map.set(item.ref, item));
    overview?.roles.forEach((role) => role.entries.forEach((entry) => map.set(entry.ref, entry)));
    return map;
  }, [overview, pool]);

  if (!overview) {
    return <Loading label={base.t('loading')} />;
  }
  const ordered = [...overview.roles].sort((a, b) => Number(!PRIMARY_ROLES.includes(a.id)) - Number(!PRIMARY_ROLES.includes(b.id)));
  return (
    <>
      <SectionHeader title={t('title')} description={t('description')} />
      <EverywhereCard />
      <div className={`grid items-start gap-4 ${FLUID.xl}`}>
        <RoutingCard routing={overview.routing} />
        <RouteTester />
      </div>
      <div className={`grid items-start gap-4 ${FLUID.lg}`}>
        {ordered.map((role) => (
          <ContextCard key={role.id} role={role} known={known} />
        ))}
      </div>
    </>
  );
};
