import React from 'react';
import { AlertTriangle, ArrowRight, Cpu, Timer } from 'lucide-react';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { SectionId } from '../../shell/sections';
import { Badge, Button, Card, Loading, Row, SectionHeader } from '../../ui/primitives';
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
      <div className="grid gap-4 md:grid-cols-2">
        {PRIMARY_ROLES.map((id) => (
          <NowCard key={id} kind={id} role={byId.get(id) ?? null} onChange={() => onNavigate('contexts')} />
        ))}
      </div>
      {missing.length > 0 && (
        <div role="alert" className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 sm:flex-row sm:items-center">
          <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
          <p className="flex-1 text-sm text-amber-900">{t('missing', { list: missing.map((role) => base.t(`role_${role.id}`)).join(', ') })}</p>
          <Button compact onClick={() => onNavigate('contexts')}>
            {t('fix')}
          </Button>
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <UsageGlance onOpen={() => onNavigate('usage')} />
        <Card title={t('system_title')} flush>
          <Row
            icon={Timer}
            title={t('last_answer')}
            description={overview.last ? t('last_answer_value', { model: overview.last.ref.model, ms: Math.round(overview.last.ms) }) : t('last_answer_none')}
          />
          <Row
            icon={Cpu}
            title={t('machine')}
            description={[t('machine_ram', { ram: hw.ramGb }), hw.gpu ? t('machine_gpu', { gpu: hw.gpu, vram: hw.vramGb }) : t('machine_no_gpu')].join(' · ')}
          />
        </Card>
      </div>
      <Card title={t('other_contexts')} flush actions={<Button compact variant="ghost" icon={ArrowRight} onClick={() => onNavigate('contexts')}>{t('manage')}</Button>}>
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
      </Card>
      <PresetsCard />
    </>
  );
};
