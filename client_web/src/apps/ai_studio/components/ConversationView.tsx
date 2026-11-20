import React, { useState, useRef, useEffect } from 'react';
import { useStudioI18n } from '../scope';
import type { Message, Artifact, Thread, Project } from '../types';

interface ConversationViewProps {
  thread: Thread | null;
  project: Project | null;
  messages: Message[];
  isThinking: boolean;
  onOpenArtifact: (artifact: Artifact) => void;
}

export const ConversationView: React.FC<ConversationViewProps> = ({
  thread,
  project,
  messages,
  isThinking,
  onOpenArtifact,
}) => {
  const { t } = useStudioI18n();
  const [expandedThoughts, setExpandedThoughts] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const toggleThought = (msgId: string) => {
    setExpandedThoughts((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  return (
    <div className="flex-1 h-full flex flex-col bg-slate-950 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-sm flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-cyan-400 font-semibold text-sm">✦</span>
          <h1 className="text-sm font-semibold text-slate-100 truncate">
            {thread?.title || t('title')}
          </h1>
          {project && (
            <span className="px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-[10px] text-cyan-300 font-medium truncate">
              📁 {project.name}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500 gap-2">
            <span className="text-4xl">🤖</span>
            <p className="text-sm max-w-sm">{t('no_messages')}</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={msg.id}
                className={`flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div className="text-[11px] font-medium text-slate-500 px-1">
                  {isUser ? 'Tu' : 'Nuxiva'}
                </div>

                {!isUser && msg.memory_recalls && msg.memory_recalls.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-1 max-w-xl">
                    {msg.memory_recalls.map((fact) => (
                      <span
                        key={fact.id}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-950/40 border border-purple-800/40 text-[10px] text-purple-300"
                      >
                        <span>{fact.source === 'voice_speech' ? '🎙️' : '🧠'}</span>
                        <span className="truncate max-w-[200px]">{fact.content}</span>
                      </span>
                    ))}
                  </div>
                )}

                {!isUser && msg.thought && (
                  <div className="w-full max-w-2xl rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden mb-1">
                    <button
                      type="button"
                      onClick={() => toggleThought(msg.id)}
                      className="w-full px-3 py-2 flex items-center justify-between text-xs text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      <span className="flex items-center gap-1.5 font-medium">
                        <span>🧠</span>
                        <span>{t('thought_process')}</span>
                      </span>
                      <span>{expandedThoughts[msg.id] ? '▲' : '▼'}</span>
                    </button>
                    {expandedThoughts[msg.id] && (
                      <div className="px-3 pb-3 text-xs text-slate-400 border-t border-slate-800/80 pt-2 whitespace-pre-wrap font-mono leading-relaxed bg-slate-950/40">
                        {msg.thought}
                      </div>
                    )}
                  </div>
                )}

                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-2xl shadow-sm ${
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

                {!isUser && msg.artifacts && msg.artifacts.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-1 max-w-2xl">
                    {msg.artifacts.map((art) => (
                      <div
                        key={art.id}
                        onClick={() => onOpenArtifact(art)}
                        className="flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-slate-900/90 border border-slate-700/80 hover:border-cyan-500/80 cursor-pointer text-xs transition-all shadow-md group"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-cyan-400">
                            {art.kind === 'code' ? '💻' : art.kind === 'html' ? '🌐' : '📊'}
                          </span>
                          <span className="font-medium text-slate-200 group-hover:text-cyan-300 truncate">
                            {art.title}
                          </span>
                        </div>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-cyan-400 font-medium">
                          {t('open_in_canvas')} ↗
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
          <div className="flex items-center gap-2 text-slate-400 text-xs bg-slate-900/60 border border-slate-800 px-3 py-2 rounded-xl w-fit animate-pulse">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
            <span>Nuxiva {t('thought_process').toLowerCase()}...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
