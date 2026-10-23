import * as THREE from 'three';
import type { Base } from '../types';
import { pbr } from './materials';
import { shade } from './builders/kit';
import { LIGHTS } from './looks';

const LAYERS: readonly (readonly [number, string, string])[] = [
  [0.14, 'soil', '#5c4630'], [0.26, 'soil', '#7a5a3a'], [0.24, 'soil', '#a07f55'], [0.2, 'stone', '#b9a98c'], [0.16, 'stone', '#6f6a63'],
];

export function buildBase(base: Base, table: string): THREE.Group {
  const group = new THREE.Group();
  let top = 0;
  LAYERS.forEach(([share, kind, color], index) => {
    const height = base.depth * share;
    const material = index === 0 ? pbr('soil', base.soil, 2) : pbr(kind, color, 2);
    const slab = new THREE.Mesh(new THREE.BoxGeometry(base.w, height + 0.002, base.d), material);
    slab.position.y = top - height / 2;
    group.add(shade(slab));
    top -= height;
  });
  const cap = new THREE.Mesh(new THREE.BoxGeometry(base.w, 0.012, base.d), pbr('grass', base.top, Math.max(3, base.w / 3)));
  cap.position.y = 0.002;
  group.add(shade(cap, false, true));
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(base.w + 0.7, 0.14, base.d + 0.7), pbr('paint', '#f4f0e8'));
  plinth.position.y = top - 0.07;
  group.add(shade(plinth));
  const tableMesh = new THREE.Mesh(new THREE.CircleGeometry(160, 64), new THREE.MeshStandardMaterial({ color: table, roughness: 0.92, metalness: 0 }));
  tableMesh.rotation.x = -Math.PI / 2;
  tableMesh.position.y = top - 0.14;
  tableMesh.receiveShadow = true;
  tableMesh.name = 'table';
  group.add(tableMesh);
  return group;
}

export const tableColor = (light: keyof typeof LIGHTS) => LIGHTS[light].table;
