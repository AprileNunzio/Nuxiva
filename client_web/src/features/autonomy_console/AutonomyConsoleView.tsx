import React from 'react';
import { Brain, CheckCircle2, Hammer, HelpCircle, ShieldCheck, Zap } from 'lucide-react';
import {
  AutonomyCognitionSnapshot,
  CompiledShortcutItem,
  EpistemicQuestionItem,
  ForgedToolProofItem,
} from './types';

export interface AutonomyConsoleViewProps {
  snapshot: AutonomyCognitionSnapshot;
  onSelectAnswer: (questionId: string, optionKey: string) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

export const AutonomyConsoleView: React.FC<AutonomyConsoleViewProps> = ({
  snapshot,
  onSelectAnswer,
  t,
}) => {
  const confidencePct = Math.round(snapshot.confidence_bps / 100);

  return (
    <section
      aria-labelledby="autonomy-console-title"
      className="flex w-full flex-col gap-5 rounded-2xl border border-outline-variant/50 bg-surface p-4 text-on-surface shadow-xl sm:p-6"
    >
      <header className="flex flex-col justify-between gap-4 border-b border-outline-variant/40 pb-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <Brain className="h-6 w-6" />
          </div>
          <div>
            <h2
              id="autonomy-console-title"
              className="text-base font-bold tracking-tight text-on-surface sm:text-lg"
            >
              {t('autonomy.console.title')}
            </h2>
            <p className="text-xs text-on-surface-variant sm:text-sm">
              {t(snapshot.goal_key)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start rounded-xl border border-primary/30 bg-primary/10 px-3.5 py-2 sm:self-auto">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-on-surface">
            {t('autonomy.console.confidence_label')}:
          </span>
          <span className="text-sm font-bold text-primary">{confidencePct}%</span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 cq-lg:grid-cols-3">
        <div className="flex flex-col gap-3 rounded-xl border border-outline-variant/40 bg-surface-container p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-on-surface">
            <HelpCircle className="h-4 w-4 text-primary" />
            <span>{t('autonomy.console.questions_section')}</span>
          </div>

          {snapshot.questions.length === 0 ? (
            <p className="text-xs text-on-surface-variant">
              {t('autonomy.console.questions_empty')}
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {snapshot.questions.map((q: EpistemicQuestionItem) => (
                <article
                  key={q.id}
                  className="flex flex-col gap-2.5 rounded-xl border border-outline-variant/30 bg-surface p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-md bg-primary/15 px-2 py-0.5 text-[11px] font-medium text-primary">
                      {t(`autonomy.scope.${q.scope}`)}
                    </span>
                    <span className="text-[11px] text-on-surface-variant">
                      {t('autonomy.console.voi_label')} {Math.round(q.voi_bps / 100)}%
                    </span>
                  </div>
                  <p className="text-xs font-medium text-on-surface sm:text-sm">
                    {t(q.question_key)}
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {q.options_keys.map((optKey: string) => {
                      const active = q.selected_option_key === optKey;
                      return (
                        <button
                          key={optKey}
                          type="button"
                          onClick={() => onSelectAnswer(q.id, optKey)}
                          className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
                            active
                              ? 'bg-primary text-on-primary shadow-sm'
                              : 'border border-outline-variant/50 bg-surface-container-high text-on-surface hover:border-primary/60'
                          }`}
                        >
                          {t(optKey)}
                        </button>
                      );
                    })}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-outline-variant/40 bg-surface-container p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-on-surface">
            <Hammer className="h-4 w-4 text-primary" />
            <span>{t('autonomy.console.forge_section')}</span>
          </div>

          {snapshot.forged_tools.length === 0 ? (
            <p className="text-xs text-on-surface-variant">
              {t('autonomy.console.forge_empty')}
            </p>
          ) : (
            <div className="flex flex-col gap-2.5">
              {snapshot.forged_tools.map((tool: ForgedToolProofItem) => (
                <div
                  key={`${tool.call_name}-v${tool.version}`}
                  className="flex flex-col gap-1.5 rounded-xl border border-outline-variant/30 bg-surface p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-on-surface">
                      {tool.call_name} (v{tool.version})
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                      <CheckCircle2 className="h-3 w-3" />
                      {t(`autonomy.status.${tool.status}`)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-on-surface-variant">
                    <span>
                      {t('autonomy.console.tests_passed')}: {tool.passed_cases}
                    </span>
                    <span>{tool.total_duration_ms} ms</span>
                  </div>
                  <span className="truncate font-mono text-[10px] text-on-surface-variant">
                    {tool.digest}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-outline-variant/40 bg-surface-container p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-on-surface">
            <Zap className="h-4 w-4 text-primary" />
            <span>{t('autonomy.console.shortcuts_section')}</span>
          </div>

          {snapshot.shortcuts.length === 0 ? (
            <p className="text-xs text-on-surface-variant">
              {t('autonomy.console.shortcuts_empty')}
            </p>
          ) : (
            <div className="flex flex-col gap-2.5">
              {snapshot.shortcuts.map((sc: CompiledShortcutItem) => (
                <div
                  key={sc.shortcut_id}
                  className="flex flex-col gap-1 rounded-xl border border-outline-variant/30 bg-surface p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-primary">
                      {sc.shortcut_id}
                    </span>
                    <span className="rounded-md bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
                      {t('autonomy.console.zero_token_badge')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-on-surface-variant">
                    <span>{sc.action_target}</span>
                    <span>
                      {t('autonomy.console.hits_label')}: {sc.consolidated_hits}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
