import React from 'react';
import { GoogleService, googleDisableService, googleEnableService } from '../data/connectorsApi';
import { usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly services: readonly GoogleService[];
  readonly linked: boolean;
  readonly available: boolean;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const GoogleServices: React.FC<Props> = ({ slug, services, linked, available, busy, run }) => {
  const { t } = usePeopleI18n();

  const toggle = async (service: GoogleService) => {
    if (service.granted) {
      await run(`gg-svc:${service.id}`, () => googleDisableService(slug, service.id), 'people_connectors_failed');
      return;
    }
    let url = '';
    const ok = await run(`gg-svc:${service.id}`, async () => {
      url = await googleEnableService(slug, service.id);
    }, 'people_connectors_failed');
    if (ok && url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <ul className="grid gap-2 sm:grid-cols-2" aria-label={t('gg_services')}>
      {services.map((service) => (
        <li key={service.id} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
          <span aria-hidden="true">{service.icon}</span>
          <span className="min-w-0 flex-1 truncate text-slate-900">{t(`gg_svc_${service.id}`)}</span>
          <button
            type="button"
            role="switch"
            aria-checked={service.granted}
            aria-label={t(`gg_svc_${service.id}`)}
            disabled={busy !== null || !available || (!linked && service.granted)}
            onClick={() => void toggle(service)}
            className={`relative h-6 w-11 shrink-0 rounded-full border transition-colors ${service.granted ? 'border-emerald-500 bg-emerald-500' : 'border-slate-300 bg-slate-200'} disabled:opacity-50`}
          >
            <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${service.granted ? 'left-6' : 'left-1'}`} />
          </button>
        </li>
      ))}
    </ul>
  );
};
