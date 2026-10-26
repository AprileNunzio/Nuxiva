import React, { useEffect, useState } from 'react';
import { fetchEnterpriseKnowledgeGraph } from '../api';
import { EnterpriseKnowledgeGraphData } from '../types';

interface Props {
  t: (key: string) => string;
}

export const KnowledgeGraphViewer: React.FC<Props> = ({ t }) => {
  const [data, setData] = useState<EnterpriseKnowledgeGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedDomain, setSelectedDomain] = useState<string>('all');

  const loadGraph = async () => {
    setLoading(true);
    try {
      const graph = await fetchEnterpriseKnowledgeGraph(selectedDomain);
      setData(graph);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [selectedDomain]);

  return (
    <div className="nx-card nx-p-5 nx-mb-6 nx-border nx-border-slate-800 nx-rounded-2xl nx-bg-slate-900/40">
      <div className="nx-flex nx-items-center nx-justify-between nx-mb-3">
        <div className="nx-flex nx-items-center nx-gap-2">
          <span className="nx-text-2xl">🧠</span>
          <h3 className="nx-text-base nx-font-bold nx-text-slate-100">
            {t('knowledge_graph_title')}
          </h3>
        </div>
        <select
          value={selectedDomain}
          onChange={(e) => setSelectedDomain(e.target.value)}
          className="nx-py-1 nx-px-3 nx-rounded-lg nx-text-xs nx-bg-slate-800 nx-text-slate-200 nx-border nx-border-slate-700"
        >
          <option value="all">{t('knowledge_graph_domain_all')}</option>
          <option value="general">General</option>
          <option value="software">Software</option>
          <option value="security">Security</option>
        </select>
      </div>

      <p className="nx-text-xs nx-text-slate-400 nx-mb-4">
        {t('knowledge_graph_desc')}
      </p>

      {loading ? (
        <div className="nx-py-6 nx-text-center nx-text-xs nx-text-slate-500">
          {t('knowledge_graph_loading')}
        </div>
      ) : !data || data.nodes.length === 0 ? (
        <div className="nx-py-6 nx-text-center nx-text-xs nx-text-slate-500">
          {t('knowledge_graph_empty')}
        </div>
      ) : (
        <div className="nx-grid nx-grid-cols-1 md:nx-grid-cols-2 nx-gap-3">
          {data.nodes.map((node) => (
            <div
              key={node.id}
              className="nx-p-3 nx-rounded-xl nx-border nx-border-slate-800/80 nx-bg-slate-950/60"
            >
              <div className="nx-flex nx-items-center nx-justify-between nx-mb-1.5">
                <span className="nx-text-[11px] nx-font-mono nx-font-semibold nx-text-cyan-400">
                  {node.kind === 'lesson_learned' ? '🛡️ LEZIONE' : '📐 DECISIONE'}
                </span>
                <span className="nx-text-[10px] nx-px-2 nx-py-0.5 nx-rounded nx-bg-slate-800 nx-text-slate-400">
                  {node.domain}
                </span>
              </div>
              <p className="nx-text-xs nx-text-slate-200 nx-leading-relaxed">
                {node.description}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
