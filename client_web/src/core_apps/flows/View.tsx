import React, { useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Field, Loading, Panel, Stat, StatRow, Unreachable, gridClass, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { discardDraft, publish, rollback, saveDraft } from './api';
import { NodeCard } from './components/NodeCard';
import { Versions } from './components/Versions';
import { FlowStudio } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/flows');
  const { data, error, loading, reload } = useResource<FlowStudio>('/api/flows/studio');
  const { busy, run } = useAction(reload);
  const [password, setPassword] = useState('');

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const pending = Object.keys(data.pending).length;
  const total = data.estimate.reduce((sum, step) => sum + step.seconds, 0);

  const pick = (node: string, algorithm: string) => void run(() => saveDraft({ ...data.draft.picks, [node]: algorithm }), 'flows_draft_failed');
  const apply = async (task: (secret: string) => Promise<unknown>, code: string) => {
    if (password && (await run(() => task(password), code)) !== null) {
      setPassword('');
    }
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_pending')} value={pending} tone={pending ? 'amber' : 'slate'} />
        <Stat label={t('stat_estimate')} value={`${total.toFixed(2)} s`} />
        <Stat label={t('stat_speed')} value={data.traits.draft.speed.toFixed(1)} tone="emerald" />
        <Stat label={t('stat_quality')} value={data.traits.draft.quality.toFixed(1)} tone="purple" />
        <Stat label={t('stat_privacy')} value={data.traits.draft.privacy.toFixed(1)} tone="cyan" />
        <Stat label={t('stat_saving')} value={data.traits.draft.saving.toFixed(1)} tone="amber" />
      </StatRow>
      <Panel title={t('templates')}>
        <div className="flex flex-wrap gap-2">
          {Object.entries(data.templates).map(([key, item]) => (
            <Btn key={key} tone={data.draft.template === key ? 'emerald' : 'slate'} busy={busy} title={item.hint} onClick={() => void run(() => saveDraft(item.picks, key), 'flows_draft_failed')}>
              {item.name}
            </Btn>
          ))}
        </div>
      </Panel>
      <div className={gridClass}>
        <Panel title={t('nodes')} className="lg:col-span-2 3xl:col-span-2">
          <ul className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {data.nodes.map((node) => (
              <NodeCard key={node.id} node={node} picked={data.draft.picks[node.id] ?? ''} changed={data.draft.picks[node.id] !== data.current[node.id]} disabled={busy || node.locked} t={t} onPick={(algorithm) => pick(node.id, algorithm)} />
            ))}
          </ul>
        </Panel>
        <Panel title={t('publish_title')}>
          <p className="mb-3 text-xs text-slate-400">{t('publish_hint')}</p>
          <Field label={t('password')}>
            <input className={inputClass} type="password" autoComplete="current-password" value={password} maxLength={200} onChange={(event) => setPassword(event.target.value)} />
          </Field>
          <div className="mt-3 flex flex-wrap gap-2">
            <Btn tone="emerald" busy={busy} disabled={!password || pending === 0} onClick={() => void apply(publish, 'flows_publish_failed')}>
              {t('publish')}
            </Btn>
            <Btn tone="slate" busy={busy} disabled={pending === 0} onClick={() => void run(discardDraft, 'flows_discard_failed')}>
              {t('discard')}
            </Btn>
          </div>
          <h3 className="mb-2 mt-5 text-xs font-bold uppercase tracking-wider text-slate-400">{t('versions')}</h3>
          <Versions versions={data.versions} lang={lang} busy={busy || !password} t={t} onRollback={(version) => void apply((secret) => rollback(version, secret), 'flows_rollback_failed')} />
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
