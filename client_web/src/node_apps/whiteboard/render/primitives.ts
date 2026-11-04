export const PAGE_W = 1600;
export const PAGE_H = 900;
export const BOARD_BG = '#12211b';
export const HAND = '"Segoe Print","Bradley Hand","Comic Sans MS","Chalkboard SE",cursive';
export const MONO = '"DejaVu Sans Mono","Cascadia Mono",Consolas,monospace';
export const SANS = '"Segoe UI",Roboto,Arial,sans-serif';
export const INKS = ['#f4f4f0', '#ffd166', '#ff4d6a', '#7cfc9a', '#29e0ff'] as const;
export const WIDTHS = { s: 4, m: 9, l: 18 } as const;
export const SERIES = ['#29e0ff', '#ffd166', '#ff4d6a', '#7cfc9a', '#c792ea', '#f4a261', '#90e0ef', '#e9c46a'] as const;
export const CALLOUT: Readonly<Record<string, readonly [string, string]>> = {
  info: ['#29e0ff', 'ⓘ'],
  tip: ['#7cfc9a', '✱'],
  warning: ['#ff4d6a', '!'],
  definition: ['#ffd166', '§'],
  formula: ['#c792ea', '∑'],
  example: ['#f4a261', '✎'],
};

const HEX = /^#[0-9a-fA-F]{6}$/;
const IMAGE_SRC = /^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/;

export type Item = Readonly<Record<string, unknown>>;

export const n = (item: Item, key: string, fallback = 0): number => {
  const value = item[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
};
export const s = (item: Item, key: string): string => (typeof item[key] === 'string' ? (item[key] as string) : '');
export const ink = (item: Item, fallback = '#f4f4f0'): string => (HEX.test(s(item, 'color')) ? s(item, 'color') : fallback);
export const strings = (value: unknown): string[] => (Array.isArray(value) ? value.map((v) => (typeof v === 'string' ? v : String(v ?? ''))) : []);
export const numbers = (value: unknown): number[] => (Array.isArray(value) ? value.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0)) : []);
export const points = (value: unknown): (readonly [number, number | null])[] =>
  Array.isArray(value)
    ? value
        .filter((p): p is unknown[] => Array.isArray(p) && p.length === 2 && typeof p[0] === 'number')
        .map((p) => [p[0] as number, typeof p[1] === 'number' ? p[1] : null] as const)
    : [];

export function roundRect(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

export function niceStep(span: number): number {
  const raw = span / 8;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const ratio = raw / mag;
  return (ratio < 1.5 ? 1 : ratio < 3.5 ? 2 : ratio < 7.5 ? 5 : 10) * mag;
}

const images = new Map<number, HTMLImageElement>();

export function imageFor(item: Item, onLoad: () => void): HTMLImageElement | null {
  const id = n(item, 'id', -1);
  const src = s(item, 'src');
  if (!IMAGE_SRC.test(src)) {
    return null;
  }
  let img = images.get(id);
  if (!img) {
    img = new Image();
    img.onload = onLoad;
    img.src = src;
    images.set(id, img);
    if (images.size > 64) {
      const oldest = images.keys().next().value;
      if (oldest !== undefined) {
        images.delete(oldest);
      }
    }
  }
  return img.complete && img.naturalWidth ? img : null;
}
