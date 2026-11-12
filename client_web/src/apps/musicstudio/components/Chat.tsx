import React, { useEffect, useRef, useState } from 'react';
import { Send } from 'lucide-react';
import { Btn, cx, inputClass } from './ui';
import type { Studio } from '../useStudio';

interface Props {
  readonly studio: Studio;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const SUGGESTIONS = ['chat_s1', 'chat_s2', 'chat_s3', 'chat_s4'];

export const Chat: React.FC<Props> = ({ studio, t }) => {
  const [text, setText] = useState('');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ block: 'end' }), [studio.chat.length]);
  const send = (message: string) => {
    const clean = message.trim();
    if (clean && !studio.busy) {
      setText('');
      void studio.talk(clean);
    }
  };
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {studio.chat.length === 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-500">{t('chat_intro')}</p>
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((key) => (
                <button key={key} type="button" onClick={() => send(t(key))} className="rounded-full bg-violet-50 px-2.5 py-1 text-[11px] text-violet-700 hover:bg-violet-100">
                  {t(key)}
                </button>
              ))}
            </div>
          </div>
        )}
        {studio.chat.map((turn, i) => (
          <div key={i} className={cx('flex', turn.who === 'you' ? 'justify-end' : 'justify-start')}>
            <div className={cx('max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-xs leading-relaxed', turn.who === 'you' ? 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white' : 'bg-slate-100 text-slate-800')}>
              {turn.text || t('chat_error')}
            </div>
          </div>
        ))}
        {studio.busy && <div className="text-[11px] text-slate-400">{t('chat_thinking')}</div>}
        <div ref={end} />
      </div>
      <form
        className="flex gap-1.5 border-t border-slate-200 p-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(text);
        }}
      >
        <input value={text} maxLength={500} onChange={(e) => setText(e.target.value)} placeholder={t('chat_placeholder')} aria-label={t('chat_placeholder')} className={cx(inputClass, 'min-w-0 flex-1')} />
        <Btn tone="accent" disabled={studio.busy || !text.trim()} aria-label={t('send')}>
          <Send size={13} />
        </Btn>
      </form>
    </div>
  );
};
