import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, ScanFace, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { PersonSummary, Profile, SchemaSection, associatePerson, deletePerson, fetchPerson, updatePerson } from '../data/peopleApi';
import { Overview, fetchOverview } from '../data/overviewApi';
import { PERMISSION_KEYS, chipClass, fieldClass, localLabel, relative, usePeopleI18n } from '../scope';
import { ConnectorsTab } from '../components/ConnectorsTab';
import { FaceTab } from '../components/FaceTab';
import { HabitsTab } from '../components/HabitsTab';
import { HealthTab } from '../components/HealthTab';
import { MemoriesTab } from '../components/MemoriesTab';
import { MoodTab } from '../components/MoodTab';
import { SectionForm } from '../components/SectionForm';
import { VoiceTab } from '../components/VoiceTab';
import { Portrait } from './IdentityCard';
import { CardId, SectionCards, useCards } from './SectionCards';
import { nameParts } from './names';

interface Props {
  readonly summary: PersonSummary;
  readonly sections: readonly SchemaSection[];
  readonly voices: Readonly<Record<string, string>>;
  readonly people: readonly PersonSummary[];
  readonly roles: Readonly<Record<string, string>>;
  readonly present: boolean;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
  readonly onBack: () => void;
  readonly onDeleted: () => void;
}

const OVERVIEW_MS = 30000;
const isPermission = (key: string) => (PERMISSION_KEYS as readonly string[]).includes(key);
const badge = (on: boolean) => `rounded-full px-2.5 py-0.5 text-xs font-semibold ${on ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200' : 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'}`;

export const PersonPage: React.FC<Props> = ({ summary, sections, voices, people, roles, present, busy, run, onBack, onDeleted }) => {
  const { t, lang } = usePeopleI18n();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [open, setOpen] = useState<CardId | null>(null);
  const [tick, setTick] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [naming, setNaming] = useState('');
  const [target, setTarget] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetchPerson(summary.slug, controller.signal)
      .then(setProfile)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_profile_failed', cause));
    fetchOverview(summary.slug, controller.signal)
      .then(setOverview)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_profile_failed', cause));
    return () => controller.abort();
  }, [summary.slug, tick]);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((v) => v + 1), OVERVIEW_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    window.scrollTo?.({ top: 0, behavior: 'smooth' });
  }, [open]);

  const act = async (key: string, task: () => Promise<unknown>, code: string) => {
    const ok = await run(key, task, code);
    if (ok) {
      setTick((v) => v + 1);
    }
    return ok;
  };

  const profileSections = useMemo(
    () =>
      sections
        .filter((s) => s.id !== 'routine')
        .map((s) => ({ ...s, fields: s.fields.filter((f) => !isPermission(f.key)) }))
        .filter((s) => s.fields.length),
    [sections],
  );
  const permissionFields = useMemo(() => sections.flatMap((s) => s.fields).filter((f) => isPermission(f.key)), [sections]);
  const routineSection = useMemo(() => sections.find((s) => s.id === 'routine'), [sections]);
  const roleLabel = roles[summary.role] ?? summary.role;
  const cards = useCards(profileSections, overview, roleLabel);
  const openCard = open ? Object.values(cards).flat().find((c) => c.id === open) : undefined;
  const { surname, given } = nameParts(summary);

  const detail = () => {
    if (!profile || !open) {
      return null;
    }
    if (open.startsWith('sec:')) {
      const section = profileSections.find((s) => `sec:${s.id}` === open);
      return section ? (
        <SectionForm key={section.id} slug={summary.slug} title={localLabel(t, lang, `section_${section.id}`, section.title)} isPrivate={section.private}
          fields={section.fields} profile={profile} people={people} busy={busy} run={act} />
      ) : null;
    }
    switch (open) {
      case 'permissions':
        return <SectionForm slug={summary.slug} title={t('tab_permissions')} isPrivate={false} fields={permissionFields} profile={profile} people={people} busy={busy} run={act} />;
      case 'face':
        return <FaceTab slug={summary.slug} quality={summary.quality} busy={busy} run={act} />;
      case 'voice':
        return <VoiceTab slug={summary.slug} profile={profile} voices={voices} busy={busy} run={act} onChanged={() => setTick((v) => v + 1)} />;
      case 'habits':
        return <HabitsTab summary={summary} profile={profile} section={routineSection} people={people} busy={busy} run={act} />;
      case 'connectors':
        return <ConnectorsTab slug={summary.slug} busy={busy} run={act} />;
      case 'memories':
        return <MemoriesTab slug={summary.slug} busy={busy} run={act} />;
      case 'mood':
        return <MoodTab slug={summary.slug} busy={busy} run={act} />;
      case 'health':
        return <HealthTab slug={summary.slug} busy={busy} run={act} onConnectors={() => setOpen('connectors')} />;
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <nav className="flex flex-wrap items-center gap-1 text-sm" aria-label={t('id_breadcrumb')}>
        <button type="button" onClick={open ? () => setOpen(null) : onBack}
          className="flex items-center gap-1.5 rounded-full px-3 py-1.5 font-semibold text-blue-800 transition hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          {open ? t('id_back_person', { name: [surname, given].filter(Boolean).join(' ') }) : t('id_back_all')}
        </button>
      </nav>
      <header className="flex flex-col gap-4 rounded-3xl bg-gradient-to-br from-white via-white to-blue-50 p-4 shadow-sm ring-1 ring-slate-200 sm:flex-row sm:items-center sm:p-6">
        <Portrait person={summary} className={`${open ? 'h-16 w-16' : 'h-28 w-28 sm:h-32 sm:w-32'} shrink-0 rounded-3xl ring-4 ring-white shadow-md transition-all`} text={open ? 'text-xl' : 'text-4xl'} />
        <div className="min-w-0 flex-1">
          <h2 id="person-title" className="font-['Rajdhani'] leading-tight text-slate-900">
            <span className={`block font-bold uppercase tracking-wide ${open ? 'text-2xl' : 'text-3xl sm:text-4xl'}`}>{summary.scanned ? t('unknown_face') : surname}</span>
            {!summary.scanned && given && <span className={`block text-slate-600 ${open ? 'text-lg' : 'text-xl sm:text-2xl'}`}>{given}</span>}
          </h2>
          {open && openCard ? (
            <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-slate-700">{openCard.icon}{openCard.title}</p>
          ) : (
            <p className="mt-2 flex flex-wrap gap-1.5">
              <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-800 ring-1 ring-blue-200">{roleLabel}</span>
              {summary.membership && <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200">{t(`membership_${summary.membership}`)}</span>}
              <span className={badge(present)}>{present ? t('present_now') : summary.lastSeen ? t('seen', { when: relative(summary.lastSeen, lang) }) : t('never_seen')}</span>
              {summary.age !== null && <span className={badge(false)}>{t('age', { age: summary.age })}</span>}
              {overview?.since && <span className={badge(false)}>{t('id_known_since', { when: new Date(overview.since * 1000).toLocaleDateString(lang, { year: 'numeric', month: 'long' }) })}</span>}
            </p>
          )}
        </div>
        {!open && (
          <button type="button" disabled={busy !== null} onClick={() => setConfirm(true)} className={`${chipClass} self-start border-rose-200 bg-white py-2 text-rose-700 sm:self-center`}>
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            {t('delete_person')}
          </button>
        )}
      </header>
      {summary.scanned && !open && (
        <div className="grid gap-2 rounded-3xl bg-amber-50 p-4 ring-1 ring-amber-200 cq-lg:grid-cols-2">
          <p className="flex items-center gap-2 text-sm text-amber-900 cq-lg:col-span-2">
            <ScanFace className="h-4 w-4" aria-hidden="true" />
            {t('scanned_hint')}
          </p>
          <div className="flex gap-2">
            <input value={naming} maxLength={40} onChange={(event) => setNaming(event.target.value)} placeholder={t('give_name')} aria-label={t('give_name')} className={`${fieldClass} min-w-0 flex-1`} />
            <button type="button" disabled={!naming.trim() || busy !== null} onClick={() => void act('name', () => updatePerson(summary.slug, { name: naming.trim() }), 'people_update_failed')} className={`${chipClass} border-blue-300 bg-blue-50 px-3 text-blue-900`}>
              {t('save')}
            </button>
          </div>
          <div className="flex gap-2">
            <select value={target} onChange={(event) => setTarget(event.target.value)} aria-label={t('associate_to')} className={`${fieldClass} min-w-0 flex-1`}>
              <option value="">{t('associate_to')}</option>
              {people.filter((p) => !p.scanned).map((p) => (
                <option key={p.slug} value={p.slug}>{p.name}</option>
              ))}
            </select>
            <button type="button" disabled={!target || busy !== null} onClick={() => void run('associate', () => associatePerson(summary.slug, target), 'people_associate_failed').then((ok) => ok && onDeleted())} className={`${chipClass} border-blue-300 bg-blue-50 px-3 text-blue-900`}>
              {t('associate')}
            </button>
          </div>
        </div>
      )}
      {!profile ? (
        <p className="flex items-center gap-2 text-sm text-slate-600" role="status">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          {t('loading')}
        </p>
      ) : open ? (
        <section className="rounded-3xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:p-6" aria-labelledby="person-title">{detail()}</section>
      ) : (
        <>
          <p className="text-xs text-slate-500">{t('id_auto_hint')}</p>
          <SectionCards sections={profileSections} overview={overview} roleLabel={roleLabel} onOpen={setOpen} />
        </>
      )}
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
    </div>
  );
};
