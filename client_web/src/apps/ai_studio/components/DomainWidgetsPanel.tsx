import React from 'react';
import type { DomainWidget, Workpiece3DData } from '../types';

interface DomainWidgetsPanelProps {
  widgets?: DomainWidget[];
  onOpen3DViewer?: (data?: Workpiece3DData) => void;
}

export const DomainWidgetsPanel: React.FC<DomainWidgetsPanelProps> = ({
  widgets = [],
  onOpen3DViewer,
}) => {
  if (widgets.length === 0) return null;

  return (
    <div className="w-full max-w-2xl flex flex-col gap-2.5 my-2 print:hidden">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-cyan-400 uppercase tracking-wider px-1">
        <span>⚡</span>
        <span>Widget Attivi (Pagina 8080)</span>
      </div>

      <div className="grid grid-cols-1 @[480px]:grid-cols-2 gap-2.5">
        {widgets.map((widget) => {
          if (widget.type === 'sensors') {
            const data = widget.data || { temp: 22.4, humidity: 45, cpu: 18, bus: 'OK' };
            return (
              <div
                key={widget.id}
                className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 flex flex-col gap-2 shadow-sm"
              >
                <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                  <span className="flex items-center gap-1.5">
                    <span>🌡️</span>
                    <span>{widget.title}</span>
                  </span>
                  <span className="px-1.5 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-800 text-[10px] text-emerald-300 font-mono">
                    ONLINE
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Temperatura</div>
                    <div className="text-sm font-semibold text-cyan-300 mt-0.5">{data.temp} °C</div>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Umidità</div>
                    <div className="text-sm font-semibold text-cyan-300 mt-0.5">{data.humidity} %</div>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Carico CPU</div>
                    <div className="text-sm font-semibold text-emerald-300 mt-0.5">{data.cpu} %</div>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Bus Nuxiva</div>
                    <div className="text-sm font-semibold text-emerald-400 mt-0.5">{data.bus}</div>
                  </div>
                </div>
              </div>
            );
          }

          if (widget.type === 'laser_cnc') {
            const data = widget.data || { power: '45W', speed: '350 mm/s', kerf: '0.14 mm', material: 'Compensato 4mm' };
            return (
              <div
                key={widget.id}
                className="p-3 rounded-2xl bg-slate-900/90 border border-cyan-900/60 flex flex-col gap-2 shadow-sm"
              >
                <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                  <span className="flex items-center gap-1.5">
                    <span>⚡</span>
                    <span>{widget.title}</span>
                  </span>
                  <span className="px-1.5 py-0.5 rounded-full bg-cyan-950 border border-cyan-800 text-[10px] text-cyan-300 font-mono">
                    TAGLIO LASER
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Potenza Laser</div>
                    <div className="text-sm font-semibold text-amber-300 mt-0.5">{data.power}</div>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Velocità</div>
                    <div className="text-sm font-semibold text-cyan-300 mt-0.5">{data.speed}</div>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Kerf Compensato</div>
                    <div className="text-sm font-semibold text-emerald-300 mt-0.5">{data.kerf}</div>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <div className="text-[10px] text-slate-400">Materiale</div>
                    <div className="text-[11px] font-semibold text-slate-200 mt-0.5 truncate">{data.material}</div>
                  </div>
                </div>
              </div>
            );
          }

          if (widget.type === 'project_progress') {
            const data = widget.data || { progress: 85, tasksDone: 17, tasksTotal: 20, level: 'Level 0 (Zero-Token)' };
            return (
              <div
                key={widget.id}
                className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 flex flex-col gap-2 shadow-sm w-full"
              >
                <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                  <span className="flex items-center gap-1.5">
                    <span>📊</span>
                    <span>{widget.title}</span>
                  </span>
                  <span className="text-[11px] font-mono text-emerald-400">
                    {data.progress}% Completato
                  </span>
                </div>

                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-full"
                    style={{ width: `${data.progress}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Task Eseguiti: {data.tasksDone} / {data.tasksTotal}</span>
                  <span className="text-cyan-400">{data.level}</span>
                </div>
              </div>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
};
