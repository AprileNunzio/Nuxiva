import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, Loader2, Search, User, UserCheck, X } from 'lucide-react';
import { PersonSummary, fetchPeople } from '../../../core_apps/people/data/peopleApi';
import { BluetoothDevice, displayName } from '../../../shared/bluetooth/model';
import { useBluetoothI18n } from '../scope';

interface PersonPickerModalProps {
  readonly device: BluetoothDevice;
  readonly onSelect: (personSlug: string) => void;
  readonly onCancel: () => void;
  readonly pending?: boolean;
}

const HUES = ['bg-blue-500', 'bg-indigo-500', 'bg-violet-500', 'bg-purple-500', 'bg-pink-500', 'bg-teal-500', 'bg-emerald-500'];
function getHue(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i);
  }
  return HUES[Math.abs(hash) % HUES.length];
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0 || !parts[0]) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export const PersonPickerModal: React.FC<PersonPickerModalProps> = ({
  device,
  onSelect,
  onCancel,
  pending = false,
}) => {
  const { t } = useBluetoothI18n();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [people, setPeople] = useState<readonly PersonSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const initialSlug = typeof device.settings.person_slug === 'string' ? device.settings.person_slug : '';
  const [selectedSlug, setSelectedSlug] = useState<string>(initialSlug);

  const name = displayName(device);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    fetchPeople(controller.signal)
      .then((data) => {
        if (active) {
          setPeople(data.people);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    searchInputRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !pending) {
        onCancel();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel, pending]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return people;
    return people.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.firstName.toLowerCase().includes(q) ||
        p.lastName.toLowerCase().includes(q) ||
        p.role.toLowerCase().includes(q) ||
        p.nickname.toLowerCase().includes(q),
    );
  }, [people, query]);

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-slate-900/40 backdrop-blur-xs sm:items-center sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="person-picker-title"
        className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-t-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-900/10 sm:rounded-2xl"
      >
        <div className="flex items-start justify-between border-b border-slate-100 p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
              <UserCheck className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <h2 id="person-picker-title" className="text-base font-bold text-slate-900">
                {t('person_picker_title')}
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                {t('person_picker_subtitle', { name })}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={pending}
            aria-label={t('cancel')}
            className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-4 border-b border-slate-100 bg-slate-50/50">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('person_search_placeholder')}
              className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-9 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-600"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {/* Option: Shared / Not assigned */}
          <button
            type="button"
            onClick={() => setSelectedSlug('')}
            className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${
              selectedSlug === ''
                ? 'border-blue-500 bg-blue-50/40 ring-1 ring-blue-500'
                : 'border-slate-200 bg-white hover:bg-slate-50'
            }`}
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500">
              <User className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-800">{t('person_unassigned')}</p>
              <p className="text-xs text-slate-500">{t('person_unassigned_hint')}</p>
            </div>
            {selectedSlug === '' && (
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            )}
          </button>

          {loading ? (
            <div className="flex items-center justify-center py-8 text-sm text-slate-500">
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-blue-600" aria-hidden="true" />
              {t('loading')}
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-500">
              {t('person_no_results')}
            </div>
          ) : (
            filtered.map((person) => {
              const selected = selectedSlug === person.slug;
              return (
                <button
                  key={person.slug}
                  type="button"
                  onClick={() => setSelectedSlug(person.slug)}
                  className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${
                    selected
                      ? 'border-blue-500 bg-blue-50/40 ring-1 ring-blue-500'
                      : 'border-slate-200 bg-white hover:bg-slate-50'
                  }`}
                >
                  <span
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-semibold text-xs text-white ${getHue(
                      person.name,
                    )}`}
                  >
                    {getInitials(person.name)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-900">{person.name}</p>
                      {person.role && (
                        <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                          {person.role}
                        </span>
                      )}
                    </div>
                    {person.nickname && (
                      <p className="truncate text-xs text-slate-500">«{person.nickname}»</p>
                    )}
                  </div>
                  {selected && (
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-100 bg-slate-50 p-4">
          <button
            type="button"
            onClick={onCancel}
            disabled={pending}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            {t('cancel')}
          </button>
          <button
            type="button"
            onClick={() => onSelect(selectedSlug)}
            disabled={pending}
            className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-bold text-white shadow-xs transition hover:bg-blue-700 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
          >
            {pending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            {t('person_confirm')}
          </button>
        </div>
      </div>
    </div>
  );
};
