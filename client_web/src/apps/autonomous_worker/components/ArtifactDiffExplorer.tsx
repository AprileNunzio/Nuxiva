import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Code2,
  Cpu,
  FileCode2,
  GitCommitHorizontal,
  History,
  Layers,
  RotateCcw,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import {
  fetchArtifactContent,
  rollbackMissionArtifact,
  verifyMissionWorkspace,
} from '../api';
import { useAutonomousI18n } from '../scope';
import { Mission, MissionArtifact, WorkspaceVerificationReport } from '../types';

interface Props {
  mission: Mission;
  onRefresh?: () => void;
}

export const ArtifactDiffExplorer: React.FC<Props> = ({ mission, onRefresh }) => {
  const { t } = useAutonomousI18n();
  const [selectedPath, setSelectedPath] = useState<string | null>(
    mission.artifacts[0]?.relative_path || null
  );
  const [viewMode, setViewMode] = useState<'diff' | 'source' | 'symbols' | 'revisions'>('diff');
  const [sourceContent, setSourceContent] = useState<string>('');
  const [loadingSource, setLoadingSource] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyReport, setVerifyReport] = useState<WorkspaceVerificationReport | null>(null);
  const [rollingBackVer, setRollingBackVer] = useState<number | null>(null);

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

  const handleVerifyWorkspace = async () => {
    setVerifying(true);
    try {
      const rep = await verifyMissionWorkspace(mission.id, 'auto');
      setVerifyReport(rep);
      onRefresh?.();
    } finally {
      setVerifying(false);
    }
  };

  const handleRollback = async (relPath: string, version: number) => {
    setRollingBackVer(version);
    try {
      await rollbackMissionArtifact(mission.id, relPath, version);
      onRefresh?.();
    } finally {
      setRollingBackVer(null);
    }
  };

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
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 font-mono text-cyan-300">
            {artifacts.length} File
          </span>
          <span className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 font-mono text-emerald-300">
            {totalLines} LOC
          </span>
          <span className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 font-mono text-indigo-300">
            {totalSymbols} AST Symbols
          </span>
          {artifacts.length > 0 && (
            <button
              type="button"
              disabled={verifying}
              onClick={handleVerifyWorkspace}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1 font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              {verifying ? t('loading') : t('verify_workspace_btn')}
            </button>
          )}
        </div>
      </div>

      {verifyReport && (
        <div
          className={`flex flex-col gap-2 rounded-xl border p-3.5 text-xs ${
            verifyReport.passed
              ? 'border-emerald-800/70 bg-emerald-950/20 text-emerald-200'
              : 'border-rose-800/70 bg-rose-950/20 text-rose-200'
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 font-bold">
              {verifyReport.passed ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <XCircle className="h-4 w-4 text-rose-400" />
              )}
              <span>
                {verifyReport.passed ? t('verify_passed_label') : t('verify_failed_label')} (exit{' '}
                {verifyReport.exit_code})
              </span>
            </div>
            <span className="font-mono text-[11px] opacity-80">
              {verifyReport.checks_run.join(' · ')}
            </span>
          </div>
          {verifyReport.contract_warnings?.length > 0 && (
            <div className="rounded-lg border border-amber-800/60 bg-amber-950/30 p-2 text-[11px] text-amber-200">
              {verifyReport.contract_warnings.map((w, idx) => (
                <div key={idx}>• {w}</div>
              ))}
            </div>
          )}
          <pre className="max-h-36 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950/80 p-2.5 font-mono text-[11px] text-slate-300">
            {verifyReport.output}
          </pre>
        </div>
      )}

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
                  <div className="flex items-center justify-between gap-1">
                    <span className="break-all font-mono text-xs font-semibold text-cyan-300">
                      {art.relative_path}
                    </span>
                    <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-amber-300">
                      v{art.version || 1}
                    </span>
                  </div>
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
                  <span className="ml-2 rounded bg-cyan-950/60 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">
                    v{selectedArt.version || 1}
                  </span>
                  <span className="ml-2 font-mono text-[10px] text-slate-500">
                    SHA256: {selectedArt.checksum.slice(0, 12)}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
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
                  <button
                    type="button"
                    onClick={() => setViewMode('revisions')}
                    className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                      viewMode === 'revisions'
                        ? 'bg-cyan-600 text-white'
                        : 'border border-slate-800 bg-slate-900 text-slate-400 hover:text-white'
                    }`}
                  >
                    <History className="h-3.5 w-3.5" />
                    {t('artifact_tab_revisions')} ({selectedArt.revisions?.length || 1})
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
                <div className="flex flex-col gap-3">
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
                    <p className="py-2 text-center text-xs text-slate-500">
                      {t('artifact_no_symbols')}
                    </p>
                  )}

                  {selectedArt.imports && selectedArt.imports.length > 0 && (
                    <div className="flex flex-col gap-1.5 border-t border-slate-800 pt-2">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                        {t('artifact_imports_label')} ({selectedArt.imports.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedArt.imports.map((imp, idx) => (
                          <span
                            key={idx}
                            className="rounded border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-[11px] text-cyan-300"
                          >
                            {imp}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {viewMode === 'revisions' && (
                <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
                  {(selectedArt.revisions || []).slice().reverse().map((rev) => (
                    <div
                      key={rev.version}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs"
                    >
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-amber-950/60 px-1.5 py-0.5 font-mono font-bold text-amber-300">
                            v{rev.version}
                          </span>
                          <span className="font-semibold text-slate-200">
                            {rev.generated_by || selectedArt.generated_by}
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">
                            {rev.checksum.slice(0, 10)}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400">
                          {rev.line_count || 0}L · {rev.size_bytes || 0}B
                        </span>
                      </div>
                      {rev.version !== selectedArt.version && (
                        <button
                          type="button"
                          disabled={rollingBackVer === rev.version}
                          onClick={() => handleRollback(selectedArt.relative_path, rev.version)}
                          className="flex items-center gap-1 rounded-lg border border-amber-700/60 bg-amber-950/40 px-2.5 py-1 text-xs font-semibold text-amber-200 transition hover:bg-amber-900/60 disabled:opacity-50"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          {t('rollback_btn')} v{rev.version}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
