import React from 'react';
import { stageDuration } from '../consoleFormat';
import type { BootStep, PipelineStage, StageStatus, UpdateRun } from '../types';
import { labelClass, mutedClass, panelClass, tone, useUpdaterI18n } from '../scope';

const GLYPH: Readonly<Record<StageStatus, string>> = { pending: '·', running: '›', done: '✓', skipped: '–', failed: '✕' };
const BAR: Readonly<Record<StageStatus, string>> = {
  pending: 'w-0',
  running: 'w-1/2 animate-pulse bg-[var(--md-sys-color-primary)]',
  done: 'w-full bg-emerald-500/35',
  skipped: 'w-full bg-[var(--md-sys-color-outline-variant)]',
  failed: 'w-full bg-rose-500/60',
};

interface PipelinePanelProps {
  readonly run: UpdateRun | null;
  readonly stageIds: readonly string[];
  readonly boot?: BootStep | null;
}

const STALL_SECONDS = 120;

const BootLine: React.FC<{ readonly boot: BootStep }> = ({ boot }) => {
  const { t } = useUpdaterI18n();
  const stalled = boot.silent_for !== null && boot.silent_for > STALL_SECONDS;
  return (
    <div className="ml-7 mt-2 flex flex-col gap-0.5 text-[11px]">
      <p className="text-[var(--md-sys-color-on-surface)]">↳ {t('boot_line', { title: boot.title, progress: boot.progress })}</p>
      {boot.message && <p className={mutedClass}>{boot.message}</p>}
      {boot.detail && <p className={`truncate ${mutedClass}`}>{boot.detail}</p>}
      {stalled && <p className={tone('warn')}>{t('boot_silent', { seconds: Math.round(boot.silent_for ?? 0) })}</p>}
    </div>
  );
};

export const PipelinePanel: React.FC<PipelinePanelProps> = ({ run, stageIds, boot }) => {
  const { t } = useUpdaterI18n();
  const pipeline = run?.pipeline ?? null;
  const now = Date.now() / 1000;
  const stages: readonly PipelineStage[] = pipeline?.stages
    ?? stageIds.map((id) => ({ id, weight: 0, status: 'pending' as const, started_at: null, finished_at: null }));
  const percent = pipeline?.percent ?? 0;
  const outcome = pipeline?.outcome ?? null;
  const headline = !pipeline ? t('pipeline_idle') : outcome ? t(`pipeline_outcome_${outcome}`) : t('pipeline_running');

  return (
    <section className={panelClass} aria-labelledby="upd-pipeline-title">
      <h2 id="upd-pipeline-title" className={labelClass}>{t('pipeline_title')}</h2>
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <p className={`text-sm ${outcome === 'failed' ? tone('failed') : 'text-[var(--md-sys-color-on-surface)]'}`}>{headline}</p>
        <p className="font-mono text-2xl tabular-nums text-[var(--md-sys-color-on-surface)]" aria-label={t('pipeline_percent', { value: percent })}>
          {percent}<span className={`text-sm ${mutedClass}`}>%</span>
        </p>
      </div>
      <div className="mb-4 h-[2px] w-full bg-[var(--md-sys-color-outline-variant)]" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
        <div className={`h-full transition-[width] duration-500 ${outcome === 'failed' ? 'bg-rose-500' : 'bg-[var(--md-sys-color-primary)]'}`} style={{ width: `${percent}%` }} />
      </div>
      {run && (
        <p className={`mb-3 font-mono text-[11px] ${mutedClass}`}>
          {run.from.slice(0, 7)} → {run.to.slice(0, 7)} · {run.reason}
        </p>
      )}
      <ol className="flex flex-col gap-2.5">
        {stages.map((stage) => {
          const duration = stageDuration(stage.started_at, stage.finished_at, now);
          return (
            <li key={stage.id} className="font-mono text-xs">
              <div className="upd-stage-row grid items-center gap-3">
                <span className={tone(stage.status)} aria-hidden="true">{GLYPH[stage.status]}</span>
                <span className={stage.status === 'pending' ? mutedClass : 'text-[var(--md-sys-color-on-surface)]'}>{t(`stage_${stage.id}`)}</span>
                <span className={`tabular-nums ${mutedClass}`}>{duration ?? ''}</span>
                <span className={`w-20 text-right ${tone(stage.status)}`}>{t(`stage_status_${stage.status}`)}</span>
              </div>
              <div className="ml-7 mt-1 h-px bg-[var(--md-sys-color-outline-variant)]/50">
                <div className={`h-full transition-all duration-500 ${BAR[stage.status]}`} />
              </div>
              {boot && stage.status === 'running' && (stage.id === 'restart' || stage.id === 'confirm') && <BootLine boot={boot} />}
            </li>
          );
        })}
      </ol>
    </section>
  );
};
