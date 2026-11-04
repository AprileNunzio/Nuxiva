import React, { useEffect } from 'react';
import { HardDrive, ShieldCheck, User } from 'lucide-react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { useBrainText, useSectionText } from '../../core/i18n';
import { PolicyChoice, PrivacyOverview, fetchPrivacy, saveDefaultPrivacy, savePersonPrivacy } from '../../core/privacyApi';
import { useBrain } from '../../core/useBrainStore';
import { SectionId } from '../../shell/sections';
import { Badge, Button, Card, Empty, FLUID, Loading, Row, SectionHeader } from '../../ui/primitives';
import { AuditCard } from './AuditCard';
import { PolicyPicker } from './PolicyPicker';

const EngineCard: React.FC<{ readonly data: PrivacyOverview; readonly onNavigate: (id: SectionId) => void }> = ({ data, onNavigate }) => {
  const { t } = useSectionText('privacy');
  const ready = data.engine.model !== '' && data.engine.origin === 'local';
  const state = data.engine.model === '' ? 'none' : data.engine.origin;
  return (
    <Card title={t('engine_title')} description={t('engine_hint')}>
      <Row
        icon={HardDrive}
        title={
          <>
            {data.engine.model || t('engine_no_model')}
            <Badge tone={ready ? 'success' : 'warning'}>{t(`engine_${state}`)}</Badge>
          </>
        }
        description={t(`engine_${state}_hint`)}
        trailing={
          ready ? undefined : (
            <Button compact onClick={() => onNavigate('local_models')}>
              {t('engine_setup')}
            </Button>
          )
        }
      />
    </Card>
  );
};

export const PrivacySection: React.FC<{ readonly onNavigate: (id: SectionId) => void }> = ({ onNavigate }) => {
  const { t } = useSectionText('privacy');
  const base = useBrainText();
  const { run, action, version } = useBrain();
  const privacy = usePolled(fetchPrivacy, 'brain_privacy_unavailable', true, 30000);
  const { refresh, setData } = privacy;
  useEffect(() => {
    if (version > 0) refresh();
  }, [version, refresh]);
  const data = privacy.data;
  if (!data) {
    return <Loading label={base.t('loading')} />;
  }

  const save = async (key: string, task: () => Promise<PrivacyOverview>) => {
    const result = await run(key, 'brain_privacy_failed', task);
    if (result) setData(result);
  };
  const busy = action.busy !== null;

  return (
    <>
      <SectionHeader title={t('title')} description={t('description')} />
      <div className={`grid items-start gap-4 ${FLUID.xl}`}>
        <EngineCard data={data} onNavigate={onNavigate} />
        <Card title={t('default_title')} description={t('default_hint')}>
          <PolicyPicker
            fallback="auto"
            current={data.automatic ? null : data.policy}
            inherited={data.suggested}
            busy={action.busy === 'privacy:default'}
            disabled={busy}
            onSave={(choice: PolicyChoice) => void save('privacy:default', () => saveDefaultPrivacy(choice))}
          />
        </Card>
      </div>
      <Card title={t('people_title')} description={t('people_hint')} flush>
        {data.people.length === 0 ? (
          <div className="p-4"><Empty>{t('people_empty')}</Empty></div>
        ) : (
          data.people.map((person) => (
            <Row
              key={person.slug}
              icon={person.owner ? ShieldCheck : User}
              title={
                <>
                  {person.name}
                  <Badge tone={person.policy ? 'info' : 'neutral'}>{person.policy ? t(`profile_${person.policy.profile}`) : t('profile_inherit')}</Badge>
                </>
              }
            >
              <PolicyPicker
                fallback="inherit"
                current={person.policy}
                inherited={data.policy}
                busy={action.busy === `privacy:${person.slug}`}
                disabled={busy}
                onSave={(choice: PolicyChoice) => void save(`privacy:${person.slug}`, () => savePersonPrivacy(person.slug, choice))}
              />
            </Row>
          ))
        )}
      </Card>
      <AuditCard data={data} />
    </>
  );
};
