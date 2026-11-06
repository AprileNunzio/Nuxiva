import { asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';

export interface FaceMark {
  readonly region: string;
  readonly side: string;
  readonly strength: number;
}

export interface FaceSimilar {
  readonly slug: string;
  readonly name: string;
  readonly similarity: number;
}

export interface FaceInsight {
  readonly samples: number;
  readonly threshold: number | null;
  readonly marks: readonly FaceMark[];
  readonly marksSamples: number;
  readonly similar: readonly FaceSimilar[];
  readonly shadowOf: string | null;
}

const REGIONS = new Set(['forehead', 'brow', 'eye', 'cheek', 'nose', 'mouth', 'chin']);
const SIDES = new Set(['left', 'right']);
const num = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) ? value : 0);
const rows = (value: unknown): Record<string, unknown>[] => (Array.isArray(value) ? value.slice(0, 32).map(asRecord) : []);

export async function fetchFaceInsight(slug: string, signal?: AbortSignal): Promise<FaceInsight | null> {
  const raw = asRecord(await requestJson<unknown>(`/api/people/${encodeURIComponent(slug)}/face`, { signal })).face;
  if (raw === null || typeof raw !== 'object') {
    return null;
  }
  const face = asRecord(raw);
  return {
    samples: num(face.samples),
    threshold: typeof face.threshold === 'number' ? face.threshold : null,
    marksSamples: num(face.marks_samples),
    shadowOf: asString(face.shadow_of, 60),
    marks: rows(face.marks).flatMap((m) => {
      const region = asString(m.region, 20);
      const side = asString(m.side, 10);
      return region && side && REGIONS.has(region) && SIDES.has(side) ? [{ region, side, strength: num(m.strength) }] : [];
    }),
    similar: rows(face.similar).flatMap((s) => {
      const id = asString(s.slug, 60);
      return id ? [{ slug: id, name: asString(s.name, 80) ?? id, similarity: num(s.similarity) }] : [];
    }),
  };
}
