import React, { useState, useRef, useEffect } from 'react';
import { useStudioI18n } from '../scope';
import type { Message, Artifact, Thread, Project, Workpiece3DData, FileDiff } from '../types';
import { ThoughtActionBlock } from './ThoughtActionBlock';

interface ConversationViewProps {
  thread: Thread | null;
  project: Project | null;
  messages: Message[];
  isThinking: boolean;
  onOpenArtifact: (artifact: Artifact) => void;
  onOpen3DViewer?: (data?: Workpiece3DData) => void;
  onOpenDiff?: (diffId?: string, diffs?: FileDiff[]) => void;
  onFeedback?: (messageId: string, type: 'positive' | 'negative') => void;
  onQuickPrompt?: (prompt: string) => void;
}

export const ConversationView: React.FC<ConversationViewProps> = ({
  thread,
  project,
  messages,
  isThinking,
  onOpenArtifact,
  onOpen3DViewer,
  onOpenDiff,
  onFeedback,
  onQuickPrompt,
}) => {
  const { t } = useStudioI18n();
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [feedbackState, setFeedbackState] = useState<Record<string, 'positive' | 'negative'>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  useEffect(() => {
    return () => {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handlePlayAudio = (msg: Message) => {
    if (playingAudioId === msg.id) {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setPlayingAudioId(null);
      return;
    }

    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    if (msg.audio_url) {
      const audio = new Audio(msg.audio_url);
      currentAudioRef.current = audio;
      setPlayingAudioId(msg.id);
      audio.onended = () => setPlayingAudioId(null);
      audio.onerror = () => setPlayingAudioId(null);
      audio.play().catch(() => setPlayingAudioId(null));
    } else if ('speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(msg.content);
      utter.lang = 'it-IT';
      utter.rate = 1.05;
      utter.onend = () => setPlayingAudioId(null);
      utter.onerror = () => setPlayingAudioId(null);
      setPlayingAudioId(msg.id);
      window.speechSynthesis.speak(utter);
    }
  };

  const handleFeedbackClick = (msgId: string, type: 'positive' | 'negative') => {
    setFeedbackState((prev) => ({ ...prev, [msgId]: type }));
    onFeedback?.(msgId, type);
  };

  const handleCopyMessage = (msgId: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 1800);
  };

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


  const isLiveVoice = thread?.id === 'th_live_voice_port80';

  const allDiffsAcrossMessages = messages.flatMap((m) => m.diffs || []);

  return (
    <div className="flex-1 h-full flex flex-col bg-slate-950 overflow-hidden print:bg-white print:text-black">
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
          {allDiffsAcrossMessages.length > 0 && onOpenDiff && (
            <button
              type="button"
              onClick={() => onOpenDiff(undefined, allDiffsAcrossMessages)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/70 hover:bg-emerald-900/80 border border-emerald-700/60 text-emerald-300 hover:text-white text-xs font-medium transition-all shadow-sm"
              title="Visualizza confronto prima/dopo per tutti i file modificati"
            >
              <span>⇄</span>
              <span>Diff File ({allDiffsAcrossMessages.length})</span>
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

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5 print:p-0 print:overflow-visible">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500 gap-2">
            <span className="text-4xl">{isLiveVoice ? '🎙️' : '🤖'}</span>
            <p className="text-sm max-w-sm">
              {isLiveVoice
                ? 'Nessuna conversazione vocale rilevata sulla Porta 80. Parla al microfono per avviare il duplex live.'
                : t('no_messages')}
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            const isPlaying = playingAudioId === msg.id;
            const userFeedback = feedbackState[msg.id] || msg.feedback;
            const isCopied = copiedId === msg.id;

            return (
              <div
                key={msg.id}
                className={`flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'} print:items-start`}
              >
                <div className="flex items-center gap-2 px-1">
                  <span className="text-[11px] font-medium text-slate-500 print:text-black font-semibold">
                    {isUser ? t('role_user') : t('role_nuxiva')}
                  </span>
                  {!isUser && msg.cached && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono font-medium text-emerald-400 border border-emerald-500/20">
                      ⚡ {t('cached_reply')}
                    </span>
                  )}
                  <span className="text-[10px] text-slate-600 print:text-slate-400">
                    {new Date(msg.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                {!isUser && (
                  <ThoughtActionBlock
                    thought={msg.thought}
                    thinkingDuration={msg.thinking_duration}
                    actions={msg.actions}
                    onOpenDiff={(diffId) => onOpenDiff?.(diffId, msg.diffs)}
                  />
                )}

                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-2xl shadow-sm print:max-w-full print:bg-white print:text-black print:border-b ${
                    isUser
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-tr-xs'
                      : 'bg-slate-900/90 border border-slate-800 text-slate-100 rounded-tl-xs'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>

                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/10">
                      {msg.attachments.map((att) => (
                        <div
                          key={att.id}
                          className="flex items-center gap-1 px-2 py-0.5 rounded bg-black/20 text-xs"
                        >
                          <span>📎</span>
                          <span className="truncate max-w-[150px]">{att.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-0.5 px-1 print:hidden">
                  <button
                    type="button"
                    onClick={() => handlePlayAudio(msg)}
                    className={`flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-xs font-medium border transition-all ${
                      isPlaying
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500 animate-pulse'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-slate-700'
                    }`}
                    title="Ascolta audio registrato o sintetizzato"
                  >
                    <span>{isPlaying ? '⏸️' : '🔊'}</span>
                    <span>{isPlaying ? 'In Riproduzione...' : 'Ascolta'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleCopyMessage(msg.id, msg.content)}
                    className="p-1 rounded-md text-slate-500 hover:text-slate-300 text-xs transition-colors"
                    title="Copia testo messaggio"
                  >
                    {isCopied ? '✓' : '📋'}
                  </button>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleFeedbackClick(msg.id, 'positive')}
                      className={`p-1 rounded-md text-xs transition-colors ${
                        userFeedback === 'positive'
                          ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800'
                          : 'text-slate-500 hover:text-emerald-400'
                      }`}
                      title="Feedback positivo"
                    >
                      👍
                    </button>
                    <button
                      type="button"
                      onClick={() => handleFeedbackClick(msg.id, 'negative')}
                      className={`p-1 rounded-md text-xs transition-colors ${
                        userFeedback === 'negative'
                          ? 'text-red-400 bg-red-950/60 border border-red-800'
                          : 'text-slate-500 hover:text-red-400'
                      }`}
                      title="Segnala risposta"
                    >
                      👎
                    </button>
                    {userFeedback && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        ✓ Inviato
                      </span>
                    )}
                  </div>

                  {msg.diffs && msg.diffs.length > 0 && onOpenDiff && (
                    <button
                      type="button"
                      onClick={() => onOpenDiff(undefined, msg.diffs)}
                      className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800/80 text-[10px] text-emerald-300 hover:text-white transition-colors"
                    >
                      <span>⇄</span>
                      <span>{msg.diffs.length} file modificati</span>
                    </button>
                  )}

                  {onOpen3DViewer && (msg.content.toLowerCase().includes('3d') || msg.content.toLowerCase().includes('cad') || msg.content.toLowerCase().includes('laser')) && (
                    <button
                      type="button"
                      onClick={() => onOpen3DViewer({
                        title: `Lavorazione 3D · ${msg.content.slice(0, 30)}`,
                        format: 'openscad',
                        dimensions_mm: [60, 90, 30],
                      })}
                      className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/80 text-[10px] text-cyan-300 hover:text-white transition-colors"
                    >
                      <span>🧊</span>
                      <span>Finestra 3D</span>
                    </button>
                  )}
                </div>

                {!isUser && msg.artifacts && msg.artifacts.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-1 max-w-2xl print:hidden">
                    {msg.artifacts.map((art) => (
                      <div
                        key={art.id}
                        onClick={() => {
                          if (art.kind === '3d' && onOpen3DViewer) {
                            onOpen3DViewer({
                              title: art.title,
                              format: 'openscad',
                              code: art.content,
                            });
                          } else {
                            onOpenArtifact(art);
                          }
                        }}
                        className="flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-slate-900/90 border border-slate-700/80 hover:border-cyan-500/80 cursor-pointer text-xs transition-all shadow-md group"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-cyan-400">
                            {art.kind === 'code' ? '💻' : art.kind === 'html' ? '🌐' : art.kind === '3d' ? '🧊' : '📊'}
                          </span>
                          <span className="font-medium text-slate-200 group-hover:text-cyan-300 truncate">
                            {art.title}
                          </span>
                        </div>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-cyan-400 font-medium">
                          {art.kind === '3d' ? 'Visualizza 3D ↗' : `${t('open_in_canvas')} ↗`}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}

        {isThinking && (
          <div className="flex items-center gap-2 text-slate-400 text-xs bg-slate-900/60 border border-slate-800 px-3 py-2 rounded-xl w-fit animate-pulse print:hidden">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
            <span>Nuxiva {t('thought_process').toLowerCase()}...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
