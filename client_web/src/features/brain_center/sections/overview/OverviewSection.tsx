import React from 'react';
import { AlertTriangle, ArrowRight, Cpu, Timer } from 'lucide-react';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { SectionId } from '../../shell/sections';
import { Badge, Button, Card, FLUID, Loading, Row, SectionHeader } from '../../ui/primitives';
import { PRIMARY_ROLES, roleIcon } from '../../ui/roleIcons';
import { NowCard } from './NowCard';
import { PresetsCard } from './PresetsCard';
import { UsageGlance } from './UsageGlance';

export const OverviewSection: React.FC<{ readonly onNavigate: (id: SectionId) => void }> = ({ onNavigate }) => {
  const { t } = useSectionText('overview');
  const base = useBrainText();
  const { overview } = useBrain();
  if (!overview) {
    return <Loading label={base.t('loading')} />;
  }
  const byId = new Map(overview.roles.map((role) => [role.id, role]));
  const missing = overview.roles.filter((role) => role.active === null);
  const hw = overview.hardware;

  return (
    <>
      <SectionHeader title={t('title')} description={t('description')} />
      <div className={`grid items-stretch gap-4 ${FLUID.md}`}>
        {PRIMARY_ROLES.map((id) => (
          <NowCard key={id} kind={id} role={byId.get(id) ?? null} onChange={() => onNavigate('contexts')} />
        ))}
      </div>
      <Card title={t('other_contexts')} flush actions={<Button compact variant="ghost" icon={ArrowRight} onClick={() => onNavigate('contexts')}>{t('manage')}</Button>}>
        <div className={`grid ${FLUID.sm}`}>
        {overview.roles
          .filter((role) => !PRIMARY_ROLES.includes(role.id))
          .map((role) => (
            <Row
              key={role.id}
              icon={roleIcon(role.id)}
              title={base.t(`role_${role.id}`)}
              description={role.active ? role.active.model : base.t('none_available')}
              trailing={role.active ? <Badge tone={role.active.origin === 'cloud' ? 'info' : 'success'}>{base.t(`origin_${role.active.origin}`)}</Badge> : <Badge tone="warning">{base.t('unavailable')}</Badge>}
            />
          ))}
        </div>
      </Card>
      <PresetsCard />
    </>
  );
};
