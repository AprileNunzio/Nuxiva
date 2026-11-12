import React, { useState } from 'react';
import { ArrowUp, Loader2, Sparkles } from 'lucide-react';

interface PromptBarProps {
  readonly placeholder: string;
  readonly action: string;
  readonly busy: boolean;
  readonly disabled: boolean;
  readonly onSubmit: (text: string) => void;
  readonly examples?: readonly string[];
}

export const PromptBar: React.FC<PromptBarProps> = ({ placeholder, action, busy, disabled, onSubmit, examples = [] }) => {
  const [text, setText] = useState('');
  const send = () => {
    const value = text.trim();
    if (value.length < 3 || busy || disabled) return;
    onSubmit(value);
    setText('');
  };
  return (
    <div className="w-full">
      {examples.length > 0 && (
        <div className="mb-3 flex flex-wrap justify-center gap-2">
          {examples.map((example) => (
            <button key={example} type="button" onClick={() => setText(example)} className="rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition hover:border-sky-300 hover:text-sky-700">
              {example}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2 rounded-3xl border border-slate-200 bg-white/95 p-2 shadow-lg shadow-slate-200/60 backdrop-blur focus-within:border-sky-400 focus-within:ring-4 focus-within:ring-sky-100">
        <Sparkles className="mb-3 ml-2 h-5 w-5 shrink-0 text-sky-500" />
        <textarea
          value={text}
          rows={1}
          maxLength={600}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder={placeholder}
          className="max-h-32 min-h-[44px] flex-1 resize-none bg-transparent px-1 py-3 text-sm text-slate-900 outline-none placeholder:text-slate-400"
        />
        <button type="button" onClick={send} disabled={busy || disabled || text.trim().length < 3} aria-label={action} className="mb-0.5 flex h-10 shrink-0 items-center gap-2 rounded-2xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
          <span className="hidden sm:inline">{action}</span>
        </button>
      </div>
    </div>
  );
};
