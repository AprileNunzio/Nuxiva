import * as THREE from 'three';
import { pbr } from '../materials';
import { range } from '../rng';
import { box, instanced, jitterColor, n, place, s, shade, type Builder } from './kit';


export const grassPatch: Builder = (p, rng) => {
  const w = n(p, 'w', 8);
  const d = n(p, 'd', 6);
  const density = n(p, 'density', 0.7);
  const color = s(p, 'color', '#6f9a3c');
  const group = new THREE.Group();
  group.add(box(w, 0.05, d, pbr('grass', new THREE.Color(color).multiplyScalar(0.72).getStyle(), Math.max(2, w / 3)), 0, 0, 0, 0.01));
  const blades = Math.min(9000, Math.round(w * d * 260 * density));
  const blade = new THREE.ConeGeometry(0.014, 0.17, 3);
  blade.translate(0, 0.085, 0);
  const mesh = instanced(blade, new THREE.MeshStandardMaterial({ roughness: 0.85, side: THREE.DoubleSide }), blades);
  mesh.castShadow = false;
  const q = new THREE.Euler();
  for (let i = 0; i < blades; i += 1) {
    q.set(range(rng, -0.35, 0.35), range(rng, 0, Math.PI * 2), range(rng, -0.35, 0.35));
    const h = range(rng, 0.6, 1.7);
    place(mesh, i, new THREE.Vector3(range(rng, -w / 2, w / 2), 0.045, range(rng, -d / 2, d / 2)), q, new THREE.Vector3(range(rng, 0.8, 1.4), h, range(rng, 0.8, 1.4)), jitterColor(color, rng, 0.05, 0.2, 0.18));
  }
  group.add(mesh);
  const flowerColor = s(p, 'flowers', '#f4d35e');
  const count = Math.min(400, Math.round(w * d * 5 * density));
  const petals = instanced(new THREE.IcosahedronGeometry(0.022, 0), new THREE.MeshStandardMaterial({ roughness: 0.7 }), count);
  for (let i = 0; i < count; i += 1) {
    place(petals, i, new THREE.Vector3(range(rng, -w / 2, w / 2), 0.1 + rng() * 0.05, range(rng, -d / 2, d / 2)), new THREE.Euler(), new THREE.Vector3(1, 0.6, 1), jitterColor(rng() > 0.7 ? '#ffffff' : flowerColor, rng, 0.04, 0.1, 0.1));
  }
  group.add(petals);
  return group;
};

export const path: Builder = (p) => {
  const material = s(p, 'material', 'concrete');
  const w = n(p, 'w', 6);
  const d = n(p, 'd', 1.4);
  return box(w, 0.07, d, pbr(material, s(p, 'color', '#a9a79f'), Math.max(2, w / 2)), 0, 0, 0, 0.015);
};

export const rock: Builder = (p, rng) => {
  const radius = n(p, 'radius', 0.6);
  const geometry = new THREE.DodecahedronGeometry(radius, 1);
  const position = geometry.attributes.position;
  const v = new THREE.Vector3();
  for (let i = 0; i < position.count; i += 1) {
    v.fromBufferAttribute(position, i);
    v.multiplyScalar(0.82 + rng() * 0.36);
    position.setXYZ(i, v.x, v.y, v.z);
  }
  geometry.computeVertexNormals();
  const material = pbr('stone', jitterColor(s(p, 'color', '#8b8a84'), rng).getStyle(), 1);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.scale.set(1, 0.68, range(rng, 0.8, 1.15));
  mesh.position.y = radius * 0.45;
  mesh.rotation.y = rng() * Math.PI;
  return shade(mesh);
};

export const pond: Builder = (p, rng) => {
  const w = n(p, 'w', 4);
  const d = n(p, 'd', 3);
  const group = new THREE.Group();
  const shape = new THREE.Shape();
  shape.absellipse(0, 0, w / 2, d / 2, 0, Math.PI * 2, false, 0);
  const water = new THREE.Mesh(
    new THREE.ShapeGeometry(shape, 48),
    new THREE.MeshPhysicalMaterial({ color: s(p, 'color', '#4a8fa8'), roughness: 0.04, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.8, transparent: true, opacity: 0.9 }),
  );
  water.rotation.x = -Math.PI / 2;
  water.position.y = 0.075;
  water.receiveShadow = true;
  group.add(water);
  const stones = Math.round((w + d) * 3.2);
  for (let i = 0; i < stones; i += 1) {
    const a = (i / stones) * Math.PI * 2;
    const r = 0.1 + rng() * 0.13;
    const stone = new THREE.Mesh(new THREE.DodecahedronGeometry(r, 0), pbr('stone', jitterColor('#8b8a84', rng).getStyle(), 1));
    stone.position.set(Math.cos(a) * (w / 2 + r * 0.3), r * 0.5, Math.sin(a) * (d / 2 + r * 0.3));
    stone.scale.y = 0.65;
    stone.rotation.set(rng(), rng() * 6, rng());
    group.add(shade(stone));
  }
  return group;
};

export const petals: Builder = (p, rng) => {
  const w = n(p, 'w', 6);
  const d = n(p, 'd', 4);
  const count = Math.round(n(p, 'count', 220));
  const color = s(p, 'color', '#f7c5d3');
  const mesh = instanced(new THREE.CircleGeometry(0.035, 5), new THREE.MeshStandardMaterial({ roughness: 0.7, side: THREE.DoubleSide }), count);
  mesh.castShadow = false;
  const e = new THREE.Euler();
  for (let i = 0; i < count; i += 1) {
    e.set(-Math.PI / 2 + range(rng, -0.2, 0.2), 0, range(rng, 0, Math.PI * 2));
    const clump = Math.pow(rng(), 1.4);
    place(mesh, i, new THREE.Vector3(range(rng, -w / 2, w / 2) * (0.4 + clump), 0.078 + rng() * 0.012, range(rng, -d / 2, d / 2)), e, new THREE.Vector3(range(rng, 0.7, 1.5), range(rng, 0.7, 1.4), 1), jitterColor(color, rng, 0.03, 0.15, 0.14));
  }
  return mesh;
};

export const road: Builder = (p) => {
  const length = n(p, 'length', 14);
  const width = n(p, 'width', 2.4);
  const group = new THREE.Group();
  group.add(box(length, 0.06, width, pbr('asphalt', '#4b4d52', Math.max(2, length / 3)), 0, 0, 0, 0.01));
  const line = pbr('paint', '#eceae0');
  for (let x = -length / 2 + 0.5; x < length / 2 - 0.3; x += 0.9) group.add(box(0.45, 0.004, 0.05, line, x, 0.06));
  group.add(box(length, 0.004, 0.035, line, 0, 0.06, width / 2 - 0.1));
  group.add(box(length, 0.004, 0.035, line, 0, 0.06, -width / 2 + 0.1));
  group.add(box(length, 0.1, 0.08, pbr('concrete', '#b8b5ac'), 0, 0, width / 2 + 0.04));
  group.add(box(length, 0.1, 0.08, pbr('concrete', '#b8b5ac'), 0, 0, -width / 2 - 0.04));
  return group;
};

export const block: Builder = (p) =>
  box(n(p, 'w', 1), n(p, 'h', 1), n(p, 'd', 1), pbr(s(p, 'material', 'concrete'), s(p, 'color', '#b0b0b0'), 1.5), 0, 0, 0, 0.012);

export const cylinder: Builder = (p) =>
  shade(new THREE.Mesh(new THREE.CylinderGeometry(n(p, 'top', 0.5), n(p, 'radius', 0.5), n(p, 'h', 1), 36), pbr(s(p, 'material', 'concrete'), s(p, 'color', '#b0b0b0'), 1.5))).translateY(n(p, 'h', 1) / 2);

