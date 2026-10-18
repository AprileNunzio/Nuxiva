import { adminPath } from '../../../shared/http/basePath';
import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, ScanFace, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { PersonSummary, Profile, SchemaSection, associatePerson, deletePerson, fetchPerson, updatePerson, voiceprintOf } from '../data/peopleApi';
import { PERMISSION_KEYS, chipClass, fieldClass, initials, localLabel, panelClass, relative, usePeopleI18n } from '../scope';
import { FaceTab } from './FaceTab';
import { HabitsTab } from './HabitsTab';
import { MemoriesTab } from './MemoriesTab';
import { MoodTab } from './MoodTab';
import { SectionForm } from './SectionForm';
import { VoiceTab } from './VoiceTab';

const TABS = ['profile', 'permissions', 'face', 'voice', 'habits', 'memories', 'mood'] as const;
type Tab = (typeof TABS)[number];

interface PersonViewProps {
  readonly summary: PersonSummary;
  readonly sections: readonly SchemaSection[];
  readonly voices: Readonly<Record<string, string>>;
  readonly people: readonly PersonSummary[];
  readonly roles: Readonly<Record<string, string>>;
  readonly present: boolean;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
  readonly onDeleted: () => void;
}

export const PersonView: React.FC<PersonViewProps> = ({ summary, sections, voices, people, roles, present, busy, run, onDeleted }) => {
  const { t, lang } = usePeopleI18n();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [tab, setTab] = useState<Tab>('profile');
  const [section, setSection] = useState<string>(sections[0]?.id ?? '');
  const [tick, setTick] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [naming, setNaming] = useState('');
  const [target, setTarget] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetchPerson(summary.slug, controller.signal)
      .then(setProfile)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_profile_failed', cause));
    return () => controller.abort();
  }, [summary.slug, tick]);

  const act = async (key: string, task: () => Promise<unknown>, code: string) => {
    const ok = await run(key, task, code);
    if (ok) {
      setTick((v) => v + 1);
    }
    return ok;
  };

  const permissionFields = useMemo(
    () => sections.flatMap((s) => s.fields).filter((f) => (PERMISSION_KEYS as readonly string[]).includes(f.key)),
    [sections],
  );
  const profileSections = useMemo(
    () => sections.map((s) => ({ ...s, fields: s.fields.filter((f) => !(PERMISSION_KEYS as readonly string[]).includes(f.key)) })).filter((s) => s.fields.length),
    [sections],
  );
  const current = profileSections.find((s) => s.id === section) ?? profileSections[0];

  if (!profile) {
    return (
      <section className={`${panelClass} flex items-center gap-2 text-sm text-slate-400`}>
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        {t('loading')}
      </section>
    );
  }

  const print = voiceprintOf(profile);
  const photo = `/api/vision/people/${summary.slug}/photo.jpg`;

  return (
    <section className={panelClass} aria-labelledby="person-title">
      <header className="flex flex-wrap items-start gap-4">
        <span className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-cyan-400/40 bg-slate-900 text-2xl font-bold text-cyan-100">
          {initials(summary.name)}
          {summary.quality > 0 && <img src={adminPath(photo)} alt="" className="absolute inset-0 h-full w-full object-cover" onError={(event) => event.currentTarget.remove()} />}
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="person-title" className="font-['Rajdhani'] text-2xl font-bold text-white sm:text-3xl">
            {summary.scanned ? t('unknown_face') : summary.name}
          </h2>
          <p className="mt-1 flex flex-wrap gap-1.5 text-xs">
            <span className="rounded-full border border-cyan-400/40 px-2 py-0.5 text-cyan-200">{roles[summary.role] ?? summary.role}</span>
            {summary.membership && <span className="rounded-full border border-indigo-400/40 px-2 py-0.5 text-indigo-200">{t(`membership_${summary.membership}`)}</span>}
            <span className={`rounded-full border px-2 py-0.5 ${present ? 'border-emerald-400/50 text-emerald-200' : 'border-slate-700 text-slate-400'}`}>
              {present ? t('present_now') : summary.lastSeen ? t('seen', { when: relative(summary.lastSeen, lang) }) : t('never_seen')}
            </span>
            <span className={`rounded-full border px-2 py-0.5 ${summary.quality > 0 ? 'border-emerald-400/40 text-emerald-200' : 'border-slate-700 text-slate-400'}`}>{t('face_badge', { quality: Math.round(summary.quality) })}</span>
            <span className={`rounded-full border px-2 py-0.5 ${print.enrolled ? 'border-emerald-400/40 text-emerald-200' : 'border-slate-700 text-slate-400'}`}>{t(print.enrolled ? 'voice_badge_on' : 'voice_badge_off')}</span>
          </p>
        </div>
        <button type="button" disabled={busy !== null} onClick={() => setConfirm(true)} className={`${chipClass} border-rose-400/40 py-2 text-rose-200`}>
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          {t('delete_person')}
        </button>
      </header>
      {summary.scanned && (
        <div className="mt-4 grid gap-2 rounded-xl border border-amber-400/40 bg-amber-400/5 p-3 lg:grid-cols-2">
          <p className="flex items-center gap-2 text-sm text-amber-100 lg:col-span-2">
            <ScanFace className="h-4 w-4" aria-hidden="true" />
            {t('scanned_hint')}
          </p>
          <div className="flex gap-2">
            <input value={naming} maxLength={40} onChange={(event) => setNaming(event.target.value)} placeholder={t('give_name')} aria-label={t('give_name')} className={`${fieldClass} min-w-0 flex-1`} />
            <button type="button" disabled={!naming.trim() || busy !== null} onClick={() => void act('name', () => updatePerson(summary.slug, { name: naming.trim() }), 'people_update_failed')} className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 px-3 text-cyan-100`}>
              {t('save')}
            </button>
          </div>
          <div className="flex gap-2">
            <select value={target} onChange={(event) => setTarget(event.target.value)} aria-label={t('associate_to')} className={`${fieldClass} min-w-0 flex-1`}>
              <option value="">{t('associate_to')}</option>
              {people.filter((p) => !p.scanned).map((p) => (
                <option key={p.slug} value={p.slug}>
                  {p.name}
                </option>
              ))}
            </select>
            <button type="button" disabled={!target || busy !== null} onClick={() => void run('associate', () => associatePerson(summary.slug, target), 'people_associate_failed').then((ok) => ok && onDeleted())} className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 px-3 text-cyan-100`}>
              {t('associate')}
            </button>
          </div>
        </div>
      )}
      <div role="tablist" aria-label={summary.name} className="mt-4 flex gap-1 overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60 p-1">
        {TABS.map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${tab === id ? 'bg-cyan-400/15 text-cyan-100' : 'text-slate-400 hover:text-white'}`}
          >
            {t(`tab_${id}`)}
          </button>
        ))}
      </div>
      <div className="mt-4" role="tabpanel">
        {tab === 'profile' && current && (
          <div className="grid gap-4 lg:grid-cols-[13rem_minmax(0,1fr)]">
            <nav aria-label={t('sections')} className="flex gap-1 overflow-x-auto lg:flex-col">
              {profileSections.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  aria-current={current.id === s.id}
                  onClick={() => setSection(s.id)}
                  className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${current.id === s.id ? 'bg-cyan-400/15 text-cyan-100' : 'text-slate-400 hover:text-white'}`}
                >
                  <span aria-hidden="true">{s.icon}</span>
                  {localLabel(t, lang, `section_${s.id}`, s.title)}
                </button>
              ))}
            </nav>
            <SectionForm
              key={current.id}
              slug={summary.slug}
              title={localLabel(t, lang, `section_${current.id}`, current.title)}
              isPrivate={current.private}
              fields={current.fields}
              profile={profile}
              people={people}
              busy={busy}
              run={act}
            />
          </div>
        )}
        {tab === 'permissions' && (
          <SectionForm slug={summary.slug} title={t('tab_permissions')} isPrivate={false} fields={permissionFields} profile={profile} people={people} busy={busy} run={act} />
        )}
        {tab === 'face' && <FaceTab slug={summary.slug} quality={summary.quality} busy={busy} run={act} />}
        {tab === 'voice' && <VoiceTab slug={summary.slug} profile={profile} voices={voices} busy={busy} run={act} />}
        {tab === 'habits' && <HabitsTab profile={profile} />}
        {tab === 'memories' && <MemoriesTab slug={summary.slug} busy={busy} run={act} />}
        {tab === 'mood' && <MoodTab slug={summary.slug} busy={busy} run={act} />}
      </div>
      {confirm && (
        <ConfirmDialog
          title={t('delete_title', { name: summary.name })}
          body={t('delete_body')}
          confirmLabel={t('delete_person')}
          cancelLabel={t('cancel')}
          pending={busy !== null}
          tone="danger"
          onConfirm={() => void run('delete', () => deletePerson(summary.slug), 'people_delete_failed').then((ok) => {
            setConfirm(false);
            if (ok) {
              onDeleted();
            }
          })}
          onCancel={() => setConfirm(false)}
        />
      )}
    </section>
  );
};
