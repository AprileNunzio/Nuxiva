import React, { useState } from 'react';
import { CheckCircle2, CloudDownload, Loader2, RefreshCw, ServerCrash, ShieldAlert } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { applyUpdate, checkNow } from '../api';
import { UpdaterStatus } from '../types';
import { buttonClass, formatDateTime, panelClass, shortRev, useUpdaterI18n } from '../scope';

interface VersionHeroProps {
  readonly status: UpdaterStatus;
  readonly applying: boolean;
  readonly unreachable: boolean;
  readonly onStatus: (status: UpdaterStatus) => void;
  readonly onApplying: (fromRev: string | null) => void;
}

type HeroState = 'restarting' | 'updating' | 'available' | 'error' | 'current' | 'unverified';

function heroState(status: UpdaterStatus, applying: boolean, unreachable: boolean): HeroState {
  if (!unreachable && status.phase === 'ERROR') return 'error';
  if (applying && unreachable) {
    return 'restarting';
  }
  if (applying || status.phase === 'UPDATING' || status.pending) {
    return 'updating';
  }
  if (status.phase === 'ERROR') {
    return 'error';
  }
  if (unreachable || status.check_error || (!status.available && status.ci_note && status.remote_rev !== status.local_rev)) return 'unverified';
  return status.available ? 'available' : 'current';
}

const STATE_STYLE: Readonly<Record<HeroState, { icon: typeof CheckCircle2; tone: string }>> = {
  unverified: { icon: ShieldAlert, tone: 'text-amber-500' },
  current: { icon: CheckCircle2, tone: 'text-emerald-500' },
  available: { icon: CloudDownload, tone: 'text-[var(--md-sys-color-primary)]' },
  updating: { icon: Loader2, tone: 'text-amber-500' },
  restarting: { icon: Loader2, tone: 'text-amber-500' },
  error: { icon: ServerCrash, tone: 'text-rose-500' },
};

export const VersionHero: React.FC<VersionHeroProps> = ({ status, applying, unreachable, onStatus, onApplying }) => {
  const { t, lang } = useUpdaterI18n();
  const [checking, setChecking] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [starting, setStarting] = useState(false);
  const state = heroState(status, applying, unreachable);
  const { icon: StateIcon, tone } = STATE_STYLE[state];
  const busy = state === 'updating' || state === 'restarting';

  const check = async () => {
    setChecking(true);
    try {
      onStatus(await checkNow());
    } catch (cause) {
      reportError('updater_check_failed', cause);
    } finally {
      setChecking(false);
    }
  };

  const apply = async () => {
    setStarting(true);
    try {
      await applyUpdate();
      onApplying(status.local_rev);
    } catch (cause) {
      reportError('updater_apply_failed', cause);
    } finally {
      setStarting(false);
      setConfirming(false);
    }
  };

  return (
    <section className={panelClass} aria-labelledby="upd-hero-title">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <span className={`inline-flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] ${tone}`} role="status">
            <StateIcon className={`h-3.5 w-3.5 ${busy ? 'animate-spin' : ''}`} aria-hidden="true" />
            {t(`state_${state}`)}
          </span>
          <h1 id="upd-hero-title" className="mt-2 font-mono text-2xl font-semibold tracking-tight text-[var(--md-sys-color-on-surface)] sm:text-3xl">
            {t('version_label', { version: status.version ?? t('value_unavailable') })}
          </h1>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-mono text-xs">
            <dt className="text-[var(--md-sys-color-on-surface-variant)]">{t('installed_rev')}</dt>
            <dd className="font-mono text-[var(--md-sys-color-primary)]">{shortRev(status.local_rev) ?? t('value_unavailable')}</dd>
            {status.available && (
              <>
                <dt className="text-[var(--md-sys-color-on-surface-variant)]">{t('target_rev')}</dt>
                <dd className="font-mono text-[var(--md-sys-color-primary)]">{shortRev(status.target_rev ?? status.remote_rev)}</dd>
              </>
            )}
            <dt className="text-[var(--md-sys-color-on-surface-variant)]">{t('last_check')}</dt>
            <dd className="text-[var(--md-sys-color-on-surface)]">{formatDateTime(status.last_check, lang) ?? t('never')}</dd>
          </dl>
          {(status.check_error || status.ci_note || status.last_result) && (
            <p className="mt-3 flex items-start gap-2 text-xs text-[var(--md-sys-color-on-surface-variant)]">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" aria-hidden="true" />
              {status.check_error || status.ci_note || status.last_result}
            </p>
          )}
          {busy && status.message && <p className="mt-2 text-xs text-amber-400">{status.message}</p>}
        </div>
        <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
          <button
            type="button"
            onClick={check}
            disabled={checking || busy}
            className={`${buttonClass} os-btn-secondary`}
          >
            <RefreshCw className={`h-4 w-4 ${checking ? 'animate-spin' : ''}`} aria-hidden="true" />
            <span>{t('action_check')}</span>
          </button>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            disabled={!status.available || busy || !!status.check_error || unreachable}
            className={`${buttonClass} os-btn-primary`}
          >
            <CloudDownload className="h-4 w-4" aria-hidden="true" />
            <span>{t('action_apply')}</span>
          </button>
        </div>
      </div>
      {confirming && (
        <ConfirmDialog
          title={t('confirm_apply_title')}
          body={t(status.policy.sync_nodes ? 'confirm_apply_body_sync' : 'confirm_apply_body', { count: status.nodes.length })}
          confirmLabel={t('action_apply')}
          cancelLabel={t('cancel')}
          pending={starting}
          tone="neutral"
          onConfirm={apply}
          onCancel={() => setConfirming(false)}
        />
      )}
    </section>
  );
};
