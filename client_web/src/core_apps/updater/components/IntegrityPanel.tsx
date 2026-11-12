import React from 'react';
import type { SignatureVerdict, UpdaterTelemetry } from '../types';
import { labelClass, mutedClass, panelClass, tone, useUpdaterI18n } from '../scope';

const VERDICT_TONE: Readonly<Record<SignatureVerdict, string>> = {
  trusted: 'ok', valid: 'ok', unsigned: 'warn', unknown_key: 'warn', expired: 'warn', revoked: 'error', bad: 'error',
};

const Row: React.FC<{ readonly label: string; readonly value: string; readonly title?: string; readonly className?: string }> = ({ label, value, title, className }) => (
  <>
    <dt className={mutedClass}>{label}</dt>
    <dd className={`min-w-0 truncate ${className ?? 'text-[var(--md-sys-color-on-surface)]'}`} title={title ?? value}>{value}</dd>
  </>
);

export const IntegrityPanel: React.FC<{ readonly telemetry: UpdaterTelemetry }> = ({ telemetry }) => {
  const { t } = useUpdaterI18n();
  const signature = telemetry.run?.signature ?? telemetry.pending.signature;
  const integrity = telemetry.run?.integrity ?? null;
  const na = t('value_unavailable');
  const engine = telemetry.engine.version ? `${telemetry.engine.name} ${telemetry.engine.version}` : telemetry.engine.name;

  return (
    <section className={panelClass} aria-labelledby="upd-integrity-title">
      <h2 id="upd-integrity-title" className={labelClass}>{t('integrity_title')}</h2>
      <dl className="upd-kv grid gap-x-4 gap-y-1.5 font-mono text-xs">
        <Row label={t('integrity_engine')} value={engine} className={telemetry.engine.name === 'rust' ? tone('ok') : tone('warn')} />
        <Row
          label={t('integrity_signature')}
          value={signature ? t(`verdict_${signature.verdict}`) : na}
          className={signature ? tone(VERDICT_TONE[signature.verdict]) : mutedClass}
        />
        {signature?.signer && <Row label={t('integrity_signer')} value={signature.signer} />}
        {signature?.fingerprint && <Row label={t('integrity_key')} value={signature.fingerprint} />}
        <Row
          label={t('integrity_tree')}
          value={integrity ? t(integrity.intact ? 'integrity_intact' : 'integrity_broken', { matched: integrity.matched, checked: integrity.checked }) : t('integrity_waiting')}
          className={integrity ? tone(integrity.intact ? 'ok' : 'error') : mutedClass}
        />
        {integrity && <Row label={t('integrity_algorithm')} value={integrity.algorithm || na} />}
        {integrity?.fingerprint && <Row label={t('integrity_fingerprint')} value={integrity.fingerprint.slice(0, 24)} title={integrity.fingerprint} />}
        <Row label={t('integrity_branch')} value={telemetry.host.branch} />
        <Row label={t('integrity_git')} value={telemetry.host.git || na} />
        <Row label={t('integrity_python')} value={telemetry.host.python} />
      </dl>
      {integrity && !integrity.intact && (
        <ul className="mt-3 font-mono text-[11px] text-rose-500">
          {[...integrity.mismatched, ...integrity.missing, ...integrity.rejected].slice(0, 8).map((path) => <li key={path} className="truncate">✕ {path}</li>)}
        </ul>
      )}
    </section>
  );
};
