import React from 'react';
import { Send, Unlink } from 'lucide-react';
import { TelegramState, telegramChat, telegramPair, telegramUnlink } from '../data/connectorsApi';
import { chipClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly state: TelegramState;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

const cardClass = 'flex flex-col gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 p-4';

export const TelegramCard: React.FC<Props> = ({ slug, state, busy, run }) => {
  const { t } = usePeopleI18n();
  return (
    <section className={cardClass} aria-labelledby="connector-telegram">
      <header className="flex items-center gap-2">
        <Send className="h-4 w-4 text-sky-300" aria-hidden="true" />
        <h3 id="connector-telegram" className="font-semibold text-white">
          Telegram
        </h3>
        <span className={`ml-auto rounded-full border px-2 py-0.5 text-xs ${state.linked ? 'border-emerald-400/40 text-emerald-200' : 'border-slate-700 text-slate-400'}`}>
          {t(state.linked ? 'connector_linked' : 'connector_not_linked')}
        </span>
      </header>
      {!state.available && <p className="text-sm text-amber-200">{t('tg_not_configured')}</p>}
      {state.chats.map((chat) => (
        <div key={chat.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800/80 px-3 py-2 text-sm">
          <span className="min-w-0 flex-1 truncate text-slate-100">{[chat.name, chat.username && `@${chat.username}`].filter(Boolean).join(' · ')}</span>
          <label className="flex items-center gap-1.5 text-xs text-slate-300">
            <input type="checkbox" checked={chat.notify} disabled={busy !== null} onChange={(event) => void run(`tg:${chat.id}`, () => telegramChat(slug, chat.id, { notify: event.target.checked }), 'people_connectors_failed')} />
            {t('tg_notify')}
          </label>
          <label className="flex items-center gap-1.5 text-xs text-slate-300">
            <input type="checkbox" checked={chat.voice} disabled={busy !== null} onChange={(event) => void run(`tg:${chat.id}`, () => telegramChat(slug, chat.id, { voice: event.target.checked }), 'people_connectors_failed')} />
            {t('tg_voice')}
          </label>
        </div>
      ))}
      {state.pairCode && (
        <p className="rounded-lg border border-cyan-400/40 bg-cyan-400/5 p-3 text-sm text-cyan-50" role="status">
          {t('tg_code_hint', { code: state.pairCode, bot: state.bot ? `@${state.bot}` : t('tg_bot'), seconds: state.pairExpiresIn })}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy !== null || !state.available} onClick={() => void run('tg-pair', () => telegramPair(slug), 'people_connectors_failed')} className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 px-3 text-cyan-100`}>
          <Send className="h-4 w-4" aria-hidden="true" />
          {t(state.linked ? 'tg_add_chat' : 'tg_generate')}
        </button>
        {state.linked && (
          <button type="button" disabled={busy !== null} onClick={() => void run('tg-unlink', () => telegramUnlink(slug), 'people_connectors_failed')} className={`${chipClass} border-rose-400/40 px-3 text-rose-200`}>
            <Unlink className="h-4 w-4" aria-hidden="true" />
            {t('connector_unlink')}
          </button>
        )}
      </div>
    </section>
  );
};
