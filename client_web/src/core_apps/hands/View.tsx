import React, { useEffect, useState } from 'react';
import { RotateCcw, Save } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { FeaturePanel } from '../shared/FeaturePanel';
import { AppFrame, Btn, Loading, Stat, StatRow, Unreachable } from '../shared/kit';
import { useFeature } from '../shared/useFeature';
import { useAction, useResource } from '../shared/useResource';
import { HANDS_PROFILE_URL, resetProfile, saveProfile } from './api';
import { BindingsPanel } from './BindingsPanel';
import { RecentPanel } from './RecentPanel';
import { SensitivityPanel } from './SensitivityPanel';
import { GestureProfile, HANDS_FEATURE_ID, HandsView, IDENTIFIER } from './types';

const isProfile = (value: HandsView['profile'] | undefined): value is GestureProfile =>
  Boolean(value && Array.isArray((value as GestureProfile).bindings));

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/hands');
  const { feature, error, loading, reload } = useFeature(HANDS_FEATURE_ID);
  const engine = useResource<HandsView>(HANDS_PROFILE_URL);
  const [draft, setDraft] = useState<GestureProfile | null>(null);
  const [dirty, setDirty] = useState(false);
  const { busy, run } = useAction(reload);

  useEffect(() => {
    if (!dirty && isProfile(engine.data?.profile)) {
      setDraft(engine.data.profile);
    }
  }, [engine.data, dirty]);

  if ((loading && !feature) || (engine.loading && !engine.data)) {
    return <Loading label={t('loading')} />;
  }
  if (!feature) {
    return <Unreachable label={t(error ? 'unreachable' : 'missing')} />;
  }

  const view = engine.data;
  const edit = (next: GestureProfile) => {
    setDraft(next);
    setDirty(true);
  };
  const valid = draft ? draft.bindings.every((b) => IDENTIFIER.test(b.action)) : false;
  const persist = (task: () => Promise<HandsView>) =>
    void run(async () => {
      const next = await task();
      setDirty(false);
      if (isProfile(next.profile)) setDraft(next.profile);
      engine.reload();
    }, 'hands_profile_failed');

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={() => {
        setDirty(false);
        reload();
        engine.reload();
      }}
      actions={
        view?.native && draft ? (
          <>
            <Btn tone="slate" busy={busy} onClick={() => persist(resetProfile)}>
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              {t('reset')}
            </Btn>
            <Btn tone="emerald" busy={busy} disabled={!dirty || !valid} onClick={() => persist(() => saveProfile(draft))}>
              <Save className="h-3.5 w-3.5" aria-hidden="true" />
              {t('save')}
            </Btn>
          </>
        ) : null
      }
    >
      <StatRow>
        <Stat label={t('stat_state')} value={feature.state.enabled ? t('running') : t('stopped')} tone={feature.state.enabled ? 'emerald' : 'slate'} />
        <Stat label={t('stat_engine')} value={view?.native ? t('engine_rust') : t('engine_js')} tone={view?.native ? 'cyan' : 'amber'} />
        <Stat label={t('stat_gestures')} value={view?.catalog.length ?? 0} />
        <Stat label={t('stat_rules')} value={draft?.bindings.filter((b) => b.enabled).length ?? 0} />
      </StatRow>
      {dirty ? <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">{t('unsaved')}</p> : null}
      {view && !view.native ? <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">{t('native_missing')}</p> : null}
      <FeaturePanel feature={feature} busy={busy} t={t} run={run} />
      {view && draft ? (
        <>
          <BindingsPanel
            t={t}
            bindings={draft.bindings}
            catalog={view.catalog}
            actions={view.actions}
            contexts={view.contexts}
            onChange={(bindings) => edit({ ...draft, bindings })}
          />
          <div className="grid gap-4 xl:grid-cols-2">
            <SensitivityPanel t={t} profile={draft} onChange={edit} />
            <RecentPanel t={t} />
          </div>
        </>
      ) : null}
    </AppFrame>
  );
};

export default View;
