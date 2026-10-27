import React, { useEffect, useState } from 'react';
import { Code2, Cpu, FileCode2, GitCommitHorizontal, Layers } from 'lucide-react';
import { fetchArtifactContent } from '../api';
import { useAutonomousI18n } from '../scope';
import { Mission, MissionArtifact } from '../types';

interface Props {
  mission: Mission;
}

export const ArtifactDiffExplorer: React.FC<Props> = ({ mission }) => {
  const { t } = useAutonomousI18n();
  const [selectedPath, setSelectedPath] = useState<string | null>(
    mission.artifacts[0]?.relative_path || null
  );
  const [viewMode, setViewMode] = useState<'diff' | 'source' | 'symbols'>('diff');
  const [sourceContent, setSourceContent] = useState<string>('');
  const [loadingSource, setLoadingSource] = useState<boolean>(false);

  const artifacts = mission.artifacts || [];
  const selectedArt: MissionArtifact | null =
    artifacts.find((a) => a.relative_path === selectedPath) || artifacts[0] || null;

  useEffect(() => {
    if (!selectedArt) {
      setSourceContent('');
      return;
    }
    if (viewMode === 'source') {
      setLoadingSource(true);
      fetchArtifactContent(mission.id, selectedArt.relative_path)
        .then((txt) => setSourceContent(txt))
        .catch(() => setSourceContent(''))
        .finally(() => setLoadingSource(false));
    }
  }, [mission.id, selectedArt?.relative_path, selectedArt?.checksum, viewMode]);

  const totalLines = artifacts.reduce((acc, a) => acc + (a.line_count || 0), 0);
  const totalSymbols = artifacts.reduce((acc, a) => acc + (a.symbols?.length || 0), 0);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <FileCode2 className="h-5 w-5 text-cyan-400" />
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100">
              {t('artifacts_title')}
            </h3>
            <p className="text-xs text-slate-400">{t('artifacts_subtitle')}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 font-mono text-cyan-300">
            {artifacts.length} File
          </span>
          <span className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 font-mono text-emerald-300">
            {totalLines} LOC
          </span>
          <span className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 font-mono text-indigo-300">
            {totalSymbols} AST Symbols
          </span>
        </div>
      </div>

      {artifacts.length === 0 ? (
        <div className="py-6 text-center text-xs text-slate-500">
          {t('artifacts_empty')}
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]">
          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto pr-1">
            {artifacts.map((art) => {
              const active = selectedArt?.relative_path === art.relative_path;
              return (
                <button
                  key={art.id + art.relative_path}
                  type="button"
                  onClick={() => setSelectedPath(art.relative_path)}
                  className={`flex flex-col gap-1 rounded-xl border p-3 text-left transition ${
                    active
                      ? 'border-cyan-500 bg-cyan-950/30 text-white'
                      : 'border-slate-800 bg-slate-950/50 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <span className="break-all font-mono text-xs font-semibold text-cyan-300">
                    {art.relative_path}
                  </span>
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>{art.generated_by}</span>
                    <span>
                      {art.line_count || 0}L · {art.size_bytes}B
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {selectedArt && (
            <div className="flex min-w-0 flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <span className="font-mono text-xs font-bold text-slate-100">
                    {selectedArt.relative_path}
                  </span>
                  <span className="ml-2 font-mono text-[10px] text-slate-500">
                    SHA256: {selectedArt.checksum.slice(0, 12)}
                  </span>
                </div>
                <div className="flex gap-1.5">
                  <button
                    type="button"
                    onClick={() => setViewMode('diff')}
                    className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                      viewMode === 'diff'
                        ? 'bg-cyan-600 text-white'
                        : 'border border-slate-800 bg-slate-900 text-slate-400 hover:text-white'
                    }`}
                  >
                    <GitCommitHorizontal className="h-3.5 w-3.5" />
                    {t('artifact_tab_diff')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('source')}
                    className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                      viewMode === 'source'
                        ? 'bg-cyan-600 text-white'
                        : 'border border-slate-800 bg-slate-900 text-slate-400 hover:text-white'
                    }`}
                  >
                    <Code2 className="h-3.5 w-3.5" />
                    {t('artifact_tab_source')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('symbols')}
                    className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                      viewMode === 'symbols'
                        ? 'bg-cyan-600 text-white'
                        : 'border border-slate-800 bg-slate-900 text-slate-400 hover:text-white'
                    }`}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    AST ({selectedArt.symbols?.length || 0})
                  </button>
                </div>
              </div>

              {viewMode === 'diff' && (
                <div className="max-h-96 overflow-auto rounded-lg border border-slate-800/80 bg-slate-950 p-3 font-mono text-xs">
                  {selectedArt.diff ? (
                    selectedArt.diff.split('\n').map((line, i) => {
                      const cls = line.startsWith('+')
                        ? 'bg-emerald-950/40 text-emerald-300'
                        : line.startsWith('-')
                        ? 'bg-rose-950/40 text-rose-300'
                        : line.startsWith('@@')
                        ? 'text-cyan-400 font-bold'
                        : 'text-slate-300';
                      return (
                        <div key={i} className={`whitespace-pre px-1.5 py-0.5 ${cls}`}>
                          {line}
                        </div>
                      );
                    })
                  ) : (
                    <div className="py-4 text-center text-slate-500">
                      {t('artifact_no_diff')}
                    </div>
                  )}
                </div>
              )}

              {viewMode === 'source' && (
                <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800/80 bg-slate-950 p-3 font-mono text-xs leading-relaxed text-slate-200">
                  {loadingSource ? t('loading') : sourceContent || t('artifact_no_source')}
                </pre>
              )}

              {viewMode === 'symbols' && (
                <div className="flex flex-col gap-2">
                  {selectedArt.symbols && selectedArt.symbols.length > 0 ? (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {selectedArt.symbols.map((sym, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 rounded-lg border border-indigo-900/40 bg-indigo-950/20 px-3 py-2 font-mono text-xs text-indigo-200"
                        >
                          <Cpu className="h-3.5 w-3.5 shrink-0 text-indigo-400" />
                          <span className="truncate">{sym}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="py-4 text-center text-xs text-slate-500">
                      {t('artifact_no_symbols')}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
