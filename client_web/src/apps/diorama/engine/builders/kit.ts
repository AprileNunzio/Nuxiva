import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import type { Params } from '../../types';
import { pbr } from '../materials';
import type { Rng } from '../rng';

export interface BuildContext {
  readonly lamps: { left: number };
}

export type Builder = (params: Params, rng: Rng, ctx: BuildContext) => THREE.Object3D;

export const n = (p: Params, key: string, fallback: number): number => (typeof p[key] === 'number' ? (p[key] as number) : fallback);
export const s = (p: Params, key: string, fallback: string): string => (typeof p[key] === 'string' ? (p[key] as string) : fallback);
export const b = (p: Params, key: string, fallback: boolean): boolean => (typeof p[key] === 'boolean' ? (p[key] as boolean) : fallback);

export function shade<T extends THREE.Object3D>(object: T, cast = true, receive = true): T {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.InstancedMesh) {
      child.castShadow = cast;
      child.receiveShadow = receive;
    }
  });
  return object;
}

export function box(w: number, h: number, d: number, material: THREE.Material, x = 0, y = 0, z = 0, round = 0): THREE.Mesh {
  const geometry = round > 0 ? new RoundedBoxGeometry(w, h, d, 3, Math.min(round, w / 2, h / 2, d / 2)) : new THREE.BoxGeometry(w, h, d);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(x, y + h / 2, z);
  return shade(mesh);
}

export function cyl(rTop: number, rBottom: number, h: number, material: THREE.Material, x = 0, y = 0, z = 0, seg = 20): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, h, seg), material);
  mesh.position.set(x, y + h / 2, z);
  return shade(mesh);
}

export function ball(radius: number, material: THREE.Material, x = 0, y = 0, z = 0): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 20, 14), material);
  mesh.position.set(x, y, z);
  return shade(mesh);
}

export function jitterColor(base: string, rng: Rng, hue = 0.03, sat = 0.1, light = 0.08): THREE.Color {
  const color = new THREE.Color(base);
  const hsl = { h: 0, s: 0, l: 0 };
  color.getHSL(hsl);
  return color.setHSL(hsl.h + (rng() - 0.5) * hue, Math.min(1, Math.max(0, hsl.s + (rng() - 0.5) * sat)), Math.min(1, Math.max(0, hsl.l + (rng() - 0.5) * light)));
}

export function labelTexture(text: string, fg: string, bg: string, ratio = 4): THREE.CanvasTexture {
  const el = document.createElement('canvas');
  el.width = 512;
  el.height = Math.round(512 / ratio);
  const ctx = el.getContext('2d');
  if (ctx) {
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, el.width, el.height);
    ctx.fillStyle = fg;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    let size = el.height * 0.62;
    ctx.font = `700 ${size}px "Helvetica Neue", Arial, sans-serif`;
    while (ctx.measureText(text).width > el.width * 0.9 && size > 12) {
      size -= 4;
      ctx.font = `700 ${size}px "Helvetica Neue", Arial, sans-serif`;
    }
    ctx.fillText(text, el.width / 2, el.height / 2 + size * 0.04);
  }
  const texture = new THREE.CanvasTexture(el);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

export function board(width: number, height: number, text: string, fg: string, bg: string, thickness = 0.03): THREE.Mesh {
  const front = new THREE.MeshStandardMaterial({ map: labelTexture(text, fg, bg, width / height), roughness: 0.5 });
  const side = pbr('paint', bg);
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, thickness), [side, side, side, side, front, side]);
  return shade(mesh);
}

export function gableRoof(w: number, d: number, h: number, material: THREE.Material, overhang = 0.3, trim?: THREE.Material): THREE.Group {
  const group = new THREE.Group();
  const run = d / 2 + overhang;
  const rise = h;
  const slope = Math.atan2(rise, run);
  const length = Math.hypot(run, rise);
  const span = w + overhang * 2;
  for (const side of [-1, 1]) {
    const slab = box(span, 0.06, length, material);
    slab.position.set(0, rise / 2, side * run / 2);
    slab.rotation.x = side * slope;
    group.add(slab);
  }
  const gable = new THREE.Shape([new THREE.Vector2(-d / 2, 0), new THREE.Vector2(d / 2, 0), new THREE.Vector2(0, h * 0.94)]);
  for (const side of [-1, 1]) {
    const mesh = new THREE.Mesh(new THREE.ExtrudeGeometry(gable, { depth: 0.04, bevelEnabled: false }), trim ?? pbr('paint', '#d8cfbd'));
    mesh.rotation.y = Math.PI / 2;
    mesh.position.set(side * (w / 2 - 0.02) - (side > 0 ? 0 : 0.02), 0, 0);
    group.add(shade(mesh));
  }
  group.add(cyl(0.04, 0.04, span, material, 0, rise - 0.01, 0, 8).rotateZ(Math.PI / 2));
  return group;
}

export function instanced(geometry: THREE.BufferGeometry, material: THREE.Material, count: number): THREE.InstancedMesh {
  const mesh = new THREE.InstancedMesh(geometry, material, count);
  mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);
  return shade(mesh);
}

export const TMP = new THREE.Object3D();

export function place(mesh: THREE.InstancedMesh, index: number, position: THREE.Vector3, rotation: THREE.Euler, scale: THREE.Vector3, color?: THREE.Color): void {
  TMP.position.copy(position);
  TMP.rotation.copy(rotation);
  TMP.scale.copy(scale);
  TMP.updateMatrix();
  mesh.setMatrixAt(index, TMP.matrix);
  if (color) mesh.setColorAt(index, color);
}
