import React, { useState } from 'react';
import { Btn, Empty, List, Panel, Pill, Row, Stat, StatRow, Toggle } from '../shared/kit';
import { killSwitch, refreshInventory, resetLedger, setMode } from './api';
import { MODES } from './types';
import type { Mode } from './types';
import type { EngineModel } from './useEngine';

const TONE = { off: 'slate', shadow: 'amber', active: 'emerald' } as const;

export function OverviewTab({ model: m }: { model: EngineModel }) {
  const { t, status } = m;
  const [force, setForce] = useState(false);
  if (!status) return <Empty>{t('loading')}</Empty>;
  if (!status.native) return <Empty>{t('native_missing')}</Empty>;
  const gate = status.gate;
  const current = status.switch?.mode ?? 'off';
  const act = (fn: () => Promise<unknown>) => void m.run(fn).then(() => m.statusResource.reload());
  const choose = (mode: Mode) => act(() => setMode(mode, mode === 'active' && force));
  return (
    <div className="flex flex-col gap-4">
      {status.emergency_off ? <Empty>{t('emergency_off')}</Empty> : null}
      <Panel title={t('mode_title')} actions={<Pill tone={TONE[current]}>{t(`mode_${current}`)}</Pill>}>
        <p className="mb-3 text-xs text-on-surface-variant">{t(`mode_${current}_hint`)}{status.switch?.forced ? ` ${t('forced_hint')}` : ''}</p>
        <div className="flex flex-wrap items-center gap-2">
          {MODES.map(mode => (
            <Btn key={mode} busy={m.busy} disabled={mode === current || (mode === 'active' && !gate?.ready && !force)} tone={TONE[mode]} onClick={() => choose(mode)}>
              {t(`set_${mode}`)}
            </Btn>
          ))}
          <Btn busy={m.busy} tone="rose" onClick={() => act(killSwitch)}>{t('kill')}</Btn>
        </div>
        {!gate?.ready ? (
          <label className="mt-3 flex items-center gap-3 text-xs text-on-surface-variant">
            <Toggle checked={force} onChange={setForce} label={t('force')} />
            <span>{t('force')}</span>
          </label>
        ) : null}
      </Panel>
      <Panel title={t('gate_title')} actions={<Pill tone={gate?.ready ? 'emerald' : 'amber'}>{t(gate?.ready ? 'gate_open' : 'gate_closed')}</Pill>}>
        <StatRow>
          <Stat label={t('days')} value={`${gate?.days ?? 0} / ${status.config?.gate.min_days ?? 0}`} />
          <Stat label={t('samples')} value={`${gate?.samples ?? 0} / ${status.config?.gate.min_samples ?? 0}`} />
          <Stat label={t('agreement')} value={m.percent(gate?.agreement_bps)} tone="emerald" />
          <Stat label={t('invalid')} value={m.percent(gate?.invalid_bps)} tone="amber" />
          <Stat label={t('wrong_action')} value={gate?.wrong_action ?? 0} tone="rose" />
        </StatRow>
        {gate && gate.reasons.length > 0 ? (
          <List>{gate.reasons.map(reason => <Row key={reason}>{t(reason.split('.').join('_'))}</Row>)}</List>
        ) : null}
        <div className="mt-3"><Btn busy={m.busy} tone="slate" onClick={() => act(resetLedger)}>{t('reset_ledger')}</Btn></div>
      </Panel>
      <Panel title={t('inventory_title')}>
        <StatRow>
          <Stat label={t('capabilities')} value={status.capabilities ?? 0} />
          <Stat label={t('inferred')} value={status.inventory?.inferred ?? 0} tone="amber" />
          <Stat label={t('generation')} value={status.generation ?? 0} tone="purple" />
          <Stat label={t('cache')} value={`${status.cache?.hits ?? 0} / ${(status.cache?.hits ?? 0) + (status.cache?.misses ?? 0)}`} tone="emerald" />
        </StatRow>
        <p className="my-3 text-xs text-on-surface-variant">{t('inferred_hint')}</p>
        <Btn busy={m.busy} onClick={() => act(refreshInventory)}>{t('refresh_inventory')}</Btn>
      </Panel>
    </div>
  );
}
