import React, { useState } from 'react';
import { Minus, Plus, X } from 'lucide-react';
import { PersonSummary, SchemaField } from '../data/peopleApi';
import { chipClass, fieldClass, localLabel, usePeopleI18n } from '../scope';

type Value = unknown;
type Row = Readonly<Record<string, unknown>>;

interface FieldInputProps {
  readonly field: SchemaField;
  readonly value: Value;
  readonly people: readonly PersonSummary[];
  readonly onChange: (value: Value) => void;
  readonly id: string;
}

const text = (value: Value): string => (typeof value === 'string' || typeof value === 'number' ? String(value) : '');

const TagsInput: React.FC<{ readonly id: string; readonly value: Value; readonly onChange: (value: string[]) => void }> = ({ id, value, onChange }) => {
  const { t } = usePeopleI18n();
  const [draft, setDraft] = useState('');
  const tags = Array.isArray(value) ? value.map((v) => String(v)) : [];
  const add = () => {
    const parts = draft.split(',').map((s) => s.trim()).filter(Boolean);
    if (parts.length) {
      onChange(Array.from(new Set([...tags, ...parts])).slice(0, 50));
      setDraft('');
    }
  };
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-2 py-1.5">
      {tags.map((tag) => (
        <span key={tag} className="flex items-center gap-1 rounded-full border border-blue-300 bg-blue-50 px-2 py-0.5 text-xs text-blue-900">
          {tag}
          <button type="button" aria-label={t('remove_tag', { tag })} onClick={() => onChange(tags.filter((x) => x !== tag))} className="text-blue-700 hover:text-slate-900">
            <X className="h-3 w-3" aria-hidden="true" />
          </button>
        </span>
      ))}
      <input
        id={id}
        value={draft}
        maxLength={80}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ',') {
            event.preventDefault();
            add();
          }
        }}
        onBlur={add}
        placeholder={t('add_tag')}
        className="min-w-[8rem] flex-1 bg-transparent px-1 py-0.5 text-sm text-slate-900 outline-none"
      />
    </div>
  );
};

export const FieldInput: React.FC<FieldInputProps> = ({ field, value, people, onChange, id }) => {
  const { t, lang } = usePeopleI18n();
  switch (field.type) {
    case 'bool':
      return <input id={id} type="checkbox" role="switch" checked={value === true} onChange={(event) => onChange(event.target.checked)} className="h-5 w-9 accent-cyan-400" />;
    case 'select':
      return (
        <select id={id} value={text(value)} onChange={(event) => onChange(event.target.value)} className={fieldClass}>
          {!field.options.includes(text(value)) && <option value={text(value)}>{text(value) || '—'}</option>}
          {field.options.map((option) => (
            <option key={option} value={option}>
              {field.labels[option] ?? (option || '—')}
            </option>
          ))}
        </select>
      );
    case 'person':
      return (
        <select id={id} value={text(value)} onChange={(event) => onChange(event.target.value)} className={fieldClass}>
          <option value="">—</option>
          {people.filter((p) => !p.scanned).map((p) => (
            <option key={p.slug} value={p.slug}>
              {p.name}
            </option>
          ))}
        </select>
      );
    case 'textarea':
      return <textarea id={id} rows={4} maxLength={4000} value={text(value)} placeholder={field.placeholder} onChange={(event) => onChange(event.target.value)} className={`${fieldClass} resize-y`} />;
    case 'tags':
      return <TagsInput id={id} value={value} onChange={onChange} />;
    case 'list': {
      const rows: Row[] = Array.isArray(value) ? value.filter((r): r is Row => typeof r === 'object' && r !== null) : [];
      const set = (index: number, key: string, v: Value) => onChange(rows.map((row, i) => (i === index ? { ...row, [key]: v } : row)));
      return (
        <div className="flex flex-col gap-2">
          {rows.map((row, index) => (
            <div key={index} className="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2 sm:grid-cols-2 3xl:grid-cols-3">
              {field.fields.map((sub) => (
                <label key={sub.key} className="flex flex-col gap-1 text-[11px] text-slate-600">
                  {localLabel(t, lang, `field_${sub.key}`, sub.label)}
                  <FieldInput field={sub} value={row[sub.key]} people={people} onChange={(v) => set(index, sub.key, v)} id={`${id}-${index}-${sub.key}`} />
                </label>
              ))}
              <button type="button" onClick={() => onChange(rows.filter((_, i) => i !== index))} className={`${chipClass} self-end justify-self-start border-slate-300 text-slate-600 hover:text-rose-700`}>
                <Minus className="h-3.5 w-3.5" aria-hidden="true" />
                {t('remove_row')}
              </button>
            </div>
          ))}
          {rows.length < 100 && (
            <button type="button" onClick={() => onChange([...rows, {}])} className={`${chipClass} self-start border-slate-300 text-slate-700`}>
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              {t('add_row')}
            </button>
          )}
        </div>
      );
    }
    default: {
      const type = { date: 'date', number: 'number', tel: 'tel', email: 'email', url: 'url' }[field.type as string] ?? 'text';
      return <input id={id} type={type} maxLength={400} value={text(value)} placeholder={field.placeholder} onChange={(event) => onChange(type === 'number' && event.target.value !== '' ? Number(event.target.value) : event.target.value)} className={fieldClass} />;
    }
  }
};
