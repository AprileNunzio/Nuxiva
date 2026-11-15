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
    <header className="flex items-start gap-3 px-1 py-2 sm:py-3">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary-container">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="node-module-title" className="text-xl font-bold tracking-tight text-on-surface sm:text-2xl">
            {title}
          </h2>
          {badge && (
            <span className="rounded-full bg-surface-container-high px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              {badge}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-on-surface-variant sm:text-sm">{subtitle}</p>
      </div>
    </header>
    {children}
  </section>
);

export const Panel: React.FC<{
  readonly title: string;
  readonly action?: React.ReactNode;
  readonly flat?: boolean;
  readonly children: React.ReactNode;
}> = ({ title, action, flat = false, children }) => (
  <div className={flat ? 'min-w-0' : 'min-w-0 rounded-2xl bg-surface-container-low/60 p-4 sm:p-5'}>
    <div className="mb-3 flex items-center justify-between gap-3">
      <h3 className={`text-xs font-semibold uppercase tracking-[0.16em] text-on-surface-variant`}>{title}</h3>
      {action}
    </div>
    {children}
  </div>
);

export const Notice: React.FC<{ readonly tone: 'info' | 'warn'; readonly children: React.ReactNode }> = ({ tone, children }) => (
  <p
    role={tone === 'warn' ? 'alert' : 'note'}
    className={`rounded-xl px-3 py-2.5 text-sm ${
      tone === 'warn' ? 'bg-warning-container text-on-warning-container' : 'bg-primary-container/60 text-on-primary-container'
    }`}
  >
    {children}
  </p>
);
