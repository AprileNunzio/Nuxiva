import React from 'react';
import { KeyRound, Users } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Empty, List, Loading, Panel, Pill, Stat, StatRow, Unreachable } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { PersonCard } from './components/PersonCard';
import { GoogleOverview } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/google');
  const { data, error, loading, reload } = useResource<GoogleOverview>('/api/google', 15000);
  const { busy, run } = useAction(reload);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const linked = data.people.filter((person) => person.linked).length;

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_state')} value={data.enabled ? t('on') : t('off')} tone={data.enabled ? 'emerald' : 'slate'} />
        <Stat label={t('stat_credentials')} value={data.has_credentials ? t('configured') : t('missing')} tone={data.has_credentials ? 'emerald' : 'amber'} />
        <Stat label={t('stat_linked')} value={`${linked}/${data.people.length}`} />
        <Stat label={t('stat_services')} value={data.services.length} tone="purple" />
      </StatRow>
      {!data.has_credentials ? (
        <Panel title={t('credentials_title')} icon={<KeyRound className="h-4 w-4 text-amber-300" aria-hidden="true" />}>
          <p className="text-sm text-slate-300">{t('credentials_help')}</p>
          <p className="mt-2 break-all font-mono text-xs text-slate-500">{t('redirect_hint', { uri: data.redirect_uri })}</p>
        </Panel>
      ) : null}
      <Panel title={t('people_title')} icon={<Users className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
        {data.people.length === 0 ? (
          <Empty>{t('people_empty')}</Empty>
        ) : (
          <List>
            {data.people.map((person) => (
              <PersonCard
                key={person.slug}
                person={person}
                services={data.services}
                defaults={data.default_services}
                waiting={data.pending.some((item) => item.slug === person.slug)}
                busy={busy}
                canLink={data.has_credentials && data.enabled}
                t={t}
                run={run}
              />
            ))}
          </List>
        )}
        {data.pending.length > 0 ? <div className="mt-3"><Pill tone="amber">{t('pending', { n: data.pending.length })}</Pill></div> : null}
      </Panel>
    </AppFrame>
  );
};

export default View;
