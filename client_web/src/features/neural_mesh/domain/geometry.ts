import { Point, SynapsePath } from './types';

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function distance(a: Point, b: Point): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

export function moveToward(from: Point, to: Point, amount: number): Point {
  const length = distance(from, to);
  if (length === 0) {
    return from;
  }
  const ratio = Math.min(1, amount / length);
  return { x: from.x + (to.x - from.x) * ratio, y: from.y + (to.y - from.y) * ratio };
}

export function bendControl(from: Point, to: Point, bend: number): Point {
  const mx = (from.x + to.x) / 2;
  const my = (from.y + to.y) / 2;
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  return { x: mx - dy * bend, y: my + dx * bend };
}

export function quadraticPoint(path: Pick<SynapsePath, 'from' | 'control' | 'to'>, t: number): Point {
  const u = 1 - t;
  return {
    x: u * u * path.from.x + 2 * u * t * path.control.x + t * t * path.to.x,
    y: u * u * path.from.y + 2 * u * t * path.control.y + t * t * path.to.y,
  };
}

export function toSvgPath(path: Pick<SynapsePath, 'from' | 'control' | 'to'>): string {
  const f = (n: number) => n.toFixed(1);
  return `M ${f(path.from.x)} ${f(path.from.y)} Q ${f(path.control.x)} ${f(path.control.y)} ${f(path.to.x)} ${f(path.to.y)}`;
}

export function onEllipse(center: Point, rx: number, ry: number, angle: number, fraction: number): Point {
  return {
    x: center.x + Math.cos(angle) * rx * fraction,
    y: center.y + Math.sin(angle) * ry * fraction,
  };
}
