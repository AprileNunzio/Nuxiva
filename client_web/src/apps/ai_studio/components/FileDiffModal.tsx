import React, { useState } from 'react';
import type { FileDiff, DiffLine } from '../types';

interface FileDiffModalProps {
  isOpen: boolean;
  onClose: () => void;
  diffs: FileDiff[];
  initialDiffId?: string;
}

function computeDiffLines(before: string, after: string): DiffLine[] {
  const beforeLines = before.split('\n');
  const afterLines = after.split('\n');
  const result: DiffLine[] = [];

  const maxLines = Math.max(beforeLines.length, afterLines.length);
  let oldIdx = 1;
  let newIdx = 1;

  for (let i = 0; i < maxLines; i++) {
    const bLine = beforeLines[i];
    const aLine = afterLines[i];

    if (bLine === undefined) {
      result.push({ type: 'add', newNum: newIdx++, text: aLine });
    } else if (aLine === undefined) {
      result.push({ type: 'del', oldNum: oldIdx++, text: bLine });
    } else if (bLine === aLine) {
      result.push({ type: 'same', oldNum: oldIdx++, newNum: newIdx++, text: aLine });
    } else {
      result.push({ type: 'del', oldNum: oldIdx++, text: bLine });
      result.push({ type: 'add', newNum: newIdx++, text: aLine });
    }
  }

  return result;
}

export const FileDiffModal: React.FC<FileDiffModalProps> = ({
  isOpen,
  onClose,
  diffs,
  initialDiffId,
}) => {
  const [selectedDiffId, setSelectedDiffId] = useState<string>(
    initialDiffId || (diffs.length > 0 ? diffs[0].id : '')
  );
  const [viewMode, setViewMode] = useState<'unified' | 'split'>('unified');
  const [copied, setCopied] = useState(false);

  if (!isOpen || diffs.length === 0) return null;

  const currentDiff = diffs.find((d) => d.id === selectedDiffId) || diffs[0];
  const computedLines = currentDiff.lines && currentDiff.lines.length > 0
    ? currentDiff.lines
    : computeDiffLines(currentDiff.before_content, currentDiff.after_content);

  const handleCopy = () => {
    navigator.clipboard.writeText(currentDiff.after_content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([currentDiff.after_content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentDiff.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-cyan-400 font-mono text-base">⇄</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-100">
                  Confronto File Modificati (Prima / Dopo)
                </span>
                <span className="px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-800 text-[10px] text-cyan-300 font-mono">
                  {diffs.length} {diffs.length === 1 ? 'file' : 'file'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Ispezione differenziale delle modifiche applicate dall'agente
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex rounded-lg bg-slate-800 p-0.5 border border-slate-700 text-xs">
              <button
                type="button"
                onClick={() => setViewMode('unified')}
                className={`px-3 py-1 rounded-md transition-all ${
                  viewMode === 'unified'
                    ? 'bg-cyan-600 text-white font-medium shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Unificato
              </button>
              <button
                type="button"
                onClick={() => setViewMode('split')}
                className={`px-3 py-1 rounded-md transition-all ${
                  viewMode === 'split'
                    ? 'bg-cyan-600 text-white font-medium shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Affiancato (Prima / Dopo)
              </button>
            </div>

            <button
              type="button"
              onClick={handleCopy}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
              title="Copia codice finale"
            >
              {copied ? '✓ Copiato' : 'Copia'}
            </button>

            <button
              type="button"
              onClick={handleDownload}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs font-medium border border-slate-700 transition-colors"
              title="Scarica file aggiornato"
            >
              Scarica
            </button>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 text-sm transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {diffs.length > 1 && (
            <div className="w-64 border-r border-slate-800 bg-slate-950/60 p-3 overflow-y-auto flex flex-col gap-1.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 mb-1">
                File Modificati
              </div>
              {diffs.map((d) => {
                const isSelected = d.id === currentDiff.id;
                return (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => setSelectedDiffId(d.id)}
                    className={`text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between border transition-all ${
                      isSelected
                        ? 'bg-cyan-950/60 border-cyan-500/80 text-cyan-200 shadow-sm'
                        : 'bg-slate-900/40 border-slate-800/60 text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-mono text-[10px] px-1 py-0.5 rounded bg-slate-800 text-cyan-400 uppercase">
                        {d.ext || 'file'}
                      </span>
                      <span className="truncate font-medium">{d.filename}</span>
                    </div>
                    <div className="flex items-center gap-1 font-mono text-[10px]">
                      <span className="text-emerald-400">+{d.added}</span>
                      <span className="text-rose-400">-{d.removed}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          <div className="flex-1 flex flex-col min-w-0 bg-slate-950 overflow-hidden">
            <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/40 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 text-[11px]">
                  {currentDiff.ext}
                </span>
                <span className="font-medium text-slate-200">{currentDiff.filename}</span>
              </div>
              <div className="flex items-center gap-3 font-mono text-xs">
                <span className="text-emerald-400 font-medium">+{currentDiff.added} aggiunte</span>
                <span className="text-rose-400 font-medium">-{currentDiff.removed} rimozioni</span>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-3 font-mono text-xs leading-relaxed">
              {viewMode === 'unified' ? (
                <div className="flex flex-col gap-0.5">
                  {computedLines.map((line, idx) => {
                    const isAdd = line.type === 'add';
                    const isDel = line.type === 'del';
                    return (
                      <div
                        key={idx}
                        className={`flex items-start px-2 py-0.5 rounded ${
                          isAdd
                            ? 'bg-emerald-950/50 text-emerald-200 border-l-2 border-emerald-500'
                            : isDel
                            ? 'bg-rose-950/50 text-rose-200 border-l-2 border-rose-500 line-through opacity-80'
                            : 'text-slate-300 hover:bg-slate-900/50'
                        }`}
                      >
                        <div className="w-16 shrink-0 flex justify-between pr-3 text-slate-600 select-none text-[11px]">
                          <span>{line.oldNum || ''}</span>
                          <span>{line.newNum || ''}</span>
                        </div>
                        <span className="w-4 shrink-0 text-slate-500 select-none">
                          {isAdd ? '+' : isDel ? '-' : ' '}
                        </span>
                        <pre className="flex-1 overflow-x-auto whitespace-pre font-mono">
                          {line.text}
                        </pre>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 h-full">
                  <div className="border border-slate-800 rounded-xl bg-slate-900/40 p-3 overflow-auto flex flex-col">
                    <div className="text-[11px] font-semibold text-rose-300 pb-2 mb-2 border-b border-slate-800 flex items-center justify-between">
                      <span>PRIMA (ORIGINALE)</span>
                      <span className="text-rose-400 font-mono">-{currentDiff.removed}</span>
                    </div>
                    <pre className="text-rose-200/90 whitespace-pre font-mono text-xs overflow-x-auto flex-1">
                      {currentDiff.before_content}
                    </pre>
                  </div>

                  <div className="border border-slate-800 rounded-xl bg-slate-900/40 p-3 overflow-auto flex flex-col">
                    <div className="text-[11px] font-semibold text-emerald-300 pb-2 mb-2 border-b border-slate-800 flex items-center justify-between">
                      <span>DOPO (MODIFICATO)</span>
                      <span className="text-emerald-400 font-mono">+{currentDiff.added}</span>
                    </div>
                    <pre className="text-emerald-200 whitespace-pre font-mono text-xs overflow-x-auto flex-1">
                      {currentDiff.after_content}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
