import { asList, asObject, getJson, num, sendJson, text } from '../../core_apps/shared/http';
import type { Base, Catalog, Diorama, Item, Job, KindInfo, LensId, LightId, Look, Motion, Params, Summary } from './types';

const LIGHTS: readonly LightId[] = ['golden_hour', 'overcast', 'blue_hour', 'noon', 'night'];
const LENSES: readonly LensId[] = ['macro', 'tilt_shift', 'standard_50mm'];
const ROOT = '/api/diorama';

const params = (value: unknown): Params => {
  const out: Params = {};
  for (const [key, entry] of Object.entries(asObject(value))) {
    if (typeof entry === 'number' || typeof entry === 'string' || typeof entry === 'boolean') out[key] = entry;
  }
  return out;
};

const parseMotion = (value: unknown): Motion | null => {
  const row = asObject(value);
  const speed = num(row.speed);
  return speed === 0 ? null : { axis: row.axis === 'z' ? 'z' : 'x', speed, span: Math.max(4, num(row.span, 24)) };
};

export const parseItem = (value: unknown): Item => {
  const row = asObject(value);
  return { motion: parseMotion(row.motion), id: text(row.id), kind: text(row.kind), x: num(row.x), y: num(row.y), z: num(row.z), rot: num(row.rot), scale: num(row.scale, 1), params: params(row.params) };
};

const parseBase = (value: unknown): Base => {
  const row = asObject(value);
  return { w: num(row.w, 22), d: num(row.d, 15), depth: num(row.depth, 1.2), soil: text(row.soil, '#6b4a2f'), top: text(row.top, '#7da04a') };
};

const parseLook = (value: unknown): Look => {
  const row = asObject(value);
  const light = LIGHTS.find((id) => id === row.light) ?? 'golden_hour';
  const lens = LENSES.find((id) => id === row.lens) ?? 'tilt_shift';
  return { light, lens, blur: num(row.blur, 0.6), mist: num(row.mist, 0.25), angle: num(row.angle, 38), orbit: row.orbit !== false };
};

const parseJob = (value: unknown): Job => {
  const row = asObject(value);
  const state = ['building', 'done', 'error'].find((s) => s === row.state);
  return { state: (state as Job['state']) ?? 'idle', stage: text(row.stage), stages: asList<string>(row.stages).filter((s) => typeof s === 'string'), mode: text(row.mode) };
};

export const parseDiorama = (value: unknown): Diorama => {
  const row = asObject(value);
  return {
    id: text(row.id), title: text(row.title), story: text(row.story), prompt: text(row.prompt), base: parseBase(row.base), look: parseLook(row.look),
    items: asList(row.items).map(parseItem).filter((i) => i.id && i.kind), revision: num(row.revision), job: parseJob(row.job),
  };
};

export const parseCatalog = (value: unknown): Catalog => {
  const row = asObject(value);
  const kinds = asList(row.kinds).map((k): KindInfo => {
    const o = asObject(k);
    const rawParams = asObject(o.params);
    const parsed: KindInfo['params'] = {};
    for (const [name, spec] of Object.entries(rawParams)) {
      const s = asObject(spec);
      parsed[name] = { type: s.type as KindInfo['params'][string]['type'], min: num(s.min), max: num(s.max), default: s.default as never, choices: asList<string>(s.choices) };
    }
    return { id: text(o.id), label: text(o.label), group: text(o.group), hint: text(o.hint), params: parsed };
  });
  return { kinds, lights: LIGHTS, lenses: LENSES };
};

export const parseSummaries = (value: unknown): Summary[] =>
  asList(asObject(value).items).map((r) => {
    const o = asObject(r);
    return { id: text(o.id), title: text(o.title), created: num(o.created), count: num(o.count) };
  });

export const fetchCatalog = async () => parseCatalog(await getJson(`${ROOT}/catalog`));
export const fetchList = async () => parseSummaries(await getJson(`${ROOT}`));
export const fetchOne = async (id: string, signal?: AbortSignal) => parseDiorama(await getJson(`${ROOT}/${id}`, signal));
export const createDiorama = async (prompt: string) => text(asObject(await sendJson(ROOT, 'POST', { prompt })).id);
export const refineDiorama = (id: string, instruction: string) => sendJson(`${ROOT}/${id}/refine`, 'POST', { instruction });
export const removeDiorama = (id: string) => sendJson(`${ROOT}/${id}`, 'DELETE');
export const saveLook = (id: string, look: Partial<Look>) => sendJson(`${ROOT}/${id}/look`, 'PUT', look);
export const saveBase = (id: string, base: Partial<Base>) => sendJson(`${ROOT}/${id}/base`, 'PUT', base);
export const addItem = async (id: string, item: Partial<Item>) => parseItem(await sendJson(`${ROOT}/${id}/items`, 'POST', item));
export const updateItem = async (id: string, itemId: string, patch: Partial<Item>) => parseItem(await sendJson(`${ROOT}/${id}/items/${itemId}`, 'PUT', patch));
export const deleteItem = (id: string, itemId: string) => sendJson(`${ROOT}/${id}/items/${itemId}`, 'DELETE');
