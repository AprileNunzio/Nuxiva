import React, { FormEvent, useState } from 'react';
import { Boxes, FlaskConical, History } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, Field, List, Loading, Panel, Pill, Row, Stat, StatRow, Toggle, Unreachable, formatTime, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { saveRules, simulate } from './api';
import { SimulationResult, TwinOverview } from './types';

const SERVICE = /^[a-z_]+\.[a-z_]+$/;
const ENTITY = /^[a-z_]+\.[a-z0-9_]+$/;

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/twin');
  const { data, error, loading, reload } = useResource<TwinOverview>('/api/twin', 15000);
  const { busy, run } = useAction(reload);
  const [service, setService] = useState('light.turn_off');
  const [entities, setEntities] = useState('');
  const [verdict, setVerdict] = useState<SimulationResult | null>(null);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const toggle = (rule: string, value: boolean) => void run(() => saveRules({ ...data.rules, [rule]: value }), 'twin_rules_failed');
  const list = entities.split(/[\s,]+/).filter(Boolean);
  const valid = SERVICE.test(service) && list.length > 0 && list.every((entity) => ENTITY.test(entity));

  const test = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    setVerdict(await run(() => simulate(service, list), 'twin_simulate_failed'));
  };

  const active = data.available.filter((rule) => data.rules[rule]).length;

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_mode')} value={t(`mode_${data.mode}`)} tone={data.mode === 'enforce' ? 'emerald' : 'amber'} />
        <Stat label={t('stat_rules')} value={`${active}/${data.available.length}`} />
        <Stat label={t('stat_verdicts')} value={data.history.length} tone="rose" />
      </StatRow>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('rules_title')} icon={<Boxes className="h-4 w-4 text-purple-700" aria-hidden="true" />}>
          <List>
            {data.available.map((rule) => (
              <Row key={rule} actions={<Toggle checked={data.rules[rule] === true} disabled={busy} onChange={(value) => toggle(rule, value)} label={t(`rule_${rule}`)} />}>
                <b>{t(`rule_${rule}`)}</b>
                <p className="text-xs text-slate-500">{t(`rule_${rule}_hint`)}</p>
              </Row>
            ))}
          </List>
        </Panel>
        <Panel title={t('simulate_title')} icon={<FlaskConical className="h-4 w-4 text-cyan-700" aria-hidden="true" />}>
          <form onSubmit={test} className="flex flex-col gap-3">
            <Field label={t('service')}>
              <input className={inputClass} value={service} onChange={(event) => setService(event.target.value)} placeholder="light.turn_off" />
            </Field>
            <Field label={t('entities')}>
              <input className={inputClass} value={entities} onChange={(event) => setEntities(event.target.value)} placeholder="camera.ingresso, lock.porta" />
            </Field>
            <Btn type="submit" busy={busy} disabled={!valid}>
              {t('simulate')}
            </Btn>
          </form>
          {verdict ? (
            <div className="mt-3 flex flex-col gap-2">
              <Pill tone={verdict.blocked ? 'rose' : verdict.conflicts.length ? 'amber' : 'emerald'}>
                {verdict.blocked ? t('verdict_blocked') : verdict.conflicts.length ? t('verdict_warn') : t('verdict_ok')}
              </Pill>
              {verdict.conflicts.map((conflict) => (
                <p key={`${conflict.rule}-${conflict.culprits.join()}`} className="text-xs text-slate-700">
                  {t(`rule_${conflict.rule}`)}: {conflict.culprits.join(', ')}
                </p>
              ))}
            </div>
          ) : null}
        </Panel>
      </div>
      <Panel title={t('history_title')} icon={<History className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
        {data.history.length === 0 ? (
          <Empty>{t('history_empty')}</Empty>
        ) : (
          <List>
            {data.history.map((entry, index) => (
              <Row key={`${entry.at}-${index}`} actions={<Pill tone={entry.blocked ? 'rose' : 'amber'}>{entry.blocked ? t('verdict_blocked') : t('verdict_warn')}</Pill>}>
                <span className="text-xs text-slate-500">{formatTime(entry.at, lang)} · {entry.source}</span>
                <p className="truncate">{entry.text}</p>
                <p className="text-xs text-slate-600">{entry.conflicts.map((conflict) => t(`rule_${conflict.rule}`)).join(' · ')}</p>
              </Row>
            ))}
          </List>
        )}
      </Panel>
    </AppFrame>
  );
};

export default View;
