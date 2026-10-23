import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Skill } from '../data/expertsApi';
import { useExpertsI18n } from '../scope';

export const SkillCard: React.FC<{ readonly skill: Skill; readonly color: string }> = ({ skill, color }) => {
  const { t } = useExpertsI18n();
  const [open, setOpen] = useState(false);
  const panel = `skill-${skill.id}`;
  return (
    <li className="rounded-xl border border-indigo-300 bg-gradient-to-br from-indigo-50 to-white p-3">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls={panel} className="flex w-full items-start gap-2 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300">
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-slate-950">{skill.name}</span>
          <span className="block text-xs text-slate-600">{skill.purpose}</span>
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-600 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
      <p className="mt-2 flex flex-wrap gap-1">
        {skill.tools.map((name) => (
          <span key={name} className="rounded-md border border-cyan-300 px-1.5 py-0.5 font-mono text-[0.625rem] text-cyan-900">
            {name}
          </span>
        ))}
      </p>
      {open && (
        <div id={panel} className="mt-3 grid gap-2 text-xs">
          <div>
            <span className="block text-[0.625rem] uppercase tracking-[0.16em] text-slate-500">{t('skill_procedure')}</span>
            <ol className="mt-1 grid list-decimal gap-0.5 pl-4 text-slate-800">
              {skill.procedure.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
          <div>
            <span className="block text-[0.625rem] uppercase tracking-[0.16em] text-slate-500">{t('skill_rules')}</span>
            <ul className="mt-1 grid list-disc gap-0.5 pl-4 text-amber-900">
              {skill.rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </li>
  );
};
