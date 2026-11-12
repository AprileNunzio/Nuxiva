import React, { useState } from 'react';
import { CalendarDays, ExternalLink, Link2Off } from 'lucide-react';
import { Btn, Field, Pill, Row, inputClass } from '../../shared/kit';
import { authUrl, cancelLink, finishLink, preview, unlink } from '../api';
import { GooglePerson, GooglePreview, GoogleService } from '../types';

interface PersonCardProps {
  readonly person: GooglePerson;
  readonly services: readonly GoogleService[];
  readonly defaults: readonly string[];
  readonly waiting: boolean;
  readonly busy: boolean;
  readonly canLink: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

const labelOf = (item: Readonly<Record<string, unknown>>): string => {
  for (const key of ['summary', 'title', 'subject', 'text', 'name']) {
    const value = item[key];
    if (typeof value === 'string' && value) {
      return value.slice(0, 120);
    }
  }
  return '—';
};

export const PersonCard: React.FC<PersonCardProps> = ({ person, services, defaults, waiting, busy, canLink, t, run }) => {
  const [chosen, setChosen] = useState<string[]>([...defaults]);
  const [link, setLink] = useState('');
  const [pasted, setPasted] = useState('');
  const [view, setView] = useState<GooglePreview | null>(null);

  const start = async () => {
    const out = await run(() => authUrl(person.slug, chosen), 'google_url_failed');
    if (out) {
      setLink(out.url);
    }
  };

  const finish = async () => {
    if ((await run(() => finishLink(person.slug, pasted.trim()), 'google_finish_failed')) !== null) {
      setPasted('');
      setLink('');
    }
  };

  const look = async () => setView(await run(() => preview(person.slug), 'google_preview_failed'));

  return (
    <Row
      actions={
        person.linked ? (
          <>
            <Btn tone="slate" busy={busy} onClick={() => void look()}>
              <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
              {t('preview')}
            </Btn>
            <Btn tone="rose" busy={busy} onClick={() => void run(() => unlink(person.slug), 'google_unlink_failed')}>
              <Link2Off className="h-3.5 w-3.5" aria-hidden="true" />
              {t('unlink')}
            </Btn>
          </>
        ) : undefined
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <b>{person.name}</b>
        <Pill tone={person.linked ? 'emerald' : 'slate'}>{person.linked ? person.email || t('linked') : t('not_linked')}</Pill>
        {person.unread ? <Pill tone="amber">{t('unread', { n: person.unread })}</Pill> : null}
      </div>
      {person.granted.length ? <p className="mt-1 text-[11px] text-slate-500">{person.granted.join(' · ')}</p> : null}
      {view ? (
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {Object.entries(view).map(([group, items]) => (
            <div key={group} className="rounded-lg border border-slate-200 bg-white p-2">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{t(`group_${group}`)} ({items.length})</div>
              <ul className="mt-1 space-y-0.5 text-xs text-slate-700">
                {items.slice(0, 5).map((item, index) => (
                  <li key={`${group}-${index}`} className="truncate">{labelOf(item)}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
      {!person.linked && canLink ? (
        <div className="mt-3 flex flex-col gap-3">
          <fieldset className="flex flex-wrap gap-3">
            <legend className="sr-only">{t('services')}</legend>
            {services.map((service) => (
              <label key={service.id} className="flex items-center gap-1.5 text-xs text-slate-700">
                <input
                  type="checkbox"
                  checked={chosen.includes(service.id)}
                  onChange={(event) => setChosen((current) => (event.target.checked ? [...current, service.id] : current.filter((item) => item !== service.id)))}
                />
                {service.icon} {service.name}
              </label>
            ))}
          </fieldset>
          <div className="flex flex-wrap gap-2">
            <Btn busy={busy} disabled={chosen.length === 0} onClick={() => void start()}>
              {t('get_link')}
            </Btn>
            {waiting ? (
              <Btn tone="slate" busy={busy} onClick={() => void run(() => cancelLink(person.slug), 'google_cancel_failed')}>
                {t('cancel')}
              </Btn>
            ) : null}
          </div>
          {link ? (
            <a href={link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-cyan-700 underline">
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              {t('open_google')}
            </a>
          ) : null}
          {waiting || link ? (
            <Field label={t('paste_label')}>
              <div className="flex gap-2">
                <input className={inputClass} value={pasted} onChange={(event) => setPasted(event.target.value)} placeholder="http://127.0.0.1:8889/?code=…" />
                <Btn tone="emerald" busy={busy} disabled={!pasted.trim()} onClick={() => void finish()}>
                  {t('finish')}
                </Btn>
              </div>
            </Field>
          ) : null}
        </div>
      ) : null}
    </Row>
  );
};
