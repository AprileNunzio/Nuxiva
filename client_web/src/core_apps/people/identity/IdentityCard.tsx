import React, { useState } from 'react';
import { ScanFace } from 'lucide-react';
import { PersonSummary } from '../data/peopleApi';
import { initials, usePeopleI18n } from '../scope';
import { facePhoto, nameParts } from './names';

interface Props {
  readonly person: PersonSummary;
  readonly role: string;
  readonly present: boolean;
  readonly onOpen: (slug: string) => void;
}

export const Portrait: React.FC<{ readonly person: PersonSummary; readonly className?: string; readonly text?: string }> = ({ person, className = '', text = 'text-4xl' }) => {
  const [broken, setBroken] = useState(false);
  const showPhoto = person.quality > 0 && !broken;
  return (
    <span className={`relative flex items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 via-slate-200 to-blue-100 ${className}`}>
      {person.scanned ? (
        <ScanFace className="h-1/3 w-1/3 text-amber-600" aria-hidden="true" />
      ) : (
        <span className={`font-['Rajdhani'] font-bold tracking-wide text-blue-900/70 ${text}`} aria-hidden="true">{initials(person.name)}</span>
      )}
      {showPhoto && <img src={facePhoto(person.slug)} alt="" loading="lazy" decoding="async" className="absolute inset-0 h-full w-full object-cover" onError={() => setBroken(true)} />}
    </span>
  );
};

export const IdentityCard: React.FC<Props> = ({ person, role, present, onOpen }) => {
  const { t } = usePeopleI18n();
  const { surname, given } = nameParts(person);
  return (
    <button
      type="button"
      onClick={() => onOpen(person.slug)}
      className="group flex w-full flex-col overflow-hidden rounded-3xl bg-white text-left shadow-sm ring-1 ring-slate-200 transition duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:ring-blue-300 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-400 motion-reduce:transition-none motion-reduce:hover:translate-y-0"
    >
      <span className="relative block">
        <Portrait person={person} className="aspect-[4/5] w-full" text="text-5xl" />
        <span className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-slate-900/45 to-transparent" aria-hidden="true" />
        {present && (
          <span className="absolute right-2.5 top-2.5 flex items-center gap-1 rounded-full bg-white/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-700 shadow-sm backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
            {t('present_now')}
          </span>
        )}
        {!person.scanned && role && (
          <span className="absolute bottom-2.5 left-2.5 max-w-[85%] truncate rounded-full bg-white/85 px-2 py-0.5 text-[10px] font-semibold text-slate-700 backdrop-blur">{role}</span>
        )}
      </span>
      <span className="flex min-h-[4.25rem] flex-col justify-center px-3 py-3 text-center">
        <span className="truncate font-['Rajdhani'] text-lg font-bold uppercase leading-tight tracking-wide text-slate-900">{person.scanned ? t('unknown_face') : surname}</span>
        {!person.scanned && given && <span className="truncate text-sm text-slate-600">{given}</span>}
      </span>
    </button>
  );
};
