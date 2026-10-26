import React, { useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import type { Base, Catalog, Item, KindInfo, ParamValue } from '../types';

interface ScenePanelProps {
  readonly catalog: Catalog;
  readonly items: readonly Item[];
  readonly base: Base;
  readonly selected: string;
  readonly t: (key: string) => string;
  readonly onSelect: (id: string) => void;
  readonly onAdd: (kind: string) => void;
  readonly onPatch: (id: string, patch: Partial<Item>) => void;
  readonly onDrop: (id: string) => void;
}

const Field: React.FC<{ label: string; value: number; min: number; max: number; step: number; onCommit: (v: number) => void }> = ({ label, value, min, max, step, onCommit }) => (
  <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
    <span className="w-14 shrink-0">{label}</span>
    <input type="range" min={min} max={max} step={step} defaultValue={value} key={value} onPointerUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))} onKeyUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))} className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-slate-200 accent-sky-600" />
    <span className="w-10 text-right font-mono text-[11px] text-slate-400">{value.toFixed(step < 1 ? 1 : 0)}</span>
  </label>
);

const Inspector: React.FC<{ item: Item; info: KindInfo | undefined; base: Base; t: (k: string) => string; onPatch: ScenePanelProps['onPatch']; onDrop: () => void }> = ({ item, info, base, t, onPatch, onDrop }) => {
  const set = (name: string, value: ParamValue) => onPatch(item.id, { params: { ...item.params, [name]: value } });
  return (
    <div className="space-y-3 rounded-2xl border border-sky-200 bg-sky-50/50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold text-slate-900">{info?.label ?? item.kind}</span>
        <button type="button" onClick={onDrop} aria-label={t('delete')} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"><Trash2 className="h-4 w-4" /></button>
      </div>
      <Field label="X" value={item.x} min={-base.w / 2} max={base.w / 2} step={0.1} onCommit={(x) => onPatch(item.id, { x })} />
      <Field label="Z" value={item.z} min={-base.d / 2} max={base.d / 2} step={0.1} onCommit={(z) => onPatch(item.id, { z })} />
      <Field label={t('rotation')} value={item.rot} min={-180} max={180} step={1} onCommit={(rot) => onPatch(item.id, { rot })} />
      <Field label={t('scale')} value={item.scale} min={0.3} max={3} step={0.05} onCommit={(scale) => onPatch(item.id, { scale })} />
      {info && Object.entries(info.params).map(([name, spec]) => {
        const value = item.params[name] ?? spec.default;
        if (spec.type === 'color') {
          return (
            <label key={name} className="flex items-center gap-2 text-xs font-semibold text-slate-600">
              <span className="w-14 shrink-0 truncate">{name}</span>
              <input type="color" defaultValue={String(value)} key={String(value)} onBlur={(e) => set(name, e.target.value)} className="h-7 w-full cursor-pointer rounded-lg border border-slate-200 bg-white p-0.5" />
            </label>
          );
        }
        if (spec.type === 'number') return <Field key={name} label={name} value={Number(value)} min={spec.min} max={spec.max} step={spec.max - spec.min > 12 ? 0.5 : 0.05} onCommit={(v) => set(name, v)} />;
        if (spec.type === 'choice') {
          return (
            <label key={name} className="flex items-center gap-2 text-xs font-semibold text-slate-600">
              <span className="w-14 shrink-0 truncate">{name}</span>
              <select value={String(value)} onChange={(e) => set(name, e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs">
                {spec.choices.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          );
        }
        if (spec.type === 'flag') {
          return (
            <label key={name} className="flex items-center gap-2 text-xs font-semibold text-slate-600">
              <input type="checkbox" checked={Boolean(value)} onChange={(e) => set(name, e.target.checked)} className="h-4 w-4 accent-sky-600" />
              {name}
            </label>
          );
        }
        return (
          <label key={name} className="flex items-center gap-2 text-xs font-semibold text-slate-600">
            <span className="w-14 shrink-0 truncate">{name}</span>
            <input type="text" defaultValue={String(value)} maxLength={24} onBlur={(e) => set(name, e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs" />
          </label>
        );
      })}
    </div>
  );
};

export const ScenePanel: React.FC<ScenePanelProps> = ({ catalog, items, base, selected, t, onSelect, onAdd, onPatch, onDrop }) => {
  const [kind, setKind] = useState('tree_cherry');
  const infoById = useMemo(() => new Map(catalog.kinds.map((k) => [k.id, k])), [catalog]);
  const chosen = items.find((i) => i.id === selected);
  const groups = useMemo(() => {
    const map = new Map<string, Item[]>();
    for (const item of items) {
      const group = infoById.get(item.kind)?.group ?? '';
      map.set(group, [...(map.get(group) ?? []), item]);
    }
    return [...map.entries()];
  }, [items, infoById]);
  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        <select value={kind} onChange={(e) => setKind(e.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700">
          {catalog.kinds.map((k) => <option key={k.id} value={k.id}>{k.group} · {k.label}</option>)}
        </select>
        <button type="button" onClick={() => onAdd(kind)} className="flex shrink-0 items-center gap-1.5 rounded-xl bg-slate-900 px-3 py-2 text-xs font-semibold text-white transition hover:bg-sky-600">
          <Plus className="h-4 w-4" />{t('add_element')}
        </button>
      </div>
      {chosen && <Inspector item={chosen} info={infoById.get(chosen.kind)} base={base} t={t} onPatch={onPatch} onDrop={() => onDrop(chosen.id)} />}
      {items.length === 0 && <p className="py-6 text-center text-xs text-slate-400">{t('no_items')}</p>}
      {groups.map(([group, rows]) => (
        <section key={group}>
          <h3 className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{group} · {rows.length}</h3>
          <div className="flex flex-wrap gap-1.5">
            {rows.map((item) => (
              <button key={item.id} type="button" onClick={() => onSelect(item.id)} className={`rounded-lg border px-2 py-1 text-[11px] font-semibold transition ${item.id === selected ? 'border-sky-400 bg-sky-100 text-sky-800' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'}`}>
                {infoById.get(item.kind)?.label ?? item.kind}
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
};
