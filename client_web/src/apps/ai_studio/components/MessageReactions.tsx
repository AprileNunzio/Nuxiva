import React, { useState, useRef, useEffect } from 'react';
import type { Reaction } from '../types';

interface MessageReactionsProps {
  reactions?: Reaction[];
  onToggleReaction: (emoji: string) => void;
}

const COMMON_EMOJIS = ['❤️', '👍', '🚀', '💡', '🎯', '🔥', '👏', '🤔', '💬', '💯', '⚙️', '🛠️', '🧊', '✨'];

export const MessageReactions: React.FC<MessageReactionsProps> = ({
  reactions = [],
  onToggleReaction,
}) => {
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setIsPickerOpen(false);
      }
    };
    if (isPickerOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isPickerOpen]);

  const handleSelectEmoji = (emoji: string) => {
    onToggleReaction(emoji);
    setIsPickerOpen(false);
  };

  return (
    <div className="relative flex flex-wrap items-center gap-1 mt-1 print:hidden">
      {reactions.map((r) => {
        const hasUserVoted = r.authors.includes('user');
        return (
          <button
            key={r.emoji}
            type="button"
            onClick={() => onToggleReaction(r.emoji)}
            className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono border transition-all ${
              hasUserVoted
                ? 'bg-cyan-950/80 border-cyan-500/80 text-cyan-300 shadow-sm'
                : 'bg-slate-900/80 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
            }`}
            title={`Reagito da: ${r.authors.join(', ')}`}
          >
            <span>{r.emoji}</span>
            <span className="text-[11px] font-medium">{r.count}</span>
          </button>
        );
      })}

      <div className="relative" ref={pickerRef}>
        <button
          type="button"
          onClick={() => setIsPickerOpen((prev) => !prev)}
          className="flex items-center justify-center h-6 w-6 rounded-full bg-slate-900 border border-slate-800 text-slate-500 hover:text-cyan-300 hover:border-slate-700 text-xs transition-colors"
          title="Aggiungi reazione"
        >
          <span>☺+</span>
        </button>

        {isPickerOpen && (
          <div className="absolute left-0 bottom-full mb-1.5 z-40 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-2xl p-2 shadow-2xl flex flex-wrap gap-1 w-52 animate-in fade-in zoom-in-95 duration-150">
            {COMMON_EMOJIS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                onClick={() => handleSelectEmoji(emoji)}
                className="h-8 w-8 flex items-center justify-center rounded-xl hover:bg-slate-800 text-base hover:scale-110 transition-transform"
              >
                {emoji}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
