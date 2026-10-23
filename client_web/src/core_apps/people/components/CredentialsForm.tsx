import React, { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { saveSettings } from '../../shared/featureApi';
import { chipClass, fieldClass, usePeopleI18n } from '../scope';

export interface CredentialField {
  readonly key: string;
  readonly label: string;
  readonly secret: boolean;
}

interface Props {
  readonly feature: string;
  readonly fields: readonly CredentialField[];
  readonly hint: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const CredentialsForm: React.FC<Props> = ({ feature, fields, hint, busy, run }) => {
  const { t } = usePeopleI18n();
  const [draft, setDraft] = useState<Readonly<Record<string, string>>>({});
  const ready = fields.every((field) => (draft[field.key] ?? '').trim().length >= 4);

  const save = async () => {
    const values = Object.fromEntries(fields.map((field) => [field.key, (draft[field.key] ?? '').trim()]));
    if (await run(`cred:${feature}`, () => saveSettings(feature, values), 'people_connectors_failed')) {
      setDraft({});
    }
  };

  return (
    <form
      className="flex flex-col gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <p className="text-sm text-amber-900">{hint}</p>
      {fields.map((field) => (
        <label key={field.key} className="flex flex-col gap-1 text-xs font-semibold text-slate-700">
          {field.label}
          <input
            type={field.secret ? 'password' : 'text'}
            autoComplete="off"
            spellCheck={false}
            maxLength={500}
            value={draft[field.key] ?? ''}
            onChange={(event) => setDraft((state) => ({ ...state, [field.key]: event.target.value }))}
            className={fieldClass}
          />
        </label>
      ))}
      <button type="submit" disabled={busy !== null || !ready} className={`${chipClass} self-start border-blue-300 bg-white px-3 text-blue-900`}>
        <KeyRound className="h-4 w-4" aria-hidden="true" />
        {t('cred_save')}
      </button>
    </form>
  );
};
