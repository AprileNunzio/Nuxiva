import React, { FormEvent, useState } from 'react';
import { Ban, Radar, ShieldCheck } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, Field, List, Loading, Panel, Pill, Row, Stat, StatRow, Toggle, Unreachable, formatTime, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { blockAddress, confirmChange, rollbackChange, savePolicy, unblockAddress } from './api';
import { ConfirmBanner } from './components/ConfirmBanner';
import { RulesPanel } from './components/RulesPanel';
import { FirewallOverview } from './types';

const MODES = ['off', 'monitor', 'protect', 'lockdown'] as const;
const SEVERITY_TONE: Record<string, 'slate' | 'amber' | 'rose'> = { low: 'slate', medium: 'amber', high: 'rose', critical: 'rose' };

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/firewall');
  const { data, error, loading, reload } = useResource<FirewallOverview>('/api/firewall', 5000);
  const { busy, run } = useAction(reload);
  const [address, setAddress] = useState('');
  const [minutes, setMinutes] = useState(60);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const policy = data.policy;
  const change = (patch: Record<string, unknown>) => void run(() => savePolicy(patch), 'firewall_policy_failed');

  const block = async (event: FormEvent) => {
    event.preventDefault();
    if (!address.trim()) {
      return;
    }
    if ((await run(() => blockAddress(address.trim(), minutes, 'manual'), 'firewall_block_failed')) !== null) {
      setAddress('');
    }
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <ConfirmBanner
        deadline={data.status.confirm_by}
        busy={busy}
        message={t('confirm_message')}
        keep={t('confirm_keep')}
        undo={t('confirm_undo')}
        onConfirm={() => void run(confirmChange, 'firewall_confirm_failed')}
        onRollback={() => void run(rollbackChange, 'firewall_rollback_failed')}
      />
      <StatRow>
        <Stat label={t('stat_mode')} value={t(`mode_${policy.mode}`)} tone={policy.mode === 'off' ? 'slate' : 'emerald'} />
        <Stat label={t('stat_engine')} value={data.status.available ? t('available') : t('unavailable')} tone={data.status.available ? 'emerald' : 'amber'} />
        <Stat label={t('stat_rules')} value={data.rules.length} />
        <Stat label={t('stat_blocks')} value={data.blocks.length} tone="rose" />
      </StatRow>
      {data.status.error ? <Pill tone="rose">{data.status.error}</Pill> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('policy_title')} icon={<ShieldCheck className="h-4 w-4 text-emerald-700" aria-hidden="true" />}>
          <Field label={t('policy_mode')}>
            <select className={inputClass} value={policy.mode} disabled={busy} onChange={(event) => change({ mode: event.target.value })}>
              {MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {t(`mode_${mode}`)}
                </option>
              ))}
            </select>
          </Field>
          <p className="mt-2 text-xs text-slate-500">{t(`mode_${policy.mode}_hint`)}</p>
          <List>
            {(['allow_lan', 'allow_ping', 'auto_block', 'ai_analysis'] as const).map((key) => (
              <Row key={key} actions={<Toggle checked={policy[key]} disabled={busy} label={t(`policy_${key}`)} onChange={(value) => change({ [key]: value })} />}>
                {t(`policy_${key}`)}
              </Row>
            ))}
          </List>
        </Panel>
        <Panel title={t('blocks_title')} icon={<Ban className="h-4 w-4 text-rose-700" aria-hidden="true" />}>
          <form onSubmit={block} className="mb-3 flex flex-wrap gap-2">
            <input className={`${inputClass} flex-1`} value={address} onChange={(event) => setAddress(event.target.value)} placeholder={t('block_placeholder')} aria-label={t('block_placeholder')} />
            <select className={`${inputClass} w-32`} value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} aria-label={t('block_duration')}>
              {[15, 60, 1440, 0].map((value) => (
                <option key={value} value={value}>
                  {value === 0 ? t('forever') : t('minutes', { n: value })}
                </option>
              ))}
            </select>
            <Btn type="submit" tone="rose" busy={busy}>
              {t('block')}
            </Btn>
          </form>
          {data.blocks.length === 0 ? (
            <Empty>{t('blocks_empty')}</Empty>
          ) : (
            <List>
              {data.blocks.map((item) => (
                <Row key={item.address} actions={<Btn tone="slate" busy={busy} onClick={() => void run(() => unblockAddress(item.address), 'firewall_unblock_failed')}>{t('unblock')}</Btn>}>
                  <span className="font-mono text-xs">{item.address}</span>
                  <span className="ml-2 text-[11px] text-slate-500">{item.expires ? formatTime(item.expires, lang) : t('forever')} · {item.reason}</span>
                </Row>
              ))}
            </List>
          )}
        </Panel>
      </div>
      <RulesPanel rules={data.rules} busy={busy} t={t} run={run} />
      <Panel title={t('alerts_title')} icon={<Radar className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
        {data.alerts.length === 0 ? (
          <Empty>{data.engine.connected ? t('alerts_empty') : t('engine_offline')}</Empty>
        ) : (
          <List>
            {[...data.alerts].reverse().map((alert) => (
              <Row key={`${alert.at}-${alert.src}-${alert.kind}`} actions={<Pill tone={SEVERITY_TONE[alert.severity] ?? 'slate'}>{alert.severity}</Pill>}>
                <b>{alert.kind}</b>
                <span className="ml-2 font-mono text-xs text-slate-600">{alert.src} → {alert.dst}</span>
                <p className="text-[11px] text-slate-500">{formatTime(alert.at, lang)} · {alert.detail}</p>
              </Row>
            ))}
          </List>
        )}
      </Panel>
    </AppFrame>
  );
};

export default View;
