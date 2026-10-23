import * as THREE from 'three';
import { seeded } from './rng';

export type Surface = 'concrete' | 'wood' | 'asphalt' | 'tile' | 'brick' | 'bark' | 'soil' | 'stone' | 'grass' | 'metal' | 'plain';

const SIZE = 256;
const cache = new Map<Surface, { bump: THREE.CanvasTexture; rough: THREE.CanvasTexture }>();

function canvas(): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const el = document.createElement('canvas');
  el.width = SIZE;
  el.height = SIZE;
  const ctx = el.getContext('2d');
  if (!ctx) throw new Error('canvas_unavailable');
  return [el, ctx];
}

function noise(ctx: CanvasRenderingContext2D, rng: () => number, base: number, amount: number, stretchX = 1, stretchY = 1) {
  const image = ctx.getImageData(0, 0, SIZE, SIZE);
  const coarse = new Float32Array(64 * 64).map(() => rng());
  for (let y = 0; y < SIZE; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      const gx = (x / stretchX) / 4;
      const gy = (y / stretchY) / 4;
      const x0 = Math.floor(gx) & 63;
      const y0 = Math.floor(gy) & 63;
      const fx = gx - Math.floor(gx);
      const fy = gy - Math.floor(gy);
      const a = coarse[y0 * 64 + x0];
      const b = coarse[y0 * 64 + ((x0 + 1) & 63)];
      const c = coarse[((y0 + 1) & 63) * 64 + x0];
      const d = coarse[((y0 + 1) & 63) * 64 + ((x0 + 1) & 63)];
      const smooth = a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy;
      const value = Math.max(0, Math.min(255, base + (smooth - 0.5) * amount + (rng() - 0.5) * amount * 0.35));
      const i = (y * SIZE + x) * 4;
      image.data[i] = image.data[i + 1] = image.data[i + 2] = value;
      image.data[i + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
}

function lines(ctx: CanvasRenderingContext2D, kind: Surface, rng: () => number) {
  ctx.strokeStyle = '#000';
  if (kind === 'tile') {
    ctx.lineWidth = 3;
    for (let x = 0; x <= SIZE; x += 16) {
      ctx.globalAlpha = 0.55;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, SIZE);
      ctx.stroke();
    }
    ctx.globalAlpha = 0.25;
    for (let y = 0; y < SIZE; y += 8) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(SIZE, y);
      ctx.stroke();
    }
  }
  if (kind === 'brick') {
    ctx.lineWidth = 3;
    ctx.globalAlpha = 0.6;
    for (let row = 0; row < 16; row += 1) {
      const y = row * 16;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(SIZE, y);
      ctx.stroke();
      for (let x = (row % 2) * 16; x < SIZE; x += 32) {
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, y + 16);
        ctx.stroke();
      }
    }
  }
  if (kind === 'wood' || kind === 'bark') {
    ctx.lineWidth = 1;
    for (let i = 0; i < 90; i += 1) {
      ctx.globalAlpha = 0.12 + rng() * 0.22;
      const x = rng() * SIZE;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.bezierCurveTo(x + rng() * 10 - 5, SIZE * 0.3, x + rng() * 10 - 5, SIZE * 0.7, x + rng() * 6 - 3, SIZE);
      ctx.stroke();
    }
  }
  if (kind === 'stone') {
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.4;
    for (let i = 0; i < 24; i += 1) {
      ctx.beginPath();
      ctx.moveTo(rng() * SIZE, rng() * SIZE);
      ctx.lineTo(rng() * SIZE, rng() * SIZE);
      ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;
}

const PROFILE: Record<Surface, { base: number; amount: number; sx: number; sy: number; rough: number }> = {
  concrete: { base: 150, amount: 120, sx: 1, sy: 1, rough: 200 }, wood: { base: 140, amount: 90, sx: 0.4, sy: 6, rough: 170 },
  asphalt: { base: 120, amount: 200, sx: 0.5, sy: 0.5, rough: 235 }, tile: { base: 170, amount: 50, sx: 1, sy: 1, rough: 90 },
  brick: { base: 150, amount: 110, sx: 1, sy: 1, rough: 215 }, bark: { base: 130, amount: 190, sx: 0.5, sy: 5, rough: 230 },
  soil: { base: 130, amount: 190, sx: 1, sy: 1, rough: 245 }, stone: { base: 150, amount: 150, sx: 1, sy: 1, rough: 190 },
  grass: { base: 140, amount: 150, sx: 0.6, sy: 0.6, rough: 235 }, metal: { base: 190, amount: 40, sx: 4, sy: 0.5, rough: 90 },
  plain: { base: 255, amount: 0, sx: 1, sy: 1, rough: 150 },
};

export function surface(kind: Surface) {
  const hit = cache.get(kind);
  if (hit) return hit;
  const profile = PROFILE[kind];
  const rng = seeded(`tex:${kind}`);
  const make = (base: number, amount: number, decorate: boolean) => {
    const [el, ctx] = canvas();
    noise(ctx, rng, base, amount, profile.sx, profile.sy);
    if (decorate) lines(ctx, kind, rng);
    const texture = new THREE.CanvasTexture(el);
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.anisotropy = 4;
    return texture;
  };
  const created = { bump: make(profile.base, profile.amount, true), rough: make(profile.rough, Math.min(60, profile.amount * 0.4), false) };
  cache.set(kind, created);
  return created;
}
