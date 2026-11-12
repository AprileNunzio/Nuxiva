import * as THREE from 'three';
import type { Base } from '../types';
import { pbr } from './materials';
import { shade } from './builders/kit';
import { LIGHTS } from './looks';

interface Layer {
  readonly share: number;
  readonly kind: string;
  readonly color: string;
  readonly inset: number;
  readonly rough: number;
}

const LAYERS: readonly Layer[] = [
  { share: 0.16, kind: 'soil', color: '#5a432e', inset: 0, rough: 0.03 },
  { share: 0.24, kind: 'soil', color: '#7b5a3a', inset: 0.012, rough: 0.07 },
  { share: 0.22, kind: 'stone', color: '#8f8171', inset: 0.03, rough: 0.14 },
  { share: 0.2, kind: 'stone', color: '#6b645b', inset: 0.06, rough: 0.2 },
  { share: 0.18, kind: 'stone', color: '#4d4841', inset: 0.1, rough: 0.28 },
];

const hash = (x: number, y: number, z: number): number => {
  const v = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453;
  return v - Math.floor(v);
};

const wave = (x: number, y: number, z: number): number =>
  (hash(Math.round(x * 2), Math.round(y * 2), Math.round(z * 2)) * 0.6 + Math.sin(x * 1.7 + z * 2.3) * 0.25 + Math.sin(x * 4.1 - z * 3.3 + y) * 0.15) - 0.3;

function strata(w: number, h: number, d: number, rough: number, last: boolean, material: THREE.Material): THREE.Mesh {
  const geometry = new THREE.BoxGeometry(w, h, d, Math.max(4, Math.ceil(w * 1.6)), 3, Math.max(4, Math.ceil(d * 1.6)));
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) {
    const x = position.getX(i);
    const y = position.getY(i);
    const z = position.getZ(i);
    const onSideX = Math.abs(Math.abs(x) - w / 2) < 1e-4;
    const onSideZ = Math.abs(Math.abs(z) - d / 2) < 1e-4;
    const bottom = y < -h / 2 + 1e-4;
    if (onSideX) position.setX(i, x + Math.sign(x) * wave(x, y, z) * rough);
    if (onSideZ) position.setZ(i, z + Math.sign(z) * wave(x + 9, y, z) * rough);
    if (last && bottom) position.setY(i, y - Math.abs(wave(x, y, z + 3)) * rough * 2.4);
  }
  const flat = geometry.toNonIndexed();
  geometry.dispose();
  flat.computeVertexNormals();
  return shade(new THREE.Mesh(flat, material));
}

function contactShadow(radius: number): THREE.Mesh {
  const el = document.createElement('canvas');
  el.width = el.height = 256;
  const ctx = el.getContext('2d');
  if (ctx) {
    const gradient = ctx.createRadialGradient(128, 128, 8, 128, 128, 128);
    gradient.addColorStop(0, 'rgba(30,38,52,0.34)');
    gradient.addColorStop(0.55, 'rgba(30,38,52,0.14)');
    gradient.addColorStop(1, 'rgba(30,38,52,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 256, 256);
  }
  const texture = new THREE.CanvasTexture(el);
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(radius * 2, radius * 2), new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false, fog: false }));
  mesh.rotation.x = -Math.PI / 2;
  mesh.name = 'shadow';
  return mesh;
}

export function buildBase(base: Base): THREE.Group {
  const group = new THREE.Group();
  let top = 0;
  LAYERS.forEach((layer, index) => {
    const height = base.depth * layer.share;
    const material = index === 0 ? pbr('soil', base.soil, 2) : pbr(layer.kind, layer.color, 2);
    const slab = strata(base.w * (1 - layer.inset), height + 0.002, base.d * (1 - layer.inset), layer.rough * Math.min(2, base.w / 14), index === LAYERS.length - 1, material);
    slab.position.y = top - height / 2;
    group.add(slab);
    top -= height;
  });
  const cap = new THREE.Mesh(new THREE.BoxGeometry(base.w, 0.012, base.d), pbr('grass', base.top, Math.max(3, base.w / 3)));
  cap.position.y = 0.002;
  group.add(shade(cap, false, true));
  const shadow = contactShadow(Math.max(base.w, base.d) * 0.95);
  shadow.position.y = top - 1.1;
  group.add(shadow);
  return group;
}

export const tableColor = (light: keyof typeof LIGHTS) => LIGHTS[light].table;
