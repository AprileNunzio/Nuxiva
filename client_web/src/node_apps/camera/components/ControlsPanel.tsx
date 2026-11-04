import React, { useEffect, useRef, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { CameraControl, fetchControls, resetControls, setControl } from '../data/camerasApi';
import { useCameraI18n } from '../scope';

const DEBOUNCE_MS = 200;

export const ControlsPanel: React.FC<{ readonly sourceId: string }> = ({ sourceId }) => {
  const { t } = useCameraI18n();
  const [controls, setControls] = useState<readonly CameraControl[] | null>(null);
  const [tick, setTick] = useState(0);
  const timers = useRef<Record<string, number>>({});

  useEffect(() => {
    const controller = new AbortController();
    setControls(null);
    fetchControls(sourceId, controller.signal)
      .then(setControls)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          reportError('node_camera_controls_failed', cause);
          setControls([]);
        }
      });
    return () => controller.abort();
  }, [sourceId, tick]);

  const change = (name: string, value: number) => {
    setControls((current) => current?.map((c) => (c.name === name ? { ...c, value } : c)) ?? current);
    window.clearTimeout(timers.current[name]);
    timers.current[name] = window.setTimeout(() => {
      setControl(sourceId, name, value).catch((cause: unknown) => reportError('node_camera_controls_failed', cause));
    }, DEBOUNCE_MS);
  };

  const reset = async () => {
    try {
      await resetControls(sourceId);
      setTick((value) => value + 1);
    } catch (cause) {
      reportError('node_camera_controls_failed', cause);
    }
  };

  return (
    <Panel
      title={t('controls_title')}
      action={
        <button
          type="button"
          onClick={reset}
          className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          {t('controls_reset')}
        </button>
      }
    >
      {controls === null ? (
        <p className="text-sm text-slate-500">{t('loading')}</p>
      ) : controls.length === 0 ? (
        <p className="text-sm text-slate-500">{t('controls_none')}</p>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {controls.map((control) => {
            const label = control.name.replace(/_/g, ' ');
            return (
              <div key={control.name} className={`rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 ${control.inactive ? 'opacity-50' : ''}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs font-medium capitalize text-slate-200">{label}</span>
                  {control.type !== 'menu' && control.type !== 'bool' && (
                    <span className="font-mono text-[11px] text-cyan-200">{control.value}</span>
                  )}
                </div>
                {control.type === 'bool' ? (
                  <input
                    type="checkbox"
                    role="switch"
                    aria-label={label}
                    checked={control.value === 1}
                    disabled={control.inactive}
                    onChange={(event) => change(control.name, event.target.checked ? 1 : 0)}
                    className="mt-1 h-5 w-9 cursor-pointer accent-cyan-400"
                  />
                ) : control.type === 'menu' ? (
                  <select
                    aria-label={label}
                    value={control.value}
                    disabled={control.inactive}
                    onChange={(event) => change(control.name, Number(event.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-white focus:border-cyan-400 focus:outline-none"
                  >
                    {control.menu.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="range"
                    aria-label={label}
                    min={control.min}
                    max={control.max}
                    step={control.step}
                    value={control.value}
                    disabled={control.inactive}
                    onChange={(event) => change(control.name, Number(event.target.value))}
                    className="mt-1 w-full cursor-pointer accent-cyan-400"
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
};
