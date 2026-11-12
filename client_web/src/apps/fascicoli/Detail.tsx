import React from 'react';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { Empty, Loading, Panel, Unreachable } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { KNOWN_PROBLEMS, segments, useFascicoliI18n } from './scope';
import type { FascicoloDetail } from './types';

const order = (name: string): string => (name.startsWith('passi/') ? `5${name}` : name);

export const Detail: React.FC<{ readonly rel: string }> = ({ rel }) => {
  const { t } = useFascicoliI18n();
  const resource = useResource<FascicoloDetail>(`/api/fascicoli/${segments(rel)}`);
  const data = resource.dataUrl === `/api/fascicoli/${segments(rel)}` ? resource.data : null;
  if (resource.error && !data) {
    return <Unreachable label={t('unreachable')} />;
  }
  if (!data) {
    return <Loading label={t('loading')} />;
  }
  const names = Object.keys(data.files).sort((a, b) => order(a).localeCompare(order(b)));
  const Icon = data.report.ok ? ShieldCheck : ShieldAlert;
  return (
    <Panel title={t('detail_title')}>
      <p className="mb-3 flex items-center gap-2 text-sm" role="status">
        <Icon className="h-4 w-4" aria-hidden="true" />
        {t(data.report.ok ? 'integrity_ok' : 'integrity_broken')}
      </p>
      {data.report.problems.length > 0 && (
        <ul className="mb-3 list-disc pl-5 text-xs text-on-surface-variant">
          {data.report.problems.map((problem) => (
            <li key={`${problem.at}:${problem.code}`}>
              {problem.at || t('ledger')}: {KNOWN_PROBLEMS.has(problem.code) ? t(`problem_${problem.code}`) : t('problem_unknown')}
            </li>
          ))}
        </ul>
      )}
      {names.length === 0 ? (
        <Empty>{t('no_files')}</Empty>
      ) : (
        <div className="flex flex-col gap-2">
          {names.map((name) => {
            const doc = data.files[name];
            return (
              <details key={name} className="rounded-2xl border border-outline px-3 py-2" open={name.endsWith('99-esito.md') || name.endsWith('90-verifica.md')}>
                <summary className="cursor-pointer text-sm font-semibold">
                  {doc?.title || name} <span className="font-normal text-on-surface-variant">· {name}</span>
                </summary>
                {doc?.sections.map((section) => (
                  <section key={section.anchor} className="mt-2">
                    <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-on-surface-variant">{section.heading}</h3>
                    <pre className="mt-1 whitespace-pre-wrap break-words text-sm">{section.body}</pre>
                  </section>
                ))}
              </details>
            );
          })}
        </div>
      )}
    </Panel>
  );
};
