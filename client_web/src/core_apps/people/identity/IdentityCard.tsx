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

const PALETTES = [
  'bg-gradient-to-br from-primary-container to-tertiary-container text-on-primary-container',
  'bg-gradient-to-br from-tertiary-container to-secondary-container text-on-tertiary-container',
  'bg-gradient-to-br from-secondary-container to-primary-container text-on-secondary-container',
  'bg-gradient-to-br from-success-container to-secondary-container text-on-success-container',
];
const SCANNED = 'bg-gradient-to-br from-warning-container to-surface-container-high text-on-warning-container';
const hash = (value: string) => [...value].reduce((acc, char) => (acc * 31 + char.charCodeAt(0)) >>> 0, 7);

export const Portrait: React.FC<{ readonly person: PersonSummary; readonly className?: string; readonly text?: string }> = ({ person, className = '', text = 'text-4xl' }) => {
  const [broken, setBroken] = useState(false);
  const showPhoto = person.quality > 0 && !broken;
  const palette = person.scanned ? SCANNED : PALETTES[hash(person.slug) % PALETTES.length];
  return (
    <span className={`relative flex items-center justify-center overflow-hidden ${palette} ${className}`}>
      {person.scanned ? (
        <ScanFace className="h-1/3 w-1/3" aria-hidden="true" />
      ) : (
        <span className={`font-bold tracking-tight ${text}`} aria-hidden="true">{initials(person.name)}</span>
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
      className="md-state md-lift group flex w-full flex-col overflow-hidden rounded-[1.75rem] border-0 bg-surface-container-low p-0 text-left text-on-surface"
    >
      <span className="relative block">
        <Portrait person={person} className="aspect-[4/5] w-full" text="text-5xl" />
        <span className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-scrim/40 to-transparent" aria-hidden="true" />
        {present && (
          <span className="md-pop absolute right-2.5 top-2.5 flex items-center gap-1.5 rounded-full bg-success-container/95 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-on-success-container shadow-sm backdrop-blur">
            <span className="md-live h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
            {t('present_now')}
          </span>
        )}
        {!person.scanned && role && (
          <span className="absolute bottom-2.5 left-2.5 max-w-[85%] truncate rounded-full bg-surface/85 px-2 py-0.5 text-[10px] font-semibold text-on-surface backdrop-blur">{role}</span>
        )}
      </span>
      <span className="flex min-h-[4.25rem] flex-col justify-center px-3 py-3 text-center">
        <span className="truncate text-base font-bold leading-tight tracking-tight text-on-surface">{person.scanned ? t('unknown_face') : surname}</span>
        {!person.scanned && given && <span className="truncate text-sm text-on-surface-variant">{given}</span>}
      </span>
    </button>
  );
};
