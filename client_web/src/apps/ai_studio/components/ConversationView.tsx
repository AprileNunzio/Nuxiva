import React, { useState, useRef, useEffect } from 'react';
import { useStudioI18n } from '../scope';
import type { Message, Artifact, Thread, Project, Workpiece3DData, FileDiff } from '../types';
import { ConversationHeader } from './ConversationHeader';
import { ThoughtActionBlock } from './ThoughtActionBlock';
import { MessageReactions } from './MessageReactions';
import { InteractivePollCard } from './InteractivePollCard';
import { DomainWidgetsPanel } from './DomainWidgetsPanel';
import { Markdown } from './Markdown';
import { formatThinking } from '../thinking';

interface ConversationViewProps {
  thread: Thread | null;
  project: Project | null;
  messages: Message[];
  isThinking: boolean;
  onOpenArtifact: (artifact: Artifact) => void;
  onOpen3DViewer?: (data?: Workpiece3DData) => void;
  onOpenDiff?: (diffId?: string, diffs?: FileDiff[]) => void;
  onFeedback?: (messageId: string, type: 'positive' | 'negative' | null) => void;
  onToggleReaction?: (messageId: string, emoji: string) => void;
  onVotePoll?: (messageId: string, pollId: string, optionId: string, stepIndex?: number) => void;
  onSubmitSurvey?: (messageId: string, pollId: string, answers: Record<string, string>) => void;
  onQuickPrompt?: (prompt: string) => void;
  onRegenerate?: () => void;
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
  onToggleReaction,
  onVotePoll,
  onSubmitSurvey,
  onQuickPrompt,
  onRegenerate,
}) => {
  const { t } = useStudioI18n();
  const safeMessages = Array.isArray(messages) ? messages.filter(Boolean) : [];
  const lastAssistantId = [...safeMessages].reverse().find((m) => m && m.role !== 'user')?.id;
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
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

  const handleFeedbackClick = (msg: Message, type: 'positive' | 'negative') => {
    onFeedback?.(msg.id, msg.feedback === type ? null : type);
  };

  const handleCopyMessage = (msgId: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const allDiffsAcrossMessages = messages.flatMap((m) => m.diffs || []);

  return (
    <div className="flex-1 h-full flex flex-col bg-slate-950 overflow-hidden print:bg-white print:text-black">
      <ConversationHeader
        thread={thread}
        project={project}
        messages={messages}
        allDiffs={allDiffsAcrossMessages}
        onOpen3DViewer={onOpen3DViewer}
        onOpenDiff={onOpenDiff}
        onQuickPrompt={onQuickPrompt}
      />

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5 print:p-0 print:overflow-visible">
        {safeMessages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500 gap-2">
            <span className="text-4xl">🤖</span>
            <p className="text-sm max-w-sm">{t('no_messages')}</p>
          </div>
        ) : (
          safeMessages.map((msg) => {
            const isUser = msg.role === 'user';
            const isPlaying = playingAudioId === msg.id;
            const userFeedback = msg.feedback;
            const isCopied = copiedId === msg.id;

            return (
              <div
                key={msg.id}
                id={`studio-msg-${msg.id}`}
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
                    thinkingDuration={formatThinking(msg.thinking_ms)}
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
                  {isUser ? (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <Markdown source={msg.content} />
                  )}

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

                {msg.poll && (
                  <InteractivePollCard
                    poll={msg.poll}
                    onVote={(pollId, optId, stepIdx) => onVotePoll?.(msg.id, pollId, optId, stepIdx)}
                    onSubmitSurvey={(pollId, answers) => onSubmitSurvey?.(msg.id, pollId, answers)}
                  />
                )}

                {msg.widgets && msg.widgets.length > 0 && (
                  <DomainWidgetsPanel
                    widgets={msg.widgets}
                    onOpen3DViewer={onOpen3DViewer}
                  />
                )}

                <MessageReactions
                  reactions={msg.reactions}
                  onToggleReaction={(emoji) => onToggleReaction?.(msg.id, emoji)}
                />

                <div className="flex items-center gap-2 mt-0.5 px-1 print:hidden">
                  <button
                    type="button"
                    onClick={() => handlePlayAudio(msg)}
                    className={`flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-xs font-medium border transition-all ${
                      isPlaying
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500 animate-pulse'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-cyan-300 hover:border-slate-700'
                    }`}
                    title={t('msg_listen_hint')}
                  >
                    <span>{isPlaying ? '⏸️' : '🔊'}</span>
                    <span>{isPlaying ? t('msg_listening') : t('msg_listen')}</span>
                  </button>

                  {!isUser && onRegenerate && msg.id === lastAssistantId && !isThinking && (
                    <button
                      type="button"
                      onClick={onRegenerate}
                      className="p-1 rounded-md text-slate-500 hover:text-cyan-300 text-xs transition-colors"
                      title={t('cmd_regenerate')}
                    >
                      ↻
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => handleCopyMessage(msg.id, msg.content)}
                    className="p-1 rounded-md text-slate-500 hover:text-slate-300 text-xs transition-colors"
                    title={t('msg_copy_hint')}
                  >
                    {isCopied ? '✓' : '📋'}
                  </button>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleFeedbackClick(msg, 'positive')}
                      className={`p-1 rounded-md text-xs transition-colors ${
                        userFeedback === 'positive'
                          ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800'
                          : 'text-slate-500 hover:text-emerald-400'
                      }`}
                      title={t('msg_good')}
                    >
                      👍
                    </button>
                    <button
                      type="button"
                      onClick={() => handleFeedbackClick(msg, 'negative')}
                      className={`p-1 rounded-md text-xs transition-colors ${
                        userFeedback === 'negative'
                          ? 'text-red-400 bg-red-950/60 border border-red-800'
                          : 'text-slate-500 hover:text-red-400'
                      }`}
                      title={t('msg_bad')}
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
                      <span>{t('diff_count', { count: msg.diffs.length })}</span>
                    </button>
                  )}

                  {onOpen3DViewer && (msg.content.toLowerCase().includes('3d') || msg.content.toLowerCase().includes('cad') || msg.content.toLowerCase().includes('laser')) && (
                    <button
                      type="button"
                      onClick={() => onOpen3DViewer({
                        title: `${t('hdr_3d')} · ${msg.content.slice(0, 30)}`,
                        format: 'openscad',
                        dimensions_mm: [60, 90, 30],
                      })}
                      className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/80 text-[10px] text-cyan-300 hover:text-white transition-colors"
                    >
                      <span>🧊</span>
                      <span>{t('msg_3d')}</span>
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
            <span>{t('thinking')}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
