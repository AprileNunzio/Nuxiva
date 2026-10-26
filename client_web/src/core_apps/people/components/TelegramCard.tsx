import React from 'react';
import { Send, Unlink } from 'lucide-react';
import { TelegramState, telegramChat, telegramPair, telegramUnlink } from '../data/connectorsApi';
import { chipClass, usePeopleI18n } from '../scope';
import { SetupLink } from './SetupLink';

interface Props {
  readonly slug: string;
  readonly state: TelegramState;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

const cardClass = 'flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4';

export const TelegramCard: React.FC<Props> = ({ slug, state, busy, run }) => {
  const { t } = usePeopleI18n();
  return (
    <section className={cardClass} aria-labelledby="connector-telegram">
      <header className="flex items-center gap-2">
        <Send className="h-4 w-4 text-sky-700" aria-hidden="true" />
        <h3 id="connector-telegram" className="font-semibold text-slate-900">
          Telegram
        </h3>
        <span className={`ml-auto rounded-full border px-2 py-0.5 text-xs ${state.linked ? 'border-emerald-300 text-emerald-800' : 'border-slate-300 text-slate-600'}`}>
          {t(state.linked ? 'connector_linked' : 'connector_not_linked')}
        </span>
      </header>
      {!state.available && <SetupLink feature="telegram" hint={t('tg_not_configured')} />}
      {state.chats.map((chat) => (
        <div key={chat.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm">
          <span className="min-w-0 flex-1 truncate text-slate-900">{[chat.name, chat.username && `@${chat.username}`].filter(Boolean).join(' · ')}</span>
          <label className="flex items-center gap-1.5 text-xs text-slate-700">
            <input type="checkbox" checked={chat.notify} disabled={busy !== null} onChange={(event) => void run(`tg:${chat.id}`, () => telegramChat(slug, chat.id, { notify: event.target.checked }), 'people_connectors_failed')} />
            {t('tg_notify')}
          </label>
          <label className="flex items-center gap-1.5 text-xs text-slate-700">
            <input type="checkbox" checked={chat.voice} disabled={busy !== null} onChange={(event) => void run(`tg:${chat.id}`, () => telegramChat(slug, chat.id, { voice: event.target.checked }), 'people_connectors_failed')} />
            {t('tg_voice')}
          </label>
        </div>
      ))}
      {state.pairCode && (
        <p className="rounded-lg border border-blue-300 bg-blue-50 p-3 text-sm text-blue-900" role="status">
          {t('tg_code_hint', { code: state.pairCode, bot: state.bot ? `@${state.bot}` : t('tg_bot'), seconds: state.pairExpiresIn })}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy !== null || !state.available} onClick={() => void run('tg-pair', () => telegramPair(slug), 'people_connectors_failed')} className={`${chipClass} border-blue-300 bg-blue-50 px-3 text-blue-900`}>
          <Send className="h-4 w-4" aria-hidden="true" />
          {t(state.linked ? 'tg_add_chat' : 'tg_generate')}
        </button>
        {state.linked && (
          <button type="button" disabled={busy !== null} onClick={() => void run('tg-unlink', () => telegramUnlink(slug), 'people_connectors_failed')} className={`${chipClass} border-rose-300 px-3 text-rose-800`}>
            <Unlink className="h-4 w-4" aria-hidden="true" />
            {t('connector_unlink')}
          </button>
        )}
      </div>
      <details className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800" open={!state.available}>
        <summary className="cursor-pointer font-semibold">{t('tg_change_title')}</summary>
        <div className="mt-2 flex flex-col gap-2">
          {state.bot && <p className="text-xs text-slate-600">{t('tg_current_bot', { bot: `@${state.bot}` })}</p>}
          <ol className="list-decimal space-y-1 pl-5 text-xs text-slate-700">
            {[1, 2, 3, 4].map((n) => (
              <li key={n}>{t(`tg_step_${n}`)}</li>
            ))}
          </ol>
          <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className={`${chipClass} self-start border-sky-300 bg-sky-50 px-3 py-2 text-sky-900`}>
            {t('tg_open_botfather')}
          </a>
          <SetupLink feature="telegram" hint={t('tg_change_hint')} />
        </div>
      </details>
    </section>
  );
};
