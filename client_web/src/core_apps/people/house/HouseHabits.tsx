import React, { useState } from 'react';
import { AlarmClock, Check, Clock, Eye, Lightbulb, ScanSearch, TriangleAlert, X } from 'lucide-react';
import { Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, formatTime } from '../../shared/kit';
import { useAction, useResource } from '../../shared/useResource';
import { usePeopleI18n } from '../scope';
import { analyse, decide } from './api';
import { HabitsOverview } from './types';

export const HouseHabits: React.FC = () => {
  const { t, lang } = usePeopleI18n();
  const { data, error, loading, reload } = useResource<HabitsOverview>('/api/habits', 10000);
  const { busy, run } = useAction(reload);
  const [note, setNote] = useState('');

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'house_unreachable' : 'loading')} />;
  }

  const open = data.suggestions.filter((item) => item.status === 'new');
  const closed = data.suggestions.filter((item) => item.status !== 'new');

  const scan = async () => {
    const out = await run(analyse, 'habits_analyse_failed');
    setNote(out ? t('house_found', { n: out.found }) : '');
  };

  const answer = async (id: string, verdict: 'accept' | 'reject' | 'snooze') => {
    const out = await run(() => decide(id, verdict), 'habits_decide_failed');
    setNote(out ? out.message : '');
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-3xl text-sm text-slate-400">{t('house_description')}</p>
        <Btn busy={busy} onClick={() => void scan()}>
          <ScanSearch className="h-3.5 w-3.5" aria-hidden="true" />
          {t('house_analyse')}
        </Btn>
      </div>
      <StatRow>
        <Stat label={t('house_stat_state')} value={data.enabled ? t('house_on') : t('house_off')} tone={data.enabled ? 'emerald' : 'slate'} />
        <Stat label={t('house_stat_events')} value={data.events} />
        <Stat label={t('house_stat_proposals')} value={open.length} tone="amber" />
        <Stat label={t('house_stat_foresight_hits')} value={data.foresight_hits} tone="purple" />
      </StatRow>
      {note ? <Pill tone="emerald">{note}</Pill> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('house_proposals_title')} icon={<Lightbulb className="h-4 w-4 text-amber-300" aria-hidden="true" />}>
          {open.length === 0 ? (
            <Empty>{t('house_proposals_empty')}</Empty>
          ) : (
            <List>
              {open.map((item) => (
                <Row
                  key={item.id}
                  actions={
                    <>
                      <Btn tone="emerald" busy={busy} onClick={() => void answer(item.id, 'accept')} title={t('house_accept')}>
                        <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                      <Btn tone="slate" busy={busy} onClick={() => void answer(item.id, 'snooze')} title={t('house_snooze')}>
                        <AlarmClock className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                      <Btn tone="rose" busy={busy} onClick={() => void answer(item.id, 'reject')} title={t('house_reject')}>
                        <X className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                    </>
                  }
                >
                  <b>{item.automation?.name ?? item.entity}</b>
                  <p className="text-xs text-slate-400">{item.text}</p>
                  <p className="mt-1 text-[11px] text-slate-500">{t('house_evidence', { support: item.support, observed: item.observed, confidence: Math.round(item.confidence * 100) })}</p>
                </Row>
              ))}
            </List>
          )}
          {closed.length > 0 ? <p className="mt-3 text-xs text-slate-500">{t('house_closed', { n: closed.length })}</p> : null}
        </Panel>
        <Panel title={t('house_foresight_title')} icon={<Eye className="h-4 w-4 text-purple-300" aria-hidden="true" />}>
          {data.foresight.length === 0 ? (
            <Empty>{t('house_foresight_empty')}</Empty>
          ) : (
            <List>
              {data.foresight.map((item) => (
                <Row key={`${item.entity}-${item.state}`} actions={<Pill tone="purple">{Math.round(item.confidence * 100)}%</Pill>}>
                  <b className="font-mono text-xs">{item.entity}</b>
                  <span className="ml-2 text-xs text-slate-400">→ {item.state}</span>
                  <p className="text-[11px] text-slate-500"><Clock className="mr-1 inline h-3 w-3" aria-hidden="true" />{formatTime(item.until, lang)} · {item.reason}</p>
                </Row>
              ))}
            </List>
          )}
        </Panel>
      </div>
      <Panel title={t('house_anomalies_title')} icon={<TriangleAlert className="h-4 w-4 text-rose-300" aria-hidden="true" />}>
        {data.anomalies.length === 0 ? (
          <Empty>{t('house_anomalies_empty')}</Empty>
        ) : (
          <List>
            {data.anomalies.map((item) => (
              <Row key={`${item.at}-${item.entity}`}>
                <span className="text-[11px] text-slate-500">{formatTime(item.at, lang)}</span>
                <p className="text-sm">{item.text}</p>
              </Row>
            ))}
          </List>
        )}
      </Panel>
    </div>
  );
};
