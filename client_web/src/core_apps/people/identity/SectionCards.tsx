import React from 'react';
import { BrainCircuit, CalendarClock, ChevronRight, HeartPulse, Mic, Plug, ScanFace, ShieldCheck, Smile } from 'lucide-react';
import { SchemaSection } from '../data/peopleApi';
import { Overview } from '../data/overviewApi';
import { localLabel, usePeopleI18n } from '../scope';

export type CardId = `sec:${string}` | 'health' | 'mood' | 'face' | 'voice' | 'habits' | 'permissions' | 'connectors' | 'memories';

export interface CardSpec {
  readonly id: CardId;
  readonly title: string;
  readonly icon: React.ReactNode;
  readonly value: string;
  readonly hint: string;
  readonly progress?: number;
  readonly tone: string;
}

interface Props {
  readonly sections: readonly SchemaSection[];
  readonly overview: Overview | null;
  readonly roleLabel: string;
  readonly onOpen: (id: CardId) => void;
}

const GROUPS = ['wellbeing', 'identity', 'life', 'biometrics', 'access', 'knowledge'] as const;
type Group = (typeof GROUPS)[number];
const icon = (Icon: React.ElementType, tone: string) => <Icon className={`h-5 w-5 ${tone}`} aria-hidden="true" />;

export function useCards(sections: readonly SchemaSection[], overview: Overview | null, roleLabel: string): Record<Group, CardSpec[]> {
  const { t, lang } = usePeopleI18n();
  const number = new Intl.NumberFormat(lang);
  const o = overview;
  const dash = '—';
  const identity: CardSpec[] = sections.map((s) => {
    const fill = o?.sections[s.id];
    return {
      id: `sec:${s.id}` as CardId,
      title: localLabel(t, lang, `section_${s.id}`, s.title),
      icon: <span className="text-lg leading-none" aria-hidden="true">{s.icon}</span>,
      value: fill ? `${fill.filled}/${fill.total}` : dash,
      hint: s.private ? t('encrypted') : t('id_fields_filled'),
      progress: fill && fill.total ? Math.round((fill.filled / fill.total) * 100) : 0,
      tone: 'text-blue-700',
    };
  });
  return {
    wellbeing: [
      {
        id: 'health', title: t('id_card_vitals'), icon: icon(HeartPulse, 'text-rose-600'), tone: 'text-rose-600',
        value: o?.health.heartRate != null ? `${number.format(o.health.heartRate)} bpm` : o?.health.metrics ? t('id_metrics', { n: o.health.metrics }) : dash,
        hint: o?.health.recovery != null ? t('id_recovery', { n: o.health.recovery }) : t('id_vitals_hint'),
      },
      {
        id: 'mood', title: t('tab_mood'), icon: icon(Smile, 'text-violet-600'), tone: 'text-violet-600',
        value: o?.mood.last ? t(`mood_${o.mood.last}`) : dash,
        hint: t('id_entries', { n: o?.mood.entries ?? 0 }),
      },
    ],
    identity,
    life: [
      {
        id: 'habits', title: t('tab_habits'), icon: icon(CalendarClock, 'text-amber-600'), tone: 'text-amber-600',
        value: t('id_visits', { n: o?.habits.visits ?? 0 }), hint: o?.habits.summary || t('id_habits_hint'),
      },
    ],
    biometrics: [
      { id: 'face', title: t('tab_face'), icon: icon(ScanFace, 'text-sky-600'), tone: 'text-sky-600', value: o ? `${Math.round(o.face)}%` : dash, hint: t('id_face_hint'), progress: o?.face ?? 0 },
      { id: 'voice', title: t('tab_voice'), icon: icon(Mic, 'text-teal-600'), tone: 'text-teal-600', value: t(o?.voice ? 'voice_badge_on' : 'voice_badge_off'), hint: t('id_voice_hint') },
    ],
    access: [
      { id: 'permissions', title: t('tab_permissions'), icon: icon(ShieldCheck, 'text-emerald-700'), tone: 'text-emerald-700', value: roleLabel, hint: t('id_permissions_hint') },
      { id: 'connectors', title: t('tab_connectors'), icon: icon(Plug, 'text-indigo-600'), tone: 'text-indigo-600', value: t('id_linked', { n: o?.connectors.length ?? 0 }), hint: t('id_connectors_hint') },
    ],
    knowledge: [
      {
        id: 'memories', title: t('id_card_knowledge'), icon: icon(BrainCircuit, 'text-fuchsia-600'), tone: 'text-fuchsia-600',
        value: t('id_memories', { n: (o?.memories.count ?? 0) + (o?.learned ?? 0) }), hint: o?.memories.last || t('id_knowledge_hint'),
      },
    ],
  };
}

const Card: React.FC<{ readonly card: CardSpec; readonly onOpen: (id: CardId) => void }> = ({ card, onOpen }) => (
  <button
    type="button"
    onClick={() => onOpen(card.id)}
    className="group flex h-full w-full flex-col gap-3 rounded-3xl bg-white p-4 text-left shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-blue-300 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-400 motion-reduce:transition-none motion-reduce:hover:translate-y-0"
  >
    <span className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-slate-50 ring-1 ring-slate-200">{card.icon}</span>
      <span className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-800">{card.title}</span>
      <ChevronRight className="h-4 w-4 shrink-0 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-blue-600" aria-hidden="true" />
    </span>
    <span className={`truncate font-['Rajdhani'] text-2xl font-bold leading-none ${card.tone}`}>{card.value}</span>
    <span className="line-clamp-2 min-h-[2rem] text-xs text-slate-500">{card.hint}</span>
    {card.progress !== undefined && (
      <span className="mt-auto h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
        <span className="block h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500" style={{ width: `${Math.max(0, Math.min(100, card.progress))}%` }} />
      </span>
    )}
  </button>
);

export const SectionCards: React.FC<Props> = ({ sections, overview, roleLabel, onOpen }) => {
  const { t } = usePeopleI18n();
  const groups = useCards(sections, overview, roleLabel);
  return (
    <div className="flex flex-col gap-6">
      {GROUPS.map((g) => (
        <section key={g} aria-labelledby={`idg-${g}`} className="flex flex-col gap-3">
          <h3 id={`idg-${g}`} className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{t(`id_group_${g}`)}</h3>
          <ul className="grid grid-cols-1 gap-3 cq-sm:grid-cols-2 cq-lg:grid-cols-3 cq-2xl:grid-cols-4 cq-3xl:grid-cols-5">
            {groups[g].map((card) => (
              <li key={card.id}>
                <Card card={card} onOpen={onOpen} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
};
