import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, Lock, Save } from 'lucide-react';
import { PersonSummary, Profile, SchemaField, updatePerson } from '../data/peopleApi';
import { localLabel, primaryClass, usePeopleI18n } from '../scope';
import { FieldInput } from './FieldInput';

interface SectionFormProps {
  readonly slug: string;
  readonly title: string;
  readonly isPrivate: boolean;
  readonly fields: readonly SchemaField[];
  readonly profile: Profile;
  readonly people: readonly PersonSummary[];
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const SectionForm: React.FC<SectionFormProps> = ({ slug, title, isPrivate, fields, profile, people, busy, run }) => {
  const { t, lang } = usePeopleI18n();
  const baseline = useMemo(() => Object.fromEntries(fields.map((f) => [f.key, profile[f.key]])), [fields, profile]);
  const [draft, setDraft] = useState<Record<string, unknown>>(baseline);
  useEffect(() => setDraft(baseline), [baseline]);
  const changed = Object.fromEntries(fields.filter((f) => JSON.stringify(draft[f.key] ?? null) !== JSON.stringify(baseline[f.key] ?? null)).map((f) => [f.key, draft[f.key]]));
  const dirty = Object.keys(changed).length > 0;
  const key = `section:${title}`;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (dirty) {
          void run(key, () => updatePerson(slug, changed), 'people_update_failed');
        }
      }}
      className="flex flex-col gap-3"
    >
      <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        {title}
        {isPrivate && (
          <span className="flex items-center gap-1 rounded-full border border-emerald-400/40 px-2 py-0.5 text-[10px] normal-case tracking-normal text-emerald-200">
            <Lock className="h-3 w-3" aria-hidden="true" />
            {t('encrypted')}
          </span>
        )}
      </h3>
      <div className="grid gap-3 md:grid-cols-2 3xl:grid-cols-3">
        {fields.map((field) => {
          const id = `person-${slug}-${field.key}`;
          const label = localLabel(t, lang, `field_${field.key}`, field.label);
          const wide = field.type === 'list' || field.type === 'textarea' || field.type === 'tags';
          return (
            <div key={field.key} className={`flex flex-col gap-1.5 ${wide ? 'md:col-span-2 3xl:col-span-3' : ''} ${field.type === 'bool' ? 'flex-row items-center justify-between rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2' : ''}`}>
              <label htmlFor={id} className="text-xs text-slate-400">
                {label}
              </label>
              <FieldInput id={id} field={field} value={draft[field.key]} people={people} onChange={(value) => setDraft((current) => ({ ...current, [field.key]: value }))} />
            </div>
          );
        })}
      </div>
      <button type="submit" disabled={!dirty || busy !== null} className={`${primaryClass} self-start`}>
        {busy === key ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
        {t('save')}
      </button>
    </form>
  );
};
