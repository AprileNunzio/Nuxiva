import React from 'react';
import { Loader2, RefreshCw, WifiOff } from 'lucide-react';
import { PAGE_CLASS } from '../../shared/ui/layout';

export type Tone = 'cyan' | 'emerald' | 'amber' | 'rose' | 'purple' | 'slate';

const TONES: Record<Tone, string> = {
  cyan: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
  emerald: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  amber: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
  rose: 'border-rose-500/40 bg-rose-500/10 text-rose-200',
  purple: 'border-purple-500/40 bg-purple-500/10 text-purple-200',
  slate: 'border-slate-600/60 bg-slate-800/60 text-slate-300',
};

export const panelClass = 'rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-900/70 to-slate-950/90 p-4 sm:p-5';
export const inputClass =
  'w-full rounded-xl border border-slate-700/80 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500';
export const gridClass = 'grid gap-4 lg:grid-cols-2 3xl:grid-cols-3';

interface FrameProps {
  readonly title: string;
  readonly description: string;
  readonly onReload?: () => void;
  readonly actions?: React.ReactNode;
  readonly children: React.ReactNode;
}

export const AppFrame: React.FC<FrameProps> = ({ title, description, onReload, actions, children }) => (
  <div className={PAGE_CLASS}>
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl font-black tracking-wide text-cyan-300">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">{description}</p>
      </div>
      <div className="flex items-center gap-2">
        {actions}
        {onReload ? (
          <button
            type="button"
            onClick={onReload}
            aria-label="refresh"
            className="rounded-xl border border-slate-700 bg-slate-900 p-2 text-slate-300 transition hover:border-cyan-500 hover:text-cyan-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </header>
    {children}
  </div>
);

interface PanelProps {
  readonly title: string;
  readonly icon?: React.ReactNode;
  readonly actions?: React.ReactNode;
  readonly className?: string;
  readonly children: React.ReactNode;
}

export const Panel: React.FC<PanelProps> = ({ title, icon, actions, className = '', children }) => (
  <section className={`${panelClass} ${className} min-w-0`}>
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        {icon}
        {title}
      </h2>
      {actions}
    </div>
    {children}
  </section>
);

export const Stat: React.FC<{ readonly label: string; readonly value: React.ReactNode; readonly tone?: Tone }> = ({ label, value, tone = 'cyan' }) => (
  <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-2.5">
    <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{label}</div>
    <div className={`mt-0.5 truncate font-mono text-lg font-bold ${TONES[tone].split(' ').pop()}`}>{value}</div>
  </div>
);

export const StatRow: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => (
  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 3xl:grid-cols-6">{children}</div>
);

export const Pill: React.FC<{ readonly tone?: Tone; readonly children: React.ReactNode }> = ({ tone = 'slate', children }) => (
  <span className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${TONES[tone]}`}>{children}</span>
);

interface BtnProps {
  readonly onClick?: () => void;
  readonly busy?: boolean;
  readonly disabled?: boolean;
  readonly tone?: Tone;
  readonly type?: 'button' | 'submit';
  readonly title?: string;
  readonly children: React.ReactNode;
}

export const Btn: React.FC<BtnProps> = ({ onClick, busy = false, disabled = false, tone = 'cyan', type = 'button', title, children }) => (
  <button
    type={type}
    title={title}
    onClick={onClick}
    disabled={busy || disabled}
    className={`inline-flex items-center justify-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-semibold transition hover:brightness-125 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${TONES[tone]}`}
  >
    {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
    {children}
  </button>
);

export const Row: React.FC<{ readonly children: React.ReactNode; readonly actions?: React.ReactNode }> = ({ children, actions }) => (
  <li className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
    <div className="min-w-0 flex-1 text-sm text-slate-200">{children}</div>
    {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
  </li>
);

export const List: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => <ul className="flex flex-col gap-2">{children}</ul>;

export const Empty: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => (
  <p className="rounded-xl border border-dashed border-slate-700/70 px-3 py-6 text-center text-sm text-slate-500">{children}</p>
);

export const Loading: React.FC<{ readonly label: string }> = ({ label }) => (
  <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-sm text-slate-400" role="status">
    <Loader2 className="h-6 w-6 animate-spin text-cyan-300" aria-hidden="true" />
    {label}
  </div>
);

export const Unreachable: React.FC<{ readonly label: string }> = ({ label }) => (
  <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-sm text-slate-400" role="alert">
    <WifiOff className="h-6 w-6 text-rose-300" aria-hidden="true" />
    {label}
  </div>
);

export const Field: React.FC<{ readonly label: string; readonly children: React.ReactNode }> = ({ label, children }) => (
  <label className="flex flex-col gap-1 text-xs font-semibold text-slate-400">
    {label}
    {children}
  </label>
);

export const Toggle: React.FC<{ readonly checked: boolean; readonly onChange: (value: boolean) => void; readonly label: string; readonly disabled?: boolean }> = ({
  checked,
  onChange,
  label,
  disabled = false,
}) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className={`relative h-6 w-11 shrink-0 rounded-full border transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${checked ? 'border-cyan-500 bg-cyan-500/30' : 'border-slate-600 bg-slate-800'}`}
  >
    <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${checked ? 'left-6' : 'left-0.5'}`} />
  </button>
);

export function formatTime(seconds: unknown, locale: string): string {
  if (typeof seconds !== 'number' || !seconds) {
    return '—';
  }
  return new Intl.DateTimeFormat(locale, { dateStyle: 'short', timeStyle: 'short' }).format(new Date(seconds * 1000));
}

export function formatBytes(value: unknown): string {
  const size = typeof value === 'number' ? value : 0;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let n = size;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}
