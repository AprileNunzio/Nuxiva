import React, { FormEvent, useState } from 'react';
import { Crosshair, Globe2, Monitor, ShieldHalf } from 'lucide-react';
import { Btn, Empty, Field, List, Panel, Pill, Row, Toggle, formatTime, inputClass } from '../../shared/kit';
import { defend, refreshGeo, revokeDefense, savePolicy, showDefenseView } from '../api';
import { DefenseState, FirewallPolicy } from '../types';
import { Run, Translate } from './shared';

const AUTONOMY = ['observe', 'assist', 'autonomous'] as const;
const OPTIONS = ['tarpit', 'honeypot', 'quarantine', 'country_block', 'geo_updates'] as const;
const KINDS = ['block', 'tarpit', 'rate_limit', 'honeypot', 'quarantine', 'sinkhole', 'country_block'] as const;
const DURATIONS = [15, 60, 1440, 10080] as const;
const COUNTRY = /^[A-Za-z]{2}$/;
const POSTURE_TONE: Record<string, 'emerald' | 'amber' | 'rose'> = { calm: 'emerald', watch: 'amber', alert: 'rose', attack: 'rose' };

interface Props {
  readonly policy: FirewallPolicy;
  readonly state: DefenseState | null;
  readonly busy: boolean;
  readonly lang: string;
  readonly t: Translate;
  readonly run: Run;
  readonly reload: () => void;
}

export const DefensePanel: React.FC<Props> = ({ policy, state, busy, lang, t, run, reload }) => {
  const [kind, setKind] = useState<string>('block');
  const [target, setTarget] = useState('');
  const [minutes, setMinutes] = useState<number>(60);
  const [home, setHome] = useState(policy.home_countries.join(' '));

  const change = (patch: Record<string, unknown>) => void run(() => savePolicy(patch), 'firewall_policy_failed');
  const homeList = home.split(/[\s,]+/).filter(Boolean);
  const homeValid = homeList.length <= 32 && homeList.every((code) => COUNTRY.test(code));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = target.trim();
    if (!value || (kind === 'country_block' && !COUNTRY.test(value))) {
      return;
    }
    if ((await run(() => defend(kind, kind === 'country_block' ? value.toUpperCase() : value, minutes), 'firewall_defend_failed')) !== null) {
      setTarget('');
      reload();
    }
  };

  const posture = state?.posture ?? 'calm';
  return (
    <>
      <Panel title={t('defense_title')} icon={<ShieldHalf className="h-4 w-4 text-emerald-700" aria-hidden="true" />}>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Pill tone={POSTURE_TONE[posture] ?? 'slate'}>{t(`posture_${posture}`)}</Pill>
          <Btn tone="cyan" busy={busy} onClick={() => void run(() => showDefenseView(true), 'firewall_view_failed')}>
            <Monitor className="mr-1 inline h-4 w-4" aria-hidden="true" />
            {t('view_open')}
          </Btn>
          <Btn tone="slate" busy={busy} onClick={() => void run(() => showDefenseView(false), 'firewall_view_failed')}>
            {t('view_close')}
          </Btn>
        </div>
        <Field label={t('autonomy_label')}>
          <select className={inputClass} value={policy.autonomy} disabled={busy} onChange={(event) => change({ autonomy: event.target.value })}>
            {AUTONOMY.map((level) => (
              <option key={level} value={level}>
                {t(`autonomy_${level}`)}
              </option>
            ))}
          </select>
        </Field>
        <p className="mt-2 text-xs text-slate-500">{t(`autonomy_${policy.autonomy}_hint`)}</p>
        <List>
          {OPTIONS.map((key) => (
            <Row key={key} actions={<Toggle checked={policy[key]} disabled={busy} label={t(`option_${key}`)} onChange={(value) => change({ [key]: value })} />}>
              <b>{t(`option_${key}`)}</b>
              <p className="text-[11px] text-slate-500">{t(`option_${key}_hint`)}</p>
            </Row>
          ))}
        </List>
        <div className="mt-3 grid gap-3 cq-sm:grid-cols-2">
          <Field label={t('country_threshold')}>
            <input className={inputClass} type="number" min={1} max={1000} value={policy.country_threshold} disabled={busy}
              onChange={(event) => change({ country_threshold: Number(event.target.value) })} />
          </Field>
          <Field label={t('max_actions')}>
            <input className={inputClass} type="number" min={1} max={1000} value={policy.max_actions_per_hour} disabled={busy}
              onChange={(event) => change({ max_actions_per_hour: Number(event.target.value) })} />
          </Field>
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <div className="min-w-[12rem] flex-1">
            <Field label={t('home_countries')}>
              <input className={inputClass} value={home} maxLength={200} onChange={(event) => setHome(event.target.value.toUpperCase())} aria-invalid={!homeValid} />
            </Field>
          </div>
          <Btn tone="cyan" busy={busy} disabled={!homeValid} onClick={() => change({ home_countries: homeList })}>
            {t('save')}
          </Btn>
        </div>
        <p className="mt-1 text-xs text-slate-500">{t('home_countries_hint')}</p>
      </Panel>
      <Panel title={t('active_title')} icon={<Crosshair className="h-4 w-4 text-rose-700" aria-hidden="true" />}>
        <form onSubmit={submit} className="mb-3 flex flex-wrap gap-2">
          <select className={`${inputClass} w-44`} value={kind} onChange={(event) => setKind(event.target.value)} aria-label={t('defense_kind')}>
            {KINDS.map((item) => (
              <option key={item} value={item}>
                {t(`defense_${item}`)}
              </option>
            ))}
          </select>
          <input className={`${inputClass} flex-1`} value={target} maxLength={80} onChange={(event) => setTarget(event.target.value)}
            placeholder={t(kind === 'country_block' ? 'target_country' : 'target_address')} aria-label={t('defense_target')} />
          <select className={`${inputClass} w-32`} value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} aria-label={t('block_duration')}>
            {DURATIONS.map((value) => (
              <option key={value} value={value}>
                {t('minutes', { n: value })}
              </option>
            ))}
          </select>
          <Btn type="submit" tone="rose" busy={busy}>
            {t('defend')}
          </Btn>
        </form>
        {!state || state.responses.length === 0 ? (
          <Empty>{t('active_empty')}</Empty>
        ) : (
          <List>
            {state.responses.map((item) => (
              <Row key={item.key} actions={<Btn tone="slate" busy={busy} onClick={() => void run(() => revokeDefense(item.key), 'firewall_revoke_failed')}>{t('revoke')}</Btn>}>
                <b>{t(`defense_${item.kind}`)}</b>
                <span className="ml-2 font-mono text-xs">{item.target}</span>
                <p className="text-[11px] text-slate-500">
                  {item.expires ? formatTime(item.expires, lang) : t('forever')} · {t(item.auto ? 'by_auto' : 'by_manual')}
                </p>
              </Row>
            ))}
          </List>
        )}
      </Panel>
      <Panel title={t('geo_title')} icon={<Globe2 className="h-4 w-4 text-sky-700" aria-hidden="true" />}>
        <p className="text-sm text-slate-600">
          {state?.geo.loaded ? t('geo_loaded', { rows: state.geo.rows, month: state.geo.month }) : t('geo_missing')}
        </p>
        <p className="mt-1 text-xs text-slate-500">{state?.geo.attribution ?? ''}</p>
        <div className="mt-3">
          <Btn tone="cyan" busy={busy} onClick={() => void run(refreshGeo, 'firewall_geo_failed').then(reload)}>
            {t('geo_refresh')}
          </Btn>
        </div>
      </Panel>
    </>
  );
};
