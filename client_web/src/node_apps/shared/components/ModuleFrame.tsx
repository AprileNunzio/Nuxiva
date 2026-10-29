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
    <header className="flex items-start gap-3 rounded-2xl border border-slate-200/90 bg-white p-4 sm:p-5 shadow-xs">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-blue-200 bg-blue-50 text-blue-600 shadow-2xs">
        <Icon className="h-5 w-5 text-blue-600" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="node-module-title" className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            {title}
          </h2>
          {badge && (
            <span className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-700 font-semibold">
              {badge}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-slate-500 sm:text-sm">{subtitle}</p>
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
  <div className="rounded-2xl border border-slate-200/90 bg-white p-4 sm:p-5 shadow-2xs">
    <div className="mb-3 flex items-center justify-between gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</h3>
      {action}
    </div>
    {children}
  </div>
);

export const Notice: React.FC<{ readonly tone: 'info' | 'warn'; readonly children: React.ReactNode }> = ({ tone, children }) => (
  <p
    role={tone === 'warn' ? 'alert' : 'note'}
    className={`rounded-xl border px-3 py-2.5 text-sm ${
      tone === 'warn' ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-blue-200 bg-blue-50 text-blue-800'
    }`}
  >
    {children}
  </p>
);
