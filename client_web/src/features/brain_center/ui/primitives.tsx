import React from 'react';
import { Loader2, LucideIcon } from 'lucide-react';

export const fieldClass =
  'w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-2xs outline-none transition focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/30 disabled:bg-slate-100 disabled:text-slate-500';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

const VARIANTS: Readonly<Record<Variant, string>> = {
  primary: 'border-blue-600 bg-blue-600 text-white hover:bg-blue-700 shadow-xs',
  secondary: 'border-slate-300 bg-white text-slate-800 hover:bg-slate-50 shadow-2xs',
  ghost: 'border-transparent bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  danger: 'border-rose-200 bg-white text-rose-700 hover:bg-rose-50',
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: Variant;
  readonly icon?: LucideIcon;
  readonly busy?: boolean;
  readonly compact?: boolean;
}

export const Button: React.FC<ButtonProps> = ({ variant = 'secondary', icon: Icon, busy = false, compact = false, children, className = '', disabled, ...rest }) => (
  <button
    type="button"
    {...rest}
    disabled={disabled || busy}
    className={`inline-flex min-h-[36px] shrink-0 items-center justify-center gap-2 rounded-lg border font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:cursor-not-allowed disabled:opacity-50 ${compact ? 'px-2.5 text-xs' : 'px-3.5 text-sm'} ${VARIANTS[variant]} ${className}`}
  >
    {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : Icon ? <Icon className="h-4 w-4" aria-hidden="true" /> : null}
    {children}
  </button>
);

export const IconButton: React.FC<{ readonly icon: LucideIcon; readonly label: string; readonly onClick: () => void; readonly disabled?: boolean; readonly tone?: 'default' | 'danger' }> = ({
  icon: Icon,
  label,
  onClick,
  disabled,
  tone = 'default',
}) => (
  <button
    type="button"
    aria-label={label}
    title={label}
    disabled={disabled}
    onClick={onClick}
    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:opacity-30 ${tone === 'danger' ? 'text-slate-500 hover:bg-rose-50 hover:text-rose-600' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'}`}
  >
    <Icon className="h-4 w-4" aria-hidden="true" />
  </button>
);

export const Switch: React.FC<{ readonly checked: boolean; readonly label: string; readonly onChange: (value: boolean) => void; readonly disabled?: boolean }> = ({
  checked,
  label,
  onChange,
  disabled,
}) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:opacity-50 ${checked ? 'border-blue-600 bg-blue-600' : 'border-slate-300 bg-slate-200'}`}
  >
    <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
  </button>
);

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

const TONES: Readonly<Record<Tone, string>> = {
  neutral: 'border-slate-200 bg-slate-100 text-slate-700',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  danger: 'border-rose-200 bg-rose-50 text-rose-800',
  info: 'border-blue-200 bg-blue-50 text-blue-800',
};

export const Badge: React.FC<{ readonly tone?: Tone; readonly children: React.ReactNode }> = ({ tone = 'neutral', children }) => (
  <span className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${TONES[tone]}`}>{children}</span>
);

interface CardProps {
  readonly title?: string;
  readonly description?: string;
  readonly actions?: React.ReactNode;
  readonly children: React.ReactNode;
  readonly flush?: boolean;
}

export const Card: React.FC<CardProps> = ({ title, description, actions, children, flush = false }) => (
  <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
    {(title || actions) && (
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-4 py-3 sm:px-5">
        <div className="min-w-0">
          {title && <h3 className="text-sm font-semibold text-slate-900">{title}</h3>}
          {description && <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </header>
    )}
    <div className={flush ? '' : 'px-4 py-4 sm:px-5'}>{children}</div>
  </section>
);

interface RowProps {
  readonly icon?: LucideIcon;
  readonly title: React.ReactNode;
  readonly description?: React.ReactNode;
  readonly trailing?: React.ReactNode;
  readonly children?: React.ReactNode;
}

export const Row: React.FC<RowProps> = ({ icon: Icon, title, description, trailing, children }) => (
  <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-3 last:border-b-0 sm:px-5">
    <div className="flex items-center gap-3">
      {Icon && (
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-900">{title}</div>
        {description && <div className="mt-0.5 text-xs leading-relaxed text-slate-500">{description}</div>}
      </div>
      {trailing && <div className="flex shrink-0 items-center gap-2">{trailing}</div>}
    </div>
    {children}
  </div>
);

export const SectionHeader: React.FC<{ readonly title: string; readonly description: string; readonly actions?: React.ReactNode }> = ({ title, description, actions }) => (
  <div className="flex flex-wrap items-end justify-between gap-3">
    <div className="min-w-0">
      <h2 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{title}</h2>
      <p className="mt-1 max-w-3xl text-sm text-slate-500">{description}</p>
    </div>
    {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
  </div>
);

export const Loading: React.FC<{ readonly label: string }> = ({ label }) => (
  <p role="status" className="flex items-center gap-2 px-1 py-6 text-sm text-slate-500">
    <Loader2 className="h-4 w-4 animate-spin text-blue-600" aria-hidden="true" />
    {label}
  </p>
);

export const Empty: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => (
  <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">{children}</p>
);

export const Meter: React.FC<{ readonly value: number; readonly label: string }> = ({ value, label }) => {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const tone = percent >= 90 ? 'bg-rose-500' : percent >= 70 ? 'bg-amber-500' : 'bg-blue-600';
  return (
    <div role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full transition-all ${tone}`} style={{ width: `${percent}%` }} />
    </div>
  );
};
