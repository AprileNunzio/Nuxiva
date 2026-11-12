import React from 'react';
import { OSIcon3D } from '../../app_shell/OSIcon3D';
import icon from './icon.png';
import { isStale } from '../../features/neural_mesh/domain/metrics';
import { OSInspector } from '../shared/kit';
import { MeshNeuron } from '../../features/neural_mesh/domain/types';

export interface MCPInsightState {
  readonly loading: boolean;
  readonly text?: string;
  readonly error?: string;
}

interface NetworkInspectorProps {
  readonly selectedNode: MeshNeuron | null;
  readonly studyingNodeId: string | null;
  readonly mcpInsights: Record<string, MCPInsightState>;
  readonly onClose: () => void;
  readonly onOpenConsole: (node: MeshNeuron, module?: string) => void;
  readonly onAskMCP: (nodeId: string, address: string) => void;
  readonly onStudy: (nodeId: string, address: string) => void;
  readonly format: (value: number, maxDigits?: number) => string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const NetworkInspector: React.FC<NetworkInspectorProps> = ({
  selectedNode,
  studyingNodeId,
  mcpInsights,
  onClose,
  onOpenConsole,
  onAskMCP,
  onStudy,
  format,
  t,
}) => {
  if (!selectedNode) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center text-slate-400">
        <OSIcon3D name="Preview" source={icon} size="md" />
        <p className="mt-3 text-xs font-semibold text-slate-300">{t('devices')}</p>
        <span className="mt-1 text-[11px] text-slate-400">
          {t('description')}
        </span>
      </div>
    );
  }

  const isLive = !isStale(selectedNode, Date.now()) && selectedNode.online !== false;
  const nodeInsight = mcpInsights[selectedNode.id];

  return (
    <OSInspector
      title={selectedNode.name}
      subtitle={`${selectedNode.room || t(selectedNode.kind)} · ${selectedNode.ip || '—'}`}
      onClose={onClose}
      actions={
        <div className="flex flex-col gap-2">
          <button
            type="button"
            className="w-full rounded-xl bg-blue-600 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 active:scale-[0.99] transition"
            onClick={() => onOpenConsole(selectedNode)}
          >
            {t('manage')} →
          </button>
          <button
            type="button"
            className="w-full rounded-xl border border-cyan-500/30 bg-cyan-500/10 py-2 text-xs font-semibold text-cyan-400 hover:bg-cyan-500/20 active:scale-[0.99] transition"
            onClick={() => onOpenConsole(selectedNode, 'task_manager')}
          >
            {t('task_manager')} →
          </button>
          <button
            type="button"
            className="w-full rounded-xl border border-slate-700/60 bg-slate-800/80 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700/80 active:scale-[0.99] transition"
            onClick={() => onOpenConsole(selectedNode, 'connections')}
          >
            {t('connections_center')} →
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              className="flex-1 rounded-xl border border-slate-700/60 bg-slate-800/60 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700/60 active:scale-[0.98] transition"
              onClick={() => onAskMCP(selectedNode.id, selectedNode.ip || selectedNode.name)}
            >
              {t('mcp_whois')}
            </button>
            <button
              type="button"
              className="flex-1 rounded-xl border border-slate-700/60 bg-slate-800/60 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700/60 active:scale-[0.98] transition"
              disabled={studyingNodeId === selectedNode.id}
              onClick={() => onStudy(selectedNode.id, selectedNode.ip || selectedNode.id)}
            >
              {studyingNodeId === selectedNode.id ? '...' : t('device_study')}
            </button>
          </div>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-100/60 dark:bg-slate-900/60 p-3.5 backdrop-blur-md">
          <OSIcon3D name={selectedNode.name} source={icon} size="md" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <strong className="truncate text-sm text-slate-900 dark:text-slate-100">{selectedNode.name}</strong>
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                style={{
                  backgroundColor: isLive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                  color: isLive ? '#10b981' : '#94a3b8',
                }}
              >
                {isLive ? t('online') : t('offline')}
              </span>
            </div>
            <span className="text-xs text-slate-500 dark:text-slate-400">{t(selectedNode.kind)}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div className="rounded-xl border border-slate-200/70 dark:border-slate-800/70 bg-slate-50/50 dark:bg-slate-900/40 p-3">
            <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400">{t('power')}</span>
            <strong className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {selectedNode.telemetry.powerWatts != null ? `${format(selectedNode.telemetry.powerWatts)} W` : '—'}
            </strong>
          </div>
          <div className="rounded-xl border border-slate-200/70 dark:border-slate-800/70 bg-slate-50/50 dark:bg-slate-900/40 p-3">
            <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400">{t('latency')}</span>
            <strong className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {selectedNode.telemetry.pingMs != null ? `${selectedNode.telemetry.pingMs} ms` : '—'}
            </strong>
          </div>
          <div className="rounded-xl border border-slate-200/70 dark:border-slate-800/70 bg-slate-50/50 dark:bg-slate-900/40 p-3">
            <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400">CPU</span>
            <strong className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {selectedNode.telemetry.cpuPercent != null ? `${format(selectedNode.telemetry.cpuPercent)}%` : '—'}
            </strong>
          </div>
          <div className="rounded-xl border border-slate-200/70 dark:border-slate-800/70 bg-slate-50/50 dark:bg-slate-900/40 p-3">
            <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400">RAM</span>
            <strong className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate block">
              {selectedNode.telemetry.ramUsedGb != null
                ? `${format(selectedNode.telemetry.ramUsedGb)} / ${format(selectedNode.telemetry.ramTotalGb || 0)} GB`
                : '—'}
            </strong>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200/70 dark:border-slate-800/70 bg-slate-50/50 dark:bg-slate-900/40 p-3.5 text-xs">
          <span className="mb-2 block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {t('technical')}
          </span>
          <div className="flex flex-col gap-2 text-slate-600 dark:text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">{t('address')}</span>
              <span className="font-mono">{selectedNode.ip || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">{t('platform')}</span>
              <span>{selectedNode.telemetry.os || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">ID Nodo</span>
              <span className="font-mono truncate max-w-[10rem]">{selectedNode.id}</span>
            </div>
          </div>
        </div>

        {nodeInsight && (
          <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-3.5 text-xs">
            <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-blue-400">
              Insight Assistente MCP
            </span>
            {nodeInsight.loading && <p className="italic text-slate-400">{t('scanning')}</p>}
            {nodeInsight.error && <p className="text-rose-400">{nodeInsight.error}</p>}
            {nodeInsight.text && (
              <p className="text-slate-200 leading-relaxed whitespace-pre-wrap">{nodeInsight.text}</p>
            )}
          </div>
        )}
      </div>
    </OSInspector>
  );
};
