import React, { useEffect, useState } from 'react';
import { fetchMissionDAG } from '../api';
import { DAGGraphData } from '../types';

interface Props {
  missionId: string;
  t: (key: string) => string;
}

export const MissionDAGVisualizer: React.FC<Props> = ({ missionId, t }) => {
  const [data, setData] = useState<DAGGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadDAG = async () => {
    setLoading(true);
    try {
      const dag = await fetchMissionDAG(missionId);
      setData(dag);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDAG();
  }, [missionId]);

  const getNodeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'done':
        return 'nx-border-emerald-600 nx-bg-emerald-950/60 nx-text-emerald-300';
      case 'running':
        return 'nx-border-cyan-500 nx-bg-cyan-950/70 nx-text-cyan-200 nx-animate-pulse';
      case 'review':
        return 'nx-border-amber-500 nx-bg-amber-950/60 nx-text-amber-200';
      case 'failed':
        return 'nx-border-rose-600 nx-bg-rose-950/60 nx-text-rose-300';
      default:
        return 'nx-border-slate-800 nx-bg-slate-900/60 nx-text-slate-400';
    }
  };

  return (
    <div className="nx-card nx-p-4 nx-mb-4 nx-border nx-border-slate-800 nx-rounded-xl nx-bg-slate-900/40">
      <div className="nx-flex nx-items-center nx-justify-between nx-mb-3">
        <div className="nx-flex nx-items-center nx-gap-2">
          <span className="nx-text-xl">🔀</span>
          <h3 className="nx-text-sm nx-font-bold nx-text-slate-100">
            {t('dag_visualizer_title')}
          </h3>
        </div>
        <button
          type="button"
          onClick={loadDAG}
          className="nx-text-[11px] nx-text-slate-400 hover:nx-text-white"
        >
          {t('dag_refresh_btn')}
        </button>
      </div>

      {loading ? (
        <div className="nx-py-4 nx-text-center nx-text-xs nx-text-slate-500">
          {t('dag_loading')}
        </div>
      ) : !data || data.nodes.length === 0 ? (
        <div className="nx-py-4 nx-text-center nx-text-xs nx-text-slate-500">
          {t('dag_empty')}
        </div>
      ) : (
        <div className="nx-flex nx-flex-wrap nx-gap-2.5">
          {data.nodes.map((node) => {
            const deps = data.edges.filter((e) => e.to === node.id).map((e) => e.from);
            return (
              <div
                key={node.id}
                className={`nx-p-2.5 nx-rounded-lg nx-border nx-text-xs nx-min-w-[140px] nx-max-w-[220px] ${getNodeColor(
                  node.status
                )}`}
              >
                <div className="nx-flex nx-items-center nx-justify-between nx-mb-1">
                  <span className="nx-font-mono nx-text-[10px] nx-opacity-70">
                    {node.id}
                  </span>
                  <span className="nx-font-bold nx-text-[10px] nx-uppercase">
                    {node.status}
                  </span>
                </div>
                <div className="nx-font-semibold nx-text-xs nx-truncate">
                  {node.title}
                </div>
                <div className="nx-text-[10px] nx-opacity-80 nx-truncate">
                  {node.role}
                </div>
                {deps.length > 0 && (
                  <div className="nx-mt-1 nx-pt-1 nx-border-t nx-border-slate-800/60 nx-text-[9px] nx-text-slate-400">
                    Dipende da: {deps.join(', ')}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
