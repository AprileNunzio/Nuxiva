import React, { useState } from 'react';
import { useStudioI18n } from '../scope';
import type { Thread, Project, Workpiece3DData, FileDiff, Message } from '../types';

interface ConversationHeaderProps {
  thread: Thread | null;
  project: Project | null;
  messages: Message[];
  allDiffs: FileDiff[];
  onOpenArtifact?: () => void;
  onOpen3DViewer?: (data?: Workpiece3DData) => void;
  onOpenDiff?: (diffId?: string, diffs?: FileDiff[]) => void;
  onQuickPrompt?: (prompt: string) => void;
}

export const ConversationHeader: React.FC<ConversationHeaderProps> = ({
  thread,
  project,
  messages,
  allDiffs,
  onOpen3DViewer,
  onOpenDiff,
  onQuickPrompt,
}) => {
  const { t } = useStudioI18n();
  const [showExportMenu, setShowExportMenu] = useState(false);

  const isLiveVoice = thread?.id === 'th_live_voice_port80';

  const handlePrint = () => {
    window.print();
  };

  const handleExport = (format: 'md' | 'json') => {
    const title = thread?.title || 'conversazione_nuxiva';
    let content = '';
    let mime = 'text/plain';
    if (format === 'md') {
      const lines = [`# ${title}\n`];
      messages.forEach((m) => {
        lines.push(`### ${m.role === 'user' ? 'UTENTE' : 'NUXIVA'} (${new Date(m.created_at * 1000).toLocaleString()})\n${m.thought ? `> **Pensiero:** ${m.thought}\n\n` : ''}${m.content}\n`);
      });
      content = lines.join('\n');
      mime = 'text/markdown';
    } else {
      content = JSON.stringify({ thread: thread?.title, project: project?.name, exported_at: new Date().toISOString(), messages }, null, 2);
      mime = 'application/json';
    }
    const blob = new Blob([content], { type: `${mime};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
    setShowExportMenu(false);
  };

  return (
    <>
      <div className="px-4 py-2.5 border-b border-slate-800/80 bg-slate-900/70 backdrop-blur-md flex items-center justify-between print:hidden">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-cyan-400 font-semibold text-sm">✦</span>
          <h1 className="text-sm font-semibold text-slate-100 truncate">
            {isLiveVoice ? 'Conversazione Vocale (Pagina 80 Live)' : (thread?.title || t('title'))}
          </h1>
          {isLiveVoice && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-500/50 text-[10px] text-cyan-300 font-mono animate-pulse">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              <span>LIVE DUPLEX</span>
            </span>
          )}
          {project && !isLiveVoice && (
            <span className="px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-[10px] text-cyan-300 font-medium truncate">
              📁 {project.name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {allDiffs.length > 0 && onOpenDiff && (
            <button
              type="button"
              onClick={() => onOpenDiff(undefined, allDiffs)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/70 hover:bg-emerald-900/80 border border-emerald-700/60 text-emerald-300 hover:text-white text-xs font-medium transition-all shadow-sm"
              title="Visualizza confronto prima/dopo per tutti i file modificati"
            >
              <span>⇄</span>
              <span>Diff File ({allDiffs.length})</span>
            </button>
          )}

          {onOpen3DViewer && (
            <button
              type="button"
              onClick={() => onOpen3DViewer({
                title: thread?.title ? `Lavorazione 3D · ${thread.title}` : 'Lavorazione 3D CAD & Laser CNC',
                format: 'openscad',
                dimensions_mm: [60, 90, 30],
                material: 'PLA / Compensato Laser',
              })}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-700/80 text-cyan-300 hover:text-white text-xs font-medium transition-all shadow-sm"
              title="Apri finestra lavorazione 3D"
            >
              <span>🧊</span>
              <span>Lavorazione 3D</span>
            </button>
          )}

          <div className="relative">
            <button
              type="button"
              onClick={() => setShowExportMenu((p) => !p)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium border border-slate-700 transition-colors"
              title="Opzioni esportazione"
            >
              <span>📥</span>
              <span>Esporta</span>
            </button>

            {showExportMenu && (
              <div className="absolute right-0 mt-1 w-44 rounded-xl bg-slate-900 border border-slate-700 shadow-xl py-1 z-30 text-xs">
                <button
                  type="button"
                  onClick={() => handleExport('md')}
                  className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 hover:text-cyan-300 flex items-center gap-2"
                >
                  <span>📝</span>
                  <span>Markdown (.md)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleExport('json')}
                  className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 hover:text-cyan-300 flex items-center gap-2"
                >
                  <span>⚙️</span>
                  <span>JSON Completo</span>
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium border border-slate-700 transition-colors"
            title="Stampa o esporta PDF"
          >
            <span>🖨️</span>
            <span>Stampa</span>
          </button>
        </div>
      </div>

      <div className="px-4 py-1.5 bg-slate-900/40 border-b border-slate-800/40 flex items-center gap-2 overflow-x-auto text-[11px] text-slate-400 print:hidden">
        <span className="font-semibold text-cyan-400 uppercase tracking-wider text-[10px]">
          Strumenti Rapidi:
        </span>
        <button
          type="button"
          onClick={() => onQuickPrompt?.('Genera codice completo modulare e moderno per la richiesta attuale')}
          className="px-2 py-0.5 rounded-full bg-slate-800/60 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 border border-slate-700/60 transition-colors whitespace-nowrap"
        >
          ⚡ Genera Codice
        </button>
        <button
          type="button"
          onClick={() => onQuickPrompt?.('Analizza le differenze dei file modificati e crea un report prima/dopo')}
          className="px-2 py-0.5 rounded-full bg-slate-800/60 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 border border-slate-700/60 transition-colors whitespace-nowrap"
        >
          🔍 Analisi & Diff
        </button>
        <button
          type="button"
          onClick={() => onQuickPrompt?.('Crea un pezzo 3D parametrico CAD per taglio laser o lavorazione CNC')}
          className="px-2 py-0.5 rounded-full bg-slate-800/60 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 border border-slate-700/60 transition-colors whitespace-nowrap"
        >
          🧊 CAD 3D & Laser
        </button>
        <button
          type="button"
          onClick={() => onQuickPrompt?.('Fai un riassunto esecutivo di tutte le modifiche e passi eseguiti')}
          className="px-2 py-0.5 rounded-full bg-slate-800/60 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 border border-slate-700/60 transition-colors whitespace-nowrap"
        >
          📝 Riassunto
        </button>
      </div>

      {isLiveVoice && (
        <div className="px-4 py-2 bg-gradient-to-r from-cyan-950/60 to-blue-950/60 border-b border-cyan-900/40 text-xs text-cyan-200 flex items-center justify-between print:hidden">
          <div className="flex items-center gap-2">
            <span>🎙️</span>
            <span>Trascrizione duplex live tra utente e Nuxiva (Porta 80) · Sincronizzazione audio attiva</span>
          </div>
          <span className="font-mono text-[10px] text-cyan-400/80">Replay & Feedback Abilitato</span>
        </div>
      )}
    </>
  );
};
