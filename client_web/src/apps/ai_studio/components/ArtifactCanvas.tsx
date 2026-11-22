import React, { useEffect, useState } from 'react';
import { useStudioI18n } from '../scope';
import type { Artifact } from '../types';
import { saveSmbFile, executeCode, type ExecutionResult } from '../api';
import { MonacoCodeEditor } from './MonacoCodeEditor';
import { Markdown } from './Markdown';

import { sanitizeSvg } from '../sanitizeSvg';

interface ArtifactCanvasProps {
  artifact: Artifact | null;
  onClose: () => void;
  defaultSmbFolder?: string;
  onPartialEdit?: (artifactTitle: string, startLine: number, endLine: number, instructions: string) => void;
}

export const ArtifactCanvas: React.FC<ArtifactCanvasProps> = ({
  artifact,
  onClose,
  defaultSmbFolder = '04 Codice',
  onPartialEdit,
}) => {
  const { t } = useStudioI18n();
  const [activeTab, setActiveTab] = useState<'code' | 'preview'>('preview');
  const [copied, setCopied] = useState(false);
  const [savingSmb, setSavingSmb] = useState(false);
  const [savedUnc, setSavedUnc] = useState<string | null>(null);

  const [isPartialEditOpen, setIsPartialEditOpen] = useState(false);
  const [startLine, setStartLine] = useState<number>(1);
  const [endLine, setEndLine] = useState<number>(10);
  const [partialInstructions, setPartialInstructions] = useState<string>('');

  const [draft, setDraft] = useState<string>(artifact?.content ?? '');
  const [past, setPast] = useState<string[]>([]);
  const [future, setFuture] = useState<string[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [showApproveModal, setShowApproveModal] = useState(false);

  useEffect(() => {
    setDraft(artifact?.content ?? '');
    setPast([]);
    setFuture([]);
    setIsEditing(false);
    setExecutionResult(null);
    setShowApproveModal(false);
  }, [artifact?.id, artifact?.content]);

  if (!artifact) return null;

  const content = draft;
  const isDirty = content !== artifact.content;
  const isExecutable = artifact.kind === 'code' || ['python', 'py', 'sh', 'bash', 'js', 'javascript'].includes((artifact.language || '').toLowerCase());

  const handleExecute = async () => {
    setShowApproveModal(false);
    setIsRunning(true);
    setExecutionResult(null);
    try {
      const res = await executeCode(content, artifact.language || 'python');
      setExecutionResult(res);
    } catch (err) {
      setExecutionResult({
        ok: false,
        exit_code: -1,
        output: String((err as Error).message || err),
        duration_ms: 0,
      });
    } finally {
      setIsRunning(false);
    }
  };


  const applyEdit = (next: string) => {
    if (next === draft) return;
    setPast((p) => [...p.slice(-49), draft]);
    setFuture([]);
    setDraft(next);
  };
  const undo = () => {
    if (past.length === 0) return;
    setFuture((f) => [draft, ...f]);
    setDraft(past[past.length - 1]);
    setPast((p) => p.slice(0, -1));
  };
  const redo = () => {
    if (future.length === 0) return;
    setPast((p) => [...p, draft]);
    setDraft(future[0]);
    setFuture((f) => f.slice(1));
  };
  const revert = () => {
    if (!isDirty) return;
    setPast((p) => [...p.slice(-49), draft]);
    setFuture([]);
    setDraft(artifact.content);
  };

  const lines = content.split('\n');
  const lineCount = lines.length;
  const canPreview = artifact.kind === 'html' || artifact.kind === 'svg' || artifact.kind === 'markdown' || artifact.kind === '3d';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const handleSaveSmb = async () => {
    setSavingSmb(true);
    setSavedUnc(null);
    try {
      const res = await saveSmbFile({
        folder: defaultSmbFolder,
        filename: artifact.title,
        content,
      });
      setSavedUnc(res.unc_path);
      setTimeout(() => setSavedUnc(null), 4000);
    } catch (err) {
      console.error(err);
    } finally {
      setSavingSmb(false);
    }
  };

  const handleSendPartialEdit = () => {
    if (!partialInstructions.trim()) return;
    onPartialEdit?.(artifact.title, startLine, endLine, partialInstructions);
    setIsPartialEditOpen(false);
    setPartialInstructions('');
  };

  return (
    <aside className="w-full h-full flex flex-col bg-slate-950 border-l border-slate-800/80 backdrop-blur-md shadow-2xl z-20">
      <div className="px-4 py-3 border-b border-slate-800/80 bg-slate-900/80 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-cyan-400 font-bold">📄</span>
          <span className="font-semibold text-xs text-slate-100 truncate">
            {artifact.title}
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-cyan-400 font-mono">
            {artifact.language}
          </span>
          <span className="px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-800/80 text-[10px] text-cyan-300 font-mono">
            🔢 {lineCount} {lineCount === 1 ? 'riga' : 'righe'}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {canPreview && (
            <div className="flex items-center bg-slate-800/90 p-0.5 rounded-lg border border-slate-700 text-[11px]">
              <button
                type="button"
                onClick={() => setActiveTab('preview')}
                className={`px-2 py-0.5 rounded-md font-medium transition-all ${
                  activeTab === 'preview'
                    ? 'bg-cyan-500/20 text-cyan-300'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t('preview')}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('code')}
                className={`px-2 py-0.5 rounded-md font-medium transition-all ${
                  activeTab === 'code'
                    ? 'bg-cyan-500/20 text-cyan-300'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t('code_view')}
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={() => setIsPartialEditOpen((prev) => !prev)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition-colors ${
              isPartialEditOpen
                ? 'bg-cyan-600 text-white border-cyan-500'
                : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
            }`}
            title="Modifica solo una porzione del file"
          >
            ✂️ Modifica parte
          </button>

          {isExecutable && (
            <button
              type="button"
              disabled={isRunning}
              onClick={() => setShowApproveModal(true)}
              className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-xs text-emerald-300 font-medium transition-colors flex items-center gap-1.5"
              title={t('sandbox_run')}
            >
              <span>{isRunning ? '⏳' : '▶'}</span>
              <span>{isRunning ? t('sandbox_running') : t('sandbox_btn')}</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleCopy}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 transition-colors"
          >
            {copied ? t('copied') : t('copy_code')}
          </button>

          <button
            type="button"
            disabled={savingSmb}
            onClick={handleSaveSmb}
            className="px-2.5 py-1 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 text-xs text-cyan-300 font-medium transition-colors"
          >
            {savingSmb ? t('saving') : `🗄️ ${t('save_to_smb')}`}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors ml-1"
            title={t('close')}
          >
            ✕
          </button>
        </div>
      </div>

      <div className="px-3 py-1.5 border-b border-slate-800/80 bg-slate-900/60 flex items-center gap-1.5 text-xs">
        <button
          type="button"
          onClick={() => {
            setIsEditing((v) => !v);
            setActiveTab('code');
          }}
          className={`px-2 py-1 rounded-lg border transition-colors ${
            isEditing ? 'bg-cyan-600 text-white border-cyan-500' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
          }`}
        >
          ✎ {t('canvas_edit')}
        </button>
        <button type="button" onClick={undo} disabled={past.length === 0} className="px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 disabled:opacity-30" title={t('canvas_undo')}>
          ↶
        </button>
        <button type="button" onClick={redo} disabled={future.length === 0} className="px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 disabled:opacity-30" title={t('canvas_redo')}>
          ↷
        </button>
        <button type="button" onClick={revert} disabled={!isDirty} className="px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 disabled:opacity-30">
          {t('canvas_revert')}
        </button>
        <span className="ml-auto text-[10px] font-mono text-slate-500">
          {isDirty ? `● ${t('canvas_modified')} · ` : ''}v{past.length + 1} · {lineCount} {t('canvas_lines')}
        </span>
      </div>

      {executionResult && (
        <div className="p-3 bg-slate-950 border-b border-slate-800 flex flex-col gap-1.5 text-xs font-mono">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5">
              <span>🖥️ {t('sandbox_console')}</span>
              <span className={executionResult.ok ? 'text-emerald-400 font-semibold' : 'text-red-400 font-semibold'}>
                {executionResult.ok ? `(${t('sandbox_ok')})` : `(${t('sandbox_fail')} code ${executionResult.exit_code})`}
              </span>
            </span>
            <span className="text-[10px] text-slate-500">{executionResult.duration_ms}ms</span>
          </div>
          <pre className="max-h-40 overflow-y-auto p-2 bg-slate-900 rounded-lg border border-slate-800 text-slate-200 whitespace-pre-wrap select-text">
            {executionResult.output}
          </pre>
        </div>
      )}

      {showApproveModal && (
        <div className="p-3 bg-cyan-950/40 border-b border-cyan-800/60 flex items-center justify-between text-xs gap-2">
          <span className="text-cyan-200">🛡️ {t('sandbox_confirm')}</span>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setShowApproveModal(false)}
              className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
            >
              {t('close')}
            </button>
            <button
              type="button"
              onClick={handleExecute}
              className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow-sm"
            >
              {t('sandbox_approve')}
            </button>
          </div>
        </div>
      )}

      {isPartialEditOpen && (
        <div className="p-3 bg-slate-900 border-b border-slate-800 flex flex-col gap-2 text-xs">
          <div className="flex items-center justify-between text-slate-300 font-semibold">
            <span>✂️ Modifica Parziale (Intervallo di Righe)</span>
            <span className="text-[11px] font-mono text-cyan-400">Totale: {lineCount} righe</span>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 text-slate-400">
              <span>Da riga:</span>
              <input
                type="number"
                min={1}
                max={lineCount}
                value={startLine}
                onChange={(e) => setStartLine(Number(e.target.value))}
                className="w-16 px-2 py-1 rounded bg-slate-950 border border-slate-700 text-white font-mono text-xs"
              />
            </label>

            <label className="flex items-center gap-1 text-slate-400">
              <span>A riga:</span>
              <input
                type="number"
                min={1}
                max={lineCount}
                value={endLine}
                onChange={(e) => setEndLine(Number(e.target.value))}
                className="w-16 px-2 py-1 rounded bg-slate-950 border border-slate-700 text-white font-mono text-xs"
              />
            </label>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Istruzioni per modificare solo queste righe..."
              value={partialInstructions}
              onChange={(e) => setPartialInstructions(e.target.value)}
              className="flex-1 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs placeholder:text-slate-500"
            />
            <button
              type="button"
              onClick={handleSendPartialEdit}
              className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs transition-colors shadow-sm"
            >
              Applica
            </button>
          </div>
        </div>
      )}

      {savedUnc && (
        <div className="px-4 py-2 bg-emerald-950/40 border-b border-emerald-800/40 text-xs text-emerald-300 flex items-center justify-between">
          <span>✓ {t('saved_smb_success')}</span>
          <span className="font-mono text-[10px] text-emerald-400/80 truncate max-w-[200px]">
            {savedUnc}
          </span>
        </div>
      )}

      <div className="flex-1 overflow-auto bg-slate-950/60 p-4">
        {canPreview && activeTab === 'preview' ? (
          artifact.kind === 'html' ? (
            <iframe
              title={artifact.title}
              sandbox="allow-scripts"
              srcDoc={content}
              className="w-full h-full min-h-[400px] rounded-xl border border-slate-800 bg-white"
            />
          ) : artifact.kind === 'svg' ? (
            <div
              className="w-full h-full min-h-[400px] flex items-center justify-center p-4 bg-slate-900 rounded-xl border border-slate-800"
              dangerouslySetInnerHTML={{ __html: sanitizeSvg(content) }}
            />
          ) : artifact.kind === '3d' ? (
            <div className="w-full h-full min-h-[400px] flex flex-col items-center justify-center p-6 bg-slate-900 rounded-xl border border-slate-800 text-center gap-3">
              <span className="text-5xl">🧊</span>
              <span className="text-sm font-bold text-white">{artifact.title}</span>
              <p className="text-xs text-slate-400 max-w-xs">
                Modello 3D CAD parametrico ({artifact.language}). Visualizzabile in viewport 3D WebGL con assi e rotazione.
              </p>
              <pre className="w-full max-h-48 overflow-y-auto text-left font-mono text-[11px] p-2 bg-slate-950 rounded border border-slate-800 text-cyan-300">
                <code>{content}</code>
              </pre>
            </div>
          ) : (
            <div className="font-sans text-xs text-slate-200 leading-relaxed">
              {artifact.kind === 'markdown' ? <Markdown source={content} /> : <div className="whitespace-pre-wrap">{content}</div>}
            </div>
          )
        ) : isEditing ? (
          <MonacoCodeEditor
            value={content}
            language={artifact.language || (artifact.kind === 'code' ? 'python' : 'plaintext')}
            onChange={applyEdit}
          />
        ) : (
          <div className="flex font-mono text-xs text-slate-200 leading-relaxed overflow-x-auto whitespace-pre">
            <div className="select-none text-slate-600 pr-3 border-r border-slate-800 mr-3 text-right">
              {lines.map((_, idx) => (
                <div key={idx}>{idx + 1}</div>
              ))}
            </div>
            <div className="flex-1">
              {lines.map((line, idx) => {
                const lineNum = idx + 1;
                const isHighlighted = isPartialEditOpen && lineNum >= startLine && lineNum <= endLine;
                return (
                  <div
                    key={idx}
                    className={isHighlighted ? 'bg-cyan-950/60 text-cyan-200 border-l-2 border-cyan-400 pl-1' : ''}
                  >
                    {line || ' '}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
