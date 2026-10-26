import React, { useEffect, useState } from 'react';
import { Check, Sparkles, Undo2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Learned, fetchLearned, learnedFeedback } from '../data/peopleApi';
import { chipClass, relative, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const LearnedPanel: React.FC<Props> = ({ slug, busy, run }) => {
  const { t, lang } = usePeopleI18n();
  const [rows, setRows] = useState<readonly Learned[] | null>(null);
  const [enabled, setEnabled] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchLearned(slug, controller.signal)
      .then((data) => {
        setRows(data.learned);
        setEnabled(data.enabled);
      })
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_memories_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  const judge = async (row: Learned, verdict: 'ok' | 'wrong') => {
    if (await run(`learned:${row.id}`, () => learnedFeedback(slug, row.id, verdict), 'people_memory_failed')) {
      setTick((v) => v + 1);
    }
  };

  return (
    <section className="flex flex-col gap-2 rounded-xl border border-blue-200 bg-blue-50 p-3" aria-labelledby="learned-title">
      <h3 id="learned-title" className="flex items-center gap-2 text-sm font-semibold text-blue-900">
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {t('learned_title')}
      </h3>
      <p className="text-xs text-slate-700">{t(enabled ? 'learned_hint' : 'learned_off')}</p>
      {rows !== null && rows.length === 0 && <p className="text-sm text-slate-500">{t('learned_empty')}</p>}
      <ul className="grid gap-2 xl:grid-cols-2">
        {(rows ?? []).slice(0, 20).map((row) => (
          <li key={row.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-900">
                <span className="text-slate-600">{t(`learned_f_${row.field}`)}:</span> {row.value}
              </p>
              <p className="truncate text-[10px] text-slate-500">{[relative(row.at, lang), `«${row.evidence}»`, t(`learned_s_${row.status}`)].join(' · ')}</p>
            </div>
            {row.status === 'auto' && (
              <>
                <button type="button" disabled={busy !== null} onClick={() => void judge(row, 'ok')} className={`${chipClass} border-emerald-300 px-2 text-emerald-800`}>
                  <Check className="h-3 w-3" aria-hidden="true" />
                  {t('feedback_right')}
                </button>
                <button type="button" disabled={busy !== null} onClick={() => void judge(row, 'wrong')} className={`${chipClass} border-rose-300 px-2 text-rose-800`}>
                  <Undo2 className="h-3 w-3" aria-hidden="true" />
                  {t('learned_undo')}
                </button>
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
};
