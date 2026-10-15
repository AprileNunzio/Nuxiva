import React from 'react';
import { LucideIcon } from 'lucide-react';

interface ModuleFrameProps {
  readonly icon: LucideIcon;
  readonly title: string;
  readonly subtitle: string;
  readonly badge?: string;
  readonly children: React.ReactNode;
}

export const ModuleFrame: React.FC<ModuleFrameProps> = ({ icon: Icon, title, subtitle, badge, children }) => (
  <section className="flex flex-col gap-4" aria-labelledby="node-module-title">
    <header className="flex items-start gap-3 rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-900/70 to-slate-950/90 p-4 sm:p-5">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-cyan-400/40 bg-cyan-400/10 shadow-[0_0_22px_rgba(34,211,238,0.2)]">
        <Icon className="h-5 w-5 text-cyan-200" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="node-module-title" className="font-['Rajdhani'] text-xl font-bold tracking-wide text-white sm:text-2xl">
            {title}
          </h2>
          {badge && (
            <span className="rounded-full border border-slate-700 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-300">
              {badge}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-slate-400 sm:text-sm">{subtitle}</p>
      </div>
    </header>
    {children}
  </section>
);

export const Panel: React.FC<{ readonly title: string; readonly action?: React.ReactNode; readonly children: React.ReactNode }> = ({
  title,
  action,
  children,
}) => (
  <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-900/60 to-slate-950/90 p-4 sm:p-5">
    <div className="mb-3 flex items-center justify-between gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{title}</h3>
      {action}
    </div>
    {children}
  </div>
);

export const Notice: React.FC<{ readonly tone: 'info' | 'warn'; readonly children: React.ReactNode }> = ({ tone, children }) => (
  <p
    role={tone === 'warn' ? 'alert' : 'note'}
    className={`rounded-xl border px-3 py-2.5 text-sm ${
      tone === 'warn' ? 'border-amber-400/40 bg-amber-400/10 text-amber-100' : 'border-cyan-400/30 bg-cyan-400/5 text-cyan-100'
    }`}
  >
    {children}
  </p>
);
