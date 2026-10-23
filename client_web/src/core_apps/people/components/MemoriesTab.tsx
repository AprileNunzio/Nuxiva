import React, { FormEvent, useEffect, useState } from 'react';
import { Brain, Plus, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Memory, addMemory, deleteMemory, fetchMemories } from '../data/peopleApi';
import { chipClass, fieldClass, relative, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const MemoriesTab: React.FC<Props> = ({ slug, busy, run }) => {
  const { t, lang } = usePeopleI18n();
  const [memories, setMemories] = useState<readonly Memory[] | null>(null);
  const [text, setText] = useState('');
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchMemories(slug, controller.signal)
      .then(setMemories)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_memories_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (text.trim().length >= 3 && (await run('memory', () => addMemory(slug, text.trim()), 'people_memory_failed'))) {
      setText('');
      setTick((v) => v + 1);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-slate-600">{t('memories_hint')}</p>
      <form onSubmit={submit} className="flex gap-2">
        <input maxLength={200} value={text} onChange={(event) => setText(event.target.value)} placeholder={t('memory_placeholder')} aria-label={t('memory_placeholder')} className={`${fieldClass} min-w-0 flex-1`} />
        <button type="submit" disabled={busy !== null || text.trim().length < 3} className={`${chipClass} border-blue-300 bg-blue-50 px-3 text-blue-900`}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t('add_memory')}
        </button>
      </form>
      {memories === null ? null : memories.length === 0 ? (
        <p className="text-sm text-slate-500">{t('memories_empty')}</p>
      ) : (
        <ul className="grid gap-2 xl:grid-cols-2 4xl:grid-cols-3">
          {memories.map((m) => (
            <li key={m.id} className="flex items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
              <Brain className="mt-0.5 h-4 w-4 shrink-0 text-indigo-700" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-slate-900">{m.text}</p>
                <p className="text-[10px] text-slate-500">{[relative(m.created, lang), t('recalled', { count: m.hits })].join(' · ')}</p>
              </div>
              <button
                type="button"
                disabled={busy !== null}
                aria-label={t('forget_memory')}
                onClick={() => void run(`memory:${m.id}`, () => deleteMemory(m.id), 'people_memory_failed').then((ok) => ok && setTick((v) => v + 1))}
                className="rounded-lg p-1 text-slate-500 hover:text-rose-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
