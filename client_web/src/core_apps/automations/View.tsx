import React from 'react';
import { Copy, History, Play, Trash2, Workflow, Square } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Toggle, Unreachable, formatTime } from '../shared/kit';
import { asList } from '../shared/http';
import { useAction, useResource } from '../shared/useResource';
import { deleteAutomation, duplicateAutomation, fromTemplate, runAutomation, stopRun, toggleAutomation } from './api';
import { Composer } from './components/Composer';
import { AutomationTemplate, AutomationsOverview } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/automations');
  const { data, error, loading, reload } = useResource<AutomationsOverview>('/api/automations', 4000);
  const catalog = useResource<{ templates: AutomationTemplate[] }>('/api/automations/catalog');
  const { busy, run } = useAction(reload);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const templates = asList<AutomationTemplate>(catalog.data?.templates);

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_engine')} value={data.enabled ? t('on') : t('off')} tone={data.enabled ? 'emerald' : 'slate'} />
        <Stat label={t('stat_total')} value={data.automations.length} />
        <Stat label={t('stat_enabled')} value={data.automations.filter((item) => item.enabled).length} tone="emerald" />
        <Stat label={t('stat_running')} value={data.active.length} tone="amber" />
      </StatRow>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel title={t('list_title')} icon={<Workflow className="h-4 w-4 text-amber-300" aria-hidden="true" />}>
          {data.automations.length === 0 ? (
            <Empty>{t('list_empty')}</Empty>
          ) : (
            <List>
              {data.automations.map((item) => (
                <Row
                  key={item.id}
                  actions={
                    <>
                      <Toggle checked={item.enabled} disabled={busy} label={t('enabled')} onChange={(value) => void run(() => toggleAutomation(item.id, value), 'automations_toggle_failed')} />
                      <Btn tone="emerald" busy={busy} onClick={() => void run(() => runAutomation(item.id), 'automations_run_failed')} title={t('run')}>
                        <Play className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                      <Btn tone="slate" busy={busy} onClick={() => void run(() => duplicateAutomation(item.id), 'automations_duplicate_failed')} title={t('duplicate')}>
                        <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                      <Btn tone="rose" busy={busy} onClick={() => void run(() => deleteAutomation(item.id), 'automations_delete_failed')} title={t('delete')}>
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </Btn>
                    </>
                  }
                >
                  <b>{item.name}</b>
                  {item.description ? <p className="text-xs text-slate-400">{item.description}</p> : null}
                  <p className="mt-1 text-[11px] text-slate-500">
                    {t('runs', { n: item.runs ?? 0 })}
                    {item.last_run ? ` · ${formatTime(item.last_run, lang)} · ${item.last_status ?? ''}` : ''}
                    {item.last_error ? ` · ${item.last_error}` : ''}
                  </p>
                </Row>
              ))}
            </List>
          )}
        </Panel>
        <div className="flex min-w-0 flex-col gap-4">
          <Composer busy={busy} t={t} run={run} />
          {templates.length > 0 ? (
            <Panel title={t('templates_title')}>
              <List>
                {templates.map((template) => (
                  <Row key={template.index} actions={<Btn busy={busy} onClick={() => void run(() => fromTemplate(template.index), 'automations_template_failed')}>{t('use')}</Btn>}>
                    <b>{template.name}</b>
                    <p className="text-xs text-slate-400">{template.description}</p>
                  </Row>
                ))}
              </List>
            </Panel>
          ) : null}
        </div>
      </div>
      <Panel title={t('runs_title')} icon={<History className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
        {data.active.length + data.recent.length === 0 ? (
          <Empty>{t('runs_empty')}</Empty>
        ) : (
          <List>
            {[...data.active, ...data.recent].map((item) => (
              <Row
                key={item.id}
                actions={
                  item.ended === null ? (
                    <Btn tone="rose" busy={busy} onClick={() => void run(() => stopRun(item.id), 'automations_stop_failed')} title={t('stop')}>
                      <Square className="h-3.5 w-3.5" aria-hidden="true" />
                    </Btn>
                  ) : undefined
                }
              >
                <b>{item.name}</b>
                <Pill tone={item.error ? 'rose' : item.ended === null ? 'amber' : 'emerald'}>{item.status}</Pill>
                <span className="ml-2 text-[11px] text-slate-500">{formatTime(item.started, lang)} · {t('steps', { n: item.steps })} · {item.ms} ms</span>
                {item.error ? <p className="text-xs text-rose-300">{item.error}</p> : null}
              </Row>
            ))}
          </List>
        )}
      </Panel>
    </AppFrame>
  );
};

export default View;
