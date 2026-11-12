import React from 'react';
import { Monitor, MonitorSmartphone } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { ScreensState } from '../data/displayApi';
import { useDisplayI18n } from '../scope';

export const ScreensPanel: React.FC<{ readonly state: ScreensState | null }> = ({ state }) => {
  const { t } = useDisplayI18n();
  const screens = state?.screens ?? [];
  const clients = state?.clients ?? [];
  const widest = Math.max(1, ...screens.map((s) => s.width));

  return (
    <Panel title={t('screens_title', { count: screens.length })}>
      {screens.length === 0 ? (
        <p className="text-sm text-slate-500">{t(state ? 'screens_empty' : 'loading')}</p>
      ) : (
        <ul className="flex flex-wrap items-end gap-3">
          {screens.map((screen) => (
            <li key={screen.index} className="flex flex-col items-center gap-1.5">
              <span
                className="flex items-center justify-center rounded-lg border border-cyan-400/50 bg-gradient-to-br from-cyan-400/15 to-indigo-500/10 shadow-[0_0_20px_rgba(34,211,238,0.15)]"
                style={{
                  width: `${Math.max(56, Math.round((screen.width / widest) * 140))}px`,
                  aspectRatio: screen.width && screen.height ? `${screen.width} / ${screen.height}` : '16 / 9',
                }}
              >
                <span className="font-['Rajdhani'] text-xl font-bold text-cyan-100">{screen.index + 1}</span>
              </span>
              <span className="font-mono text-[11px] text-slate-300">
                {screen.width}×{screen.height}
              </span>
              <span className="text-[10px] uppercase tracking-wide text-slate-500">{t(screen.local ? 'screen_local' : 'screen_remote')}</span>
            </li>
          ))}
        </ul>
      )}
      {clients.length > 0 && (
        <div className="mt-4 border-t border-slate-800/80 pt-3">
          <p className="mb-2 text-xs font-semibold text-slate-300">{t('clients_title')}</p>
          <ul className="flex flex-col gap-1.5">
            {clients.map((client) => {
              const Icon = client.client === 'questo server' ? Monitor : MonitorSmartphone;
              return (
                <li
                  key={`${client.client}#${client.screen}`}
                  className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2"
                >
                  <Icon className="h-4 w-4 shrink-0 text-cyan-200" aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate text-sm text-slate-200">
                    {client.client === 'questo server' ? t('client_this_server') : client.client}
                    <span className="ml-2 font-mono text-[11px] text-slate-500">
                      #{client.screen + 1}
                      {client.size ? ` · ${client.size}` : ''}
                    </span>
                  </span>
                  {client.metrics.map(([key, value]) => (
                    <span key={key} className="rounded-full border border-slate-700 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                      {key} {value}
                    </span>
                  ))}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Panel>
  );
};
