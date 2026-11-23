import React from 'react';
import { useStudioI18n } from '../scope';
import type { DomainWidget, Workpiece3DData } from '../types';

interface DomainWidgetsPanelProps {
  widgets?: DomainWidget[];
  onOpen3DViewer?: (data?: Workpiece3DData) => void;
}

type Metric = { key: string; field: string; unit?: string; tone: string };

const METRICS: Record<string, { icon: string; badge: string; border: string; items: Metric[] }> = {
  sensors: {
    icon: '🌡️', badge: 'w_badge_online', border: 'border-slate-800',
    items: [
      { key: 'w_temp', field: 'temp', unit: ' °C', tone: 'text-cyan-300' },
      { key: 'w_humidity', field: 'humidity', unit: ' %', tone: 'text-cyan-300' },
      { key: 'w_cpu', field: 'cpu', unit: ' %', tone: 'text-emerald-300' },
      { key: 'w_bus', field: 'bus', tone: 'text-emerald-400' },
    ],
  },
  laser_cnc: {
    icon: '⚡', badge: 'w_badge_laser', border: 'border-cyan-900/60',
    items: [
      { key: 'w_power', field: 'power', tone: 'text-amber-300' },
      { key: 'w_speed', field: 'speed', tone: 'text-cyan-300' },
      { key: 'w_kerf', field: 'kerf', tone: 'text-emerald-300' },
      { key: 'w_material', field: 'material', tone: 'text-slate-200' },
    ],
  },
};

export const DomainWidgetsPanel: React.FC<DomainWidgetsPanelProps> = ({ widgets = [] }) => {
  const { t } = useStudioI18n();
  const usable = widgets.filter((w) => w.data && Object.keys(w.data).length > 0);
  if (usable.length === 0) return null;

  return (
    <div className="w-full max-w-2xl flex flex-col gap-2.5 my-2 print:hidden">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-cyan-400 uppercase tracking-wider px-1">
        <span aria-hidden>⚡</span>
        <span>{t('w_title')}</span>
      </div>
      <div className="grid grid-cols-1 cq-sm:grid-cols-2 gap-2.5">
        {usable.map((widget) => {
          const data = widget.data as Record<string, string | number>;
          if (widget.type === 'project_progress') {
            const progress = Math.max(0, Math.min(100, Number(data.progress) || 0));
            return (
              <div key={widget.id} className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 flex flex-col gap-2 shadow-sm w-full">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                  <span className="flex items-center gap-1.5"><span aria-hidden>📊</span><span>{widget.title}</span></span>
                  <span className="text-[11px] font-mono text-emerald-400">{t('w_progress', { value: progress })}</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-full" style={{ width: `${progress}%` }} />
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>{t('w_tasks', { done: data.tasksDone ?? 0, total: data.tasksTotal ?? 0 })}</span>
                  {data.level && <span className="text-cyan-400">{data.level}</span>}
                </div>
              </div>
            );
          }
          const spec = METRICS[widget.type];
          if (!spec) return null;
          return (
            <div key={widget.id} className={`p-3 rounded-2xl bg-slate-900/90 border ${spec.border} flex flex-col gap-2 shadow-sm`}>
              <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                <span className="flex items-center gap-1.5"><span aria-hidden>{spec.icon}</span><span>{widget.title}</span></span>
                <span className="px-1.5 py-0.5 rounded-full bg-slate-950 border border-slate-700 text-[10px] text-cyan-300 font-mono uppercase">{t(spec.badge)}</span>
              </div>
              <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                {spec.items.filter((m) => data[m.field] !== undefined).map((m) => (
                  <div key={m.field} className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">{t(m.key)}</div>
                    <div className={`text-sm font-semibold mt-0.5 truncate ${m.tone}`}>{data[m.field]}{m.unit ?? ''}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
