import React, { useState } from 'react';
import { Loader2, Users } from 'lucide-react';
import { ExpertChat } from './components/ExpertChat';
import { ExpertProfile } from './components/ExpertProfile';
import { ExpertRoster } from './components/ExpertRoster';
import { LivePanel } from './components/LivePanel';
import { NewExpertDialog } from './components/NewExpertDialog';
import { useExperts } from './hooks/useExperts';
import { glassClass, useExpertsI18n } from './scope';

export const ExpertsSection: React.FC = () => {
  const { t } = useExpertsI18n();
  const handle = useExperts();
  const { overview } = handle;
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  if (!overview) {
    return (
      <div className="flex min-h-[30vh] items-center justify-center gap-2 text-sm text-slate-400" role="status">
        <Loader2 className="h-5 w-5 animate-spin text-cyan-300" aria-hidden="true" />
        {t('loading')}
      </div>
    );
  }

  const expert = overview.experts.find((e) => e.id === selected) ?? overview.experts[0] ?? null;
  const working = overview.experts.filter((e) => e.doing).length;

  return (
    <section aria-labelledby="experts-title" className="flex flex-col gap-4">
      <header className={glassClass}>
        <div className="pointer-events-none absolute -left-24 -top-24 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl" aria-hidden="true" />
        <div className="relative flex flex-wrap items-center gap-4">
          <Users className="h-8 w-8 text-cyan-300" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <h1 id="experts-title" className="font-['Rajdhani'] text-3xl font-bold tracking-wide text-white 3xl:text-5xl">
              {t('title')}
            </h1>
            <p className="mt-1 text-sm text-slate-400">{t('description')}</p>
          </div>
          <dl className="flex w-full gap-2 sm:w-auto">
            <div className="flex-1 rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2 sm:flex-none">
              <dt className="text-[0.625rem] uppercase tracking-[0.14em] text-slate-500">{t('stat_experts')}</dt>
              <dd className="font-mono text-xl text-white">{overview.experts.length}</dd>
            </div>
            <div className="flex-1 rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2 sm:flex-none">
              <dt className="text-[0.625rem] uppercase tracking-[0.14em] text-slate-500">{t('stat_working')}</dt>
              <dd className="font-mono text-xl text-emerald-200">{working}</dd>
            </div>
          </dl>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)] 3xl:grid-cols-[22rem_minmax(0,1fr)]">
        <ExpertRoster experts={overview.experts} selected={expert?.id ?? null} onSelect={setSelected} onCreate={() => setCreating(true)} />
        {expert ? (
          <div className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
            <div className="flex min-w-0 flex-col gap-4">
              <ExpertProfile key={`p-${expert.id}`} expert={expert} skills={overview.skills} tools={overview.tools} handle={handle} onDeleted={() => setSelected(null)} />
              <LivePanel key={`l-${expert.id}`} expert={expert} />
            </div>
            <ExpertChat key={`c-${expert.id}`} expert={expert} skills={overview.skills} onChange={handle.refresh} />
          </div>
        ) : (
          <div className={`${glassClass} flex flex-col items-center justify-center gap-3 text-center`}>
            <p className="max-w-md text-sm text-slate-400">{t('empty')}</p>
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-sm font-bold text-slate-950 hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
            >
              {t('new_expert')}
            </button>
          </div>
        )}
      </div>

      {creating && (
        <NewExpertDialog
          templates={overview.templates}
          handle={handle}
          onClose={(id) => {
            setCreating(false);
            if (id) {
              setSelected(id);
            }
          }}
        />
      )}
    </section>
  );
};
