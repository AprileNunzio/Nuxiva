import React from 'react';
import type { ServiceState } from '../types';
import { labelClass, mutedClass, panelClass, useUpdaterI18n } from '../scope';

const DOT: Readonly<Record<string, string>> = {
  active: 'bg-emerald-500',
  activating: 'bg-amber-500 animate-pulse',
  reloading: 'bg-amber-500 animate-pulse',
  deactivating: 'bg-amber-500',
  failed: 'bg-rose-500',
};

export const ServicesPanel: React.FC<{ readonly services: readonly ServiceState[] }> = ({ services }) => {
  const { t } = useUpdaterI18n();
  return (
    <section className={panelClass} aria-labelledby="upd-services-title">
      <h2 id="upd-services-title" className={labelClass}>{t('services_title')}</h2>
      <ul className="upd-services grid gap-x-6 gap-y-1.5 font-mono text-xs">
        {services.map((service) => (
          <li key={service.unit} className="flex items-center gap-2.5">
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[service.state] ?? 'bg-[var(--md-sys-color-outline-variant)]'}`} aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate text-[var(--md-sys-color-on-surface)]">{service.unit.replace(/^nuxiva-/, '')}</span>
            <span className={mutedClass}>{t(`service_${service.state}`)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
};
