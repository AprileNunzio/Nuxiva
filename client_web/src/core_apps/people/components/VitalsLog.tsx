import React, { useEffect, useState } from 'react';
import { ScrollText } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { VitalLogEntry, fetchVitalsLog } from '../data/connectorsApi';
import { usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly tick: number;
}

const TONE: Record<VitalLogEntry['level'], string> = { info: 'text-slate-700', warn: 'text-amber-800', error: 'text-rose-800' };
const HINTED: readonly string[] = ['no_profiles', 'connect_failed', 'scan_failed', 'cloud_error', 'search_no_nodes', 'rejected_values'];

export const VitalsLog: React.FC<Props> = ({ slug, tick }) => {
  const { t, lang } = usePeopleI18n();
  const [rows, setRows] = useState<readonly VitalLogEntry[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    fetchVitalsLog(slug, controller.signal)
      .then(setRows)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_connectors_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  return (
    <details className="rounded-lg border border-slate-200 bg-white p-3 text-xs">
      <summary className="flex cursor-pointer items-center gap-2 font-semibold text-slate-800">
        <ScrollText className="h-4 w-4" aria-hidden="true" />
        {t('vitals_log')}
      </summary>
      {rows.length === 0 ? (
        <p className="mt-2 text-slate-600">{t('vitals_log_empty')}</p>
      ) : (
        <ul className="mt-2 flex max-h-56 flex-col gap-1 overflow-y-auto">
          {rows.map((row, i) => (
            <li key={`${row.at}-${i}`} className={TONE[row.level]}>
              <span className="mr-2 font-mono text-slate-500">{new Date(row.at * 1000).toLocaleTimeString(lang)}</span>
              {t(`vitals_log_${row.code}`, row.params)}
              {HINTED.includes(row.code) && <span className="block pl-14 text-slate-600">{t(`vitals_hint_${row.code}`)}</span>}
            </li>
          ))}
        </ul>
      )}
    </details>
  );
};
