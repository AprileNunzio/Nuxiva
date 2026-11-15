import React from 'react';
import { MicTestReport, MicVerdict } from '../data/micTestApi';
import { useMicI18n } from '../scope';
import { ZONE_TEXT, meterPercent } from './LevelMeter';

const VERDICT_TONE: Readonly<Record<MicVerdict, string>> = {
  ok: 'bg-emerald-400/10 text-emerald-200',
  raise: 'bg-amber-400/10 text-amber-200',
  lower: 'bg-rose-400/10 text-rose-200',
  silent: 'bg-surface-container text-on-surface-variant',
};

const ZONE_BAR: Readonly<Record<string, string>> = {
  silent: 'bg-slate-500',
  quiet: 'bg-amber-400',
  good: 'bg-emerald-400',
  loud: 'bg-orange-400',
  clip: 'bg-rose-500',
};

const fmtDb = (value: number) => `${value.toFixed(1)} dBFS`;
const fmtGain = (value: number) => `${value.toFixed(1)}×`;

const Stat: React.FC<{ readonly label: string; readonly value: string; readonly hint?: string }> = ({ label, value, hint }) => (
  <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2">
    <dt className="text-[11px] uppercase tracking-[0.12em] text-slate-400">{label}</dt>
    <dd className="font-mono text-sm text-cyan-100">{value}</dd>
    {hint && <dd className="text-[11px] text-on-surface-variant">{hint}</dd>}
  </div>
);

interface MicTestResultProps {
  readonly report: MicTestReport;
  readonly rawUrl: string;
  readonly processedUrl: string;
}

export const MicTestResult: React.FC<MicTestResultProps> = ({ report, rawUrl, processedUrl }) => {
  const { t } = useMicI18n();
  return (
    <div className="flex flex-col gap-3">
      <p role="status" className={`rounded-xl border px-3 py-2.5 text-sm ${VERDICT_TONE[report.verdict]}`}>
        {t(`test_verdict_${report.verdict}`)}
      </p>
      <div className="flex h-12 items-end gap-px overflow-hidden rounded-lg border border-slate-800 bg-slate-950 px-1" aria-hidden="true">
        {report.timeline.map((sample, index) => (
          <span
            key={index}
            className={`min-w-px flex-1 rounded-t-sm ${ZONE_BAR[sample.zone]}`}
            style={{ height: `${Math.max(4, meterPercent(sample.rmsDb))}%` }}
          />
        ))}
      </div>
      <div className="grid gap-2 cq-sm:grid-cols-2">
        <figure className="flex min-w-0 flex-col gap-1">
          <figcaption className="text-xs font-semibold text-slate-300">{t('test_play_raw')}</figcaption>
          <audio controls preload="auto" src={rawUrl} className="w-full" aria-label={t('test_play_raw')} />
        </figure>
        <figure className="flex min-w-0 flex-col gap-1">
          <figcaption className="text-xs font-semibold text-slate-300">{t('test_play_processed')}</figcaption>
          <audio controls preload="auto" src={processedUrl} className="w-full" aria-label={t('test_play_processed')} />
        </figure>
      </div>
      <p className="text-xs text-on-surface-variant">{t(report.eqEnabled ? 'test_processed_hint_eq' : 'test_processed_hint')}</p>
      <dl className="grid grid-cols-2 gap-2 cq-lg:grid-cols-3">
        <Stat label={t('test_stat_voice')} value={fmtDb(report.voiceDb)} />
        <Stat label={t('test_stat_noise')} value={fmtDb(report.noiseDb)} />
        <Stat label={t('test_stat_snr')} value={`${report.snrDb.toFixed(1)} dB`} />
        <Stat label={t('test_stat_peak')} value={fmtDb(report.peakDb)} hint={t('test_stat_clip', { percent: (report.clipRatio * 100).toFixed(1) })} />
        <Stat
          label={t('test_stat_wake_gain')}
          value={fmtGain(report.wakeGain)}
          hint={t('test_stat_limit', { limit: fmtGain(report.wakeGainLimit), median: fmtGain(report.wakeGainMedian) })}
        />
        <Stat label={t('test_stat_phrase_gain')} value={fmtGain(report.phraseGain)} hint={t('test_stat_max', { limit: fmtGain(report.maxGain) })} />
      </dl>
      {report.autotuned && <p className={`text-xs ${ZONE_TEXT.quiet}`}>{t('test_autotuned')}</p>}
    </div>
  );
};
