import * as THREE from 'three';
import { pbr } from '../materials';
import { range, type Rng } from '../rng';
import { ball, cyl, instanced, jitterColor, n, place, s, shade, type Builder } from './kit';

interface Tip {
  readonly p: THREE.Vector3;
  readonly r: number;
}

function limb(group: THREE.Group, from: THREE.Vector3, to: THREE.Vector3, r0: number, r1: number, material: THREE.Material): void {
  const length = from.distanceTo(to);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(r1, r0, length, 9), material);
  mesh.position.copy(from).add(to).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), to.clone().sub(from).normalize());
  group.add(shade(mesh));
}

function branches(group: THREE.Group, rng: Rng, height: number, material: THREE.Material, tips: Tip[]): void {
  const trunkTop = new THREE.Vector3(0, 0, 0);
  const steps = 4;
  let r = height * 0.045;
  for (let i = 0; i < steps; i += 1) {
    const next = trunkTop.clone().add(new THREE.Vector3(range(rng, -0.08, 0.08) * height, (height * 0.62) / steps, range(rng, -0.08, 0.08) * height));
    limb(group, trunkTop.clone(), next, r, r * 0.8, material);
    trunkTop.copy(next);
    r *= 0.8;
  }
  const count = 5 + Math.floor(rng() * 3);
  for (let i = 0; i < count; i += 1) {
    const angle = (i / count) * Math.PI * 2 + rng() * 0.6;
    const start = trunkTop.clone().add(new THREE.Vector3(0, -height * range(rng, 0, 0.18), 0));
    const mid = start.clone().add(new THREE.Vector3(Math.cos(angle) * height * range(rng, 0.14, 0.24), height * range(rng, 0.1, 0.2), Math.sin(angle) * height * range(rng, 0.14, 0.24)));
    const end = mid.clone().add(new THREE.Vector3(Math.cos(angle + 0.4) * height * range(rng, 0.14, 0.26), height * range(rng, 0.06, 0.2), Math.sin(angle + 0.4) * height * range(rng, 0.14, 0.26)));
    limb(group, start, mid, r * 0.9, r * 0.55, material);
    limb(group, mid, end, r * 0.55, r * 0.25, material);
    tips.push({ p: end, r: height * range(rng, 0.2, 0.3) });
    tips.push({ p: mid.clone().lerp(end, 0.5), r: height * range(rng, 0.14, 0.22) });
  }
  tips.push({ p: trunkTop.clone().add(new THREE.Vector3(0, height * 0.12, 0)), r: height * 0.3 });
}

function foliage(group: THREE.Group, rng: Rng, tips: Tip[], color: string, density: number, size: number, accent?: string): void {
  const total = Math.round(Math.min(2600, 520 * density * tips.length * 0.55));
  const mesh = instanced(new THREE.IcosahedronGeometry(1, 0), new THREE.MeshStandardMaterial({ roughness: 0.82, flatShading: true }), total);
  const e = new THREE.Euler();
  const v = new THREE.Vector3();
  for (let i = 0; i < total; i += 1) {
    const tip = tips[Math.floor(rng() * tips.length)];
    v.set(rng() - 0.5, rng() - 0.35, rng() - 0.5).normalize().multiplyScalar(tip.r * Math.cbrt(rng()));
    e.set(rng() * 6, rng() * 6, rng() * 6);
    const sz = size * range(rng, 0.6, 1.3);
    place(mesh, i, tip.p.clone().add(v), e, new THREE.Vector3(sz, sz * 0.85, sz), jitterColor(accent && rng() > 0.82 ? accent : color, rng, 0.04, 0.18, 0.2));
  }
  group.add(mesh);
}

export const treeCherry: Builder = (p, rng) => {
  const height = n(p, 'height', 3.4);
  const group = new THREE.Group();
  const bark = pbr('bark', '#4a3528', 1);
  const tips: Tip[] = [];
  group.add(cyl(height * 0.034, height * 0.052, height * 0.08, bark, 0, 0, 0, 10));
  const crown = new THREE.Group();
  crown.position.y = height * 0.07;
  branches(crown, rng, height, bark, tips);
  foliage(crown, rng, tips, s(p, 'color', '#f5b6c8'), n(p, 'bloom', 0.9), height * 0.045, '#ffffff');
  group.add(crown);
  return group;
};

export const treeMaple: Builder = (p, rng) => {
  const height = n(p, 'height', 3);
  const group = new THREE.Group();
  const bark = pbr('bark', '#52392a', 1);
  const tips: Tip[] = [];
  group.add(cyl(height * 0.03, height * 0.05, height * 0.08, bark, 0, 0, 0, 10));
  const crown = new THREE.Group();
  crown.position.y = height * 0.07;
  branches(crown, rng, height, bark, tips);
  foliage(crown, rng, tips, s(p, 'color', '#c8542b'), 0.9, height * 0.05, '#e0a030');
  group.add(crown);
  return group;
};

export const treePine: Builder = (p, rng) => {
  const height = n(p, 'height', 3);
  const group = new THREE.Group();
  group.add(cyl(height * 0.025, height * 0.04, height * 0.3, pbr('bark', '#3d2c20', 1), 0, 0, 0, 8));
  const tiers = 7;
  for (let i = 0; i < tiers; i += 1) {
    const t = i / tiers;
    const radius = height * 0.3 * (1 - t * 0.85);
    const cone = new THREE.Mesh(new THREE.ConeGeometry(radius, height * 0.26, 14, 1), new THREE.MeshStandardMaterial({ color: jitterColor(s(p, 'color', '#2f5d3a'), rng, 0.03, 0.1, 0.1), roughness: 0.9, flatShading: true }));
    const pos = cone.geometry.attributes.position;
    for (let k = 0; k < pos.count; k += 1) {
      if (pos.getY(k) < 0) pos.setXYZ(k, pos.getX(k) * range(rng, 0.85, 1.12), pos.getY(k), pos.getZ(k) * range(rng, 0.85, 1.12));
    }
    cone.position.y = height * (0.2 + t * 0.62);
    cone.rotation.y = rng() * 6;
    group.add(shade(cone));
  }
  return group;
};

export const bush: Builder = (p, rng) => {
  const radius = n(p, 'radius', 0.5);
  const group = new THREE.Group();
  const clumps = 9;
  for (let i = 0; i < clumps; i += 1) {
    const a = rng() * Math.PI * 2;
    const r = radius * range(rng, 0.5, 0.9);
    const lump = ball(radius * range(rng, 0.45, 0.7), new THREE.MeshStandardMaterial({ color: jitterColor(s(p, 'color', '#4f7d3a'), rng, 0.04, 0.15, 0.18), roughness: 0.9 }), Math.cos(a) * r * 0.6, radius * range(rng, 0.35, 0.7), Math.sin(a) * r * 0.6);
    lump.scale.y = 0.8;
    group.add(lump);
  }
  const count = 60;
  const flowers = instanced(new THREE.IcosahedronGeometry(0.03, 0), new THREE.MeshStandardMaterial({ roughness: 0.6 }), count);
  const e = new THREE.Euler();
  for (let i = 0; i < count; i += 1) {
    const v = new THREE.Vector3(rng() - 0.5, Math.abs(rng() - 0.2), rng() - 0.5).normalize().multiplyScalar(radius * range(rng, 0.85, 1.05));
    place(flowers, i, new THREE.Vector3(v.x, v.y + radius * 0.2, v.z), e, new THREE.Vector3(1, 1, 1), jitterColor(s(p, 'flowers', '#e35d8f'), rng, 0.04, 0.1, 0.12));
  }
  group.add(flowers);
  return group;
};
