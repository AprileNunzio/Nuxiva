import { adminPath } from '../../../shared/http/basePath';
import { PersonSummary } from '../data/peopleApi';

export interface NameParts {
  readonly surname: string;
  readonly given: string;
}

export function nameParts(p: PersonSummary): NameParts {
  const first = p.firstName.trim();
  const last = p.lastName.trim();
  if (first || last) {
    return last ? { surname: last, given: first } : { surname: first, given: '' };
  }
  const words = p.name.trim().split(/\s+/);
  return words.length > 1 ? { surname: words.slice(1).join(' '), given: words[0] } : { surname: p.name, given: '' };
}

export const fullName = (p: PersonSummary): string => {
  const n = nameParts(p);
  return [n.surname, n.given].filter(Boolean).join(' ');
};

export const sortKey = (p: PersonSummary): string => {
  const n = nameParts(p);
  return `${n.surname} ${n.given}`.toLocaleLowerCase();
};

export const facePhoto = (slug: string): string => adminPath(`/api/vision/people/${encodeURIComponent(slug)}/photo.jpg`);
