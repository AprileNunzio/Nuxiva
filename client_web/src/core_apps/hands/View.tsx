import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { FeaturePanel } from '../shared/FeaturePanel';
import { AppFrame, List, Loading, Panel, Stat, StatRow, Unreachable } from '../shared/kit';
import { useFeature } from '../shared/useFeature';
import { useAction } from '../shared/useResource';
import { HANDS_FEATURE_ID, HandsSettingKey } from './types';

const FPS: HandsSettingKey = 'NUXIVA_HANDS_FPS';
const COUNT: HandsSettingKey = 'NUXIVA_HANDS_COUNT';
const BUDGET: HandsSettingKey = 'NUXIVA_HANDS_MAX_MS';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/hands');
  const { feature, error, loading, reload } = useFeature(HANDS_FEATURE_ID);
  const { busy, run } = useAction(reload);

  if (loading && !feature) {
    return <Loading label={t('loading')} />;
  }
  if (!feature) {
    return <Unreachable label={t(error ? 'unreachable' : 'missing')} />;
  }

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_state')} value={feature.state.enabled ? t('running') : t('stopped')} tone={feature.state.enabled ? 'emerald' : 'slate'} />
        <Stat label={t('stat_fps')} value={feature.values[FPS] || '20'} />
        <Stat label={t('stat_hands')} value={feature.values[COUNT] || '2'} />
        <Stat label={t('stat_budget')} value={`${feature.values[BUDGET] || '50'} ms`} />
      </StatRow>
      <FeaturePanel feature={feature} busy={busy} t={t} run={run} />
      <Panel title={t('gestures')}>
        <List>
          {feature.capabilities.map((capability) => (
            <li key={capability} className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-300">
              {capability}
            </li>
          ))}
        </List>
      </Panel>
    </AppFrame>
  );
};

export default View;
