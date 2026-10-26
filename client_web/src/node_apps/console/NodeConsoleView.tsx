import React, { useMemo, useState } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { KIND_COLORS, isStale, useMeshTopology } from '../../features/neural_mesh';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { NodeCommandBar } from './components/NodeCommandBar';
import { NodeLiveStrip } from './components/NodeLiveStrip';
import { NodeNameEditor } from './components/NodeNameEditor';
import { useNodeControl } from './hooks/useNodeControl';
import { NODE_MODULES } from './moduleRegistry';
import { CONSOLE_SCOPE } from './scope';

interface NodeConsoleViewProps {
  readonly standaloneApps?: boolean;
  readonly nodeId: string;
  readonly initialName: string;
  readonly initialModule?: string;
  readonly onBack: () => void;
  readonly onRenamed: (nodeId: string, name: string) => void;
}

export const NodeConsoleView: React.FC<NodeConsoleViewProps> = ({
  nodeId,
  initialName,
  initialModule,
  onBack,
  onRenamed,
  standaloneApps = false,
}) => {
  const { t } = useScopedI18n(CONSOLE_SCOPE);
  const { snapshot } = useMeshTopology();
  const control = useNodeControl(nodeId);
  const [activeModule, setActiveModule] = useState(initialModule || NODE_MODULES[0].id);
  const [renamed, setRenamed] = useState<string | null>(null);

  const neuron = useMemo(() => snapshot?.neurons.find((n) => n.id === nodeId) ?? null, [snapshot, nodeId]);
  const name = renamed ?? neuron?.name ?? initialName;
  const online = neuron ? !isStale(neuron, Date.now()) : null;
  const color = neuron ? KIND_COLORS[neuron.kind] : '#22d3ee';
  const modules = useMemo(
    () => NODE_MODULES.filter((m) => !control?.unsupportedModules.includes(m.id)),
    [control],
  );
  const ActiveModule = (modules.find((m) => m.id === activeModule) ?? modules[0] ?? NODE_MODULES[0]).component;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 bg-[#02040a] px-3 py-4 text-slate-100 sm:px-6">
      <section className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-900/80 to-slate-950/90 p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <button
              type="button"
              onClick={onBack}
              aria-label={t('back')}
              className="mt-1 rounded-xl border border-slate-800 bg-slate-900/80 p-2 text-slate-300 transition hover:border-cyan-400/60 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            </button>
            <div className="min-w-0">
              <NodeNameEditor
                nodeId={nodeId}
                name={name}
                onRenamed={(next) => {
                  setRenamed(next);
                  onRenamed(nodeId, next);
                }}
              />
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                {neuron && (
                  <span className="rounded-full border px-2 py-0.5 font-mono uppercase tracking-wider" style={{ borderColor: `${color}66`, color }}>
                    {t(`kind_${neuron.kind}`)}
                  </span>
                )}
                {online !== null && (
                  <span className={`rounded-full border px-2 py-0.5 font-semibold ${online ? 'border-emerald-400/40 text-emerald-300' : 'border-amber-400/40 text-amber-300'}`}>
                    {t(online ? 'state_online' : 'state_offline')}
                  </span>
                )}
                {control && <span className="text-slate-400">{t(`scope_${control.scope}`)}</span>}
                {neuron?.ip && <span className="font-mono text-cyan-200">{neuron.ip}</span>}
                {neuron?.room && <span className="text-slate-400">{neuron.room}</span>}
              </div>
            </div>
          </div>
          <div className="lg:max-w-md">
            {control ? (
              <NodeCommandBar nodeId={nodeId} nodeName={name} scope={control.scope} commands={control.commands} />
            ) : (
              <Loader2 className="h-4 w-4 animate-spin text-cyan-300" aria-label={t('loading')} />
            )}
          </div>
        </div>
        <div className="mt-4">
          <NodeLiveStrip neuron={neuron} />
        </div>
      </section>

      {!standaloneApps && <><nav aria-label={t('modules_label')} className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {modules.map(({ id, icon: Icon }) => {
          const selected = id === activeModule;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setActiveModule(id)}
              aria-current={selected ? 'page' : undefined}
              className={`flex shrink-0 items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                selected
                  ? 'border-cyan-400/50 bg-cyan-400/10 text-cyan-200 shadow-[0_0_18px_rgba(34,211,238,0.18)]'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-600 hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {t(`module_${id}`)}
            </button>
          );
        })}
      </nav>

      <section className="min-h-0 flex-1">
        {control ? (
          <ActiveModule key={`${activeModule}-${control.scope}`} nodeId={nodeId} scope={control.scope} />
        ) : (
          <Loader2 className="h-5 w-5 animate-spin text-cyan-300" aria-label={t('loading')} />
        )}
      </section></>}
    </div>
  );
};
