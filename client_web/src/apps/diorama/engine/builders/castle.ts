import * as THREE from 'three';
import { glow, pbr } from '../materials';
import { range } from '../rng';
import { ball, box, cyl, n, s, shade, type Builder } from './kit';

const masonry = (color: string, size: number) => pbr('stone', color, Math.max(1, Math.round(size)));
const dark = () => pbr('metal', '#1b1d21');
const roofTile = (color: string) => pbr('tile', color, 4);

function merlons(length: number, y: number, z: number, material: THREE.Material, step = 0.5, size = 0.28): THREE.Group {
  const group = new THREE.Group();
  const count = Math.max(2, Math.floor(length / step));
  const gap = length / count;
  for (let i = 0; i < count; i += 1) group.add(box(size, 0.3, 0.16, material, -length / 2 + gap * (i + 0.5), y, z, 0.015));
  return group;
}

function crown(radius: number, y: number, material: THREE.Material): THREE.Group {
  const group = new THREE.Group();
  const count = Math.max(8, Math.round((Math.PI * 2 * radius) / 0.42));
  for (let i = 0; i < count; i += 1) {
    const angle = (i / count) * Math.PI * 2;
    const merlon = box(0.22, 0.28, 0.14, material, Math.cos(angle) * radius, y, Math.sin(angle) * radius, 0.012);
    merlon.rotation.y = -angle + Math.PI / 2;
    group.add(merlon);
  }
  return group;
}

function pennant(color: string, size = 0.5): THREE.Mesh {
  const geometry = new THREE.PlaneGeometry(size, size * 0.55, 8, 3);
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) {
    const x = position.getX(i) + size / 2;
    position.setZ(i, Math.sin(x * 9) * 0.035 * x);
    position.setY(i, position.getY(i) * (1 - (x / size) * 0.55));
  }
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: 0.7, side: THREE.DoubleSide }));
  mesh.position.x = size / 2;
  return shade(mesh, true, false);
}

function banner(height: number, color: string): THREE.Group {
  const group = new THREE.Group();
  group.add(cyl(0.012, 0.016, height, pbr('metal', '#8c9298'), 0, 0, 0, 8));
  group.add(ball(0.03, pbr('metal', '#d4b04a'), 0, height, 0));
  const cloth = pennant(color, Math.max(0.35, height * 0.35));
  cloth.position.set(0.02 + cloth.position.x, height * 0.86, 0);
  group.add(cloth);
  return group;
}

function slits(group: THREE.Group, radius: number, heights: number[], count: number): void {
  for (const y of heights) {
    for (let i = 0; i < count; i += 1) {
      const angle = (i / count) * Math.PI * 2 + y;
      const slit = box(0.07, 0.3, 0.05, dark(), Math.cos(angle) * radius, y, Math.sin(angle) * radius);
      slit.rotation.y = -angle + Math.PI / 2;
      group.add(slit);
    }
  }
}

export const castleWall: Builder = (p, rng) => {
  const length = n(p, 'length', 8);
  const height = n(p, 'height', 2.2);
  const thick = n(p, 'thickness', 0.6);
  const color = s(p, 'color', '#b5a58d');
  const stone = masonry(color, length / 1.5);
  const group = new THREE.Group();
  group.add(box(length, height, thick, stone, 0, 0, 0, 0.02));
  group.add(box(length + 0.08, 0.28, thick + 0.16, masonry('#8d8068', 2), 0, 0, 0, 0.02));
  group.add(box(length + 0.04, 0.1, thick + 0.1, masonry('#cbbda4', 2), 0, height - 0.04, 0, 0.01));
  if (p.battlements !== false) {
    for (const side of [-1, 1]) group.add(merlons(length - 0.1, height + 0.06, side * (thick / 2 - 0.07), stone));
  }
  const spacing = Math.max(1.4, length / Math.max(2, Math.round(length / 1.7)));
  for (let x = -length / 2 + spacing / 2; x < length / 2; x += spacing) {
    for (const side of [-1, 1]) group.add(box(0.07, 0.34, 0.03, dark(), x + range(rng, -0.05, 0.05), height * 0.52, side * (thick / 2 + 0.005)));
  }
  return group;
};

export const towerRound: Builder = (p, rng) => {
  const radius = n(p, 'radius', 1.1);
  const height = n(p, 'height', 4);
  const color = s(p, 'color', '#b9a98f');
  const roofed = p.roofed !== false;
  const stone = masonry(color, radius * 3);
  const group = new THREE.Group();
  group.add(cyl(radius * 1.12, radius * 1.22, 0.4, masonry('#8d8068', 3), 0, 0, 0, 28));
  group.add(cyl(radius, radius * 1.04, height, stone, 0, 0.35, 0, 32));
  for (const y of [height * 0.38, height * 0.72]) group.add(cyl(radius * 1.03, radius * 1.03, 0.07, masonry('#cbbda4', 2), 0, y, 0, 32));
  slits(group, radius * 1.01, [height * 0.3, height * 0.55, height * 0.8], 3);
  const top = height + 0.35;
  group.add(cyl(radius * 1.14, radius * 1.02, 0.26, stone, 0, top - 0.2, 0, 32));
  if (roofed) {
    group.add(cyl(radius * 1.2, radius * 1.14, 0.08, masonry('#8d8068', 2), 0, top + 0.05, 0, 32));
    const cone = new THREE.Mesh(new THREE.ConeGeometry(radius * 1.32, radius * 2.1, 32), roofTile(s(p, 'roof', '#8c3a2c')));
    cone.position.y = top + 0.13 + radius * 1.05;
    group.add(shade(cone));
    const flag = banner(Math.max(0.7, radius * 0.9), '#b3202e');
    flag.position.y = top + 0.13 + radius * 2.05;
    group.add(flag);
    const window = box(0.16, 0.26, 0.05, glow('#ffd58a', 0.9), 0, top - 0.5, radius * 1.01);
    group.add(window);
  } else {
    group.add(cyl(radius * 0.96, radius * 0.96, 0.05, masonry('#7c7164', 2), 0, top - 0.04, 0, 32));
    group.add(crown(radius * 1.08, top - 0.07, stone));
  }
  group.rotation.y = range(rng, 0, Math.PI * 2);
  return group;
};

export const keep: Builder = (p) => {
  const w = n(p, 'w', 7);
  const d = n(p, 'd', 6);
  const h = n(p, 'h', 4.2);
  const color = s(p, 'color', '#b3a38b');
  const stone = masonry(color, w / 1.5);
  const group = new THREE.Group();
  group.add(box(w + 0.2, 0.3, d + 0.2, masonry('#8d8068', 3), 0, 0, 0, 0.02));
  group.add(box(w, h, d, stone, 0, 0.3, 0, 0.03));
  group.add(box(w + 0.16, 0.1, d + 0.16, masonry('#cbbda4', 2), 0, h + 0.26, 0, 0.01));
  for (const side of [-1, 1]) {
    group.add(merlons(w - 0.2, h + 0.38, side * (d / 2 - 0.1), stone, 0.55));
    const end = merlons(d - 0.2, h + 0.38, side * (w / 2 - 0.1), stone, 0.55);
    end.rotation.y = Math.PI / 2;
    group.add(end);
  }
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    group.add(box(0.8, h + 0.7, 0.8, stone, sx * (w / 2), 0.3, sz * (d / 2), 0.03));
    group.add(box(0.92, 0.14, 0.92, masonry('#cbbda4', 2), sx * (w / 2), h + 0.96, sz * (d / 2), 0.01));
  }
  const upperW = w * 0.58;
  const upperD = d * 0.58;
  const upperH = h * 0.5;
  group.add(box(upperW, upperH, upperD, stone, 0, h + 0.36, 0, 0.03));
  const roof = new THREE.Mesh(new THREE.ConeGeometry(Math.max(upperW, upperD) * 0.78, upperH * 0.9, 4), roofTile(s(p, 'roof', '#6d3a30')));
  roof.rotation.y = Math.PI / 4;
  roof.position.y = h + 0.36 + upperH + upperH * 0.45;
  group.add(shade(roof));
  const flag = banner(1.1, '#b3202e');
  flag.position.y = h + 0.36 + upperH + upperH * 0.9;
  group.add(flag);
  const columns = Math.max(2, Math.round(w / 2));
  for (const [face, span] of [[d / 2 + 0.02, w], [-d / 2 - 0.02, w]] as const) {
    for (let i = 0; i < columns; i += 1) {
      const x = -span / 2 + (span / columns) * (i + 0.5);
      for (const y of [h * 0.35, h * 0.7]) {
        group.add(box(0.26, 0.5, 0.04, pbr('stone', '#d9ccb2', 1), x, y + 0.3, face));
        group.add(box(0.18, 0.42, 0.05, glow('#ffd58a', 0.35), x, y + 0.34, face + Math.sign(face) * 0.01));
      }
    }
  }
  const door = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.06, 20, 1, false, 0, Math.PI), pbr('wood', '#3f2a1a', 1));
  door.rotation.x = Math.PI / 2;
  door.position.set(0, 0.3 + 0.9, d / 2 + 0.02);
  group.add(shade(door));
  group.add(box(0.84, 0.9, 0.06, pbr('wood', '#3f2a1a', 1), 0, 0.3, d / 2 + 0.02));
  return group;
};

export const gatehouse: Builder = (p) => {
  const width = n(p, 'width', 3.4);
  const height = n(p, 'height', 3.2);
  const color = s(p, 'color', '#b5a58d');
  const stone = masonry(color, 3);
  const group = new THREE.Group();
  const tower = 1.3;
  const opening = width * 0.5;
  for (const side of [-1, 1]) {
    const x = side * (opening / 2 + tower / 2);
    group.add(box(tower, height + 0.5, 1.7, stone, x, 0, 0, 0.03));
    const crownBar = merlons(tower, height + 0.5, 0.7, stone, 0.46);
    crownBar.position.x = x;
    group.add(crownBar);
    const back = merlons(tower, height + 0.5, -0.7, stone, 0.46);
    back.position.x = x;
    group.add(back);
    group.add(box(0.07, 0.34, 0.03, dark(), x, height * 0.6, 0.86));
  }
  const lintelH = height * 0.36;
  group.add(box(opening + 0.1, lintelH, 1.7, stone, 0, height * 0.64 + 0.5 - lintelH + lintelH * 0.0, 0, 0.02));
  const archY = height * 0.62;
  const arch = new THREE.Mesh(new THREE.CylinderGeometry(opening / 2, opening / 2, 1.76, 24, 1, false, 0, Math.PI), dark());
  arch.rotation.z = Math.PI / 2;
  arch.rotation.y = Math.PI / 2;
  arch.rotation.x = Math.PI / 2;
  arch.position.set(0, archY, 0);
  group.add(shade(arch));
  group.add(box(opening, archY, 1.76, dark(), 0, 0, 0));
  for (let i = 0; i < 7; i += 1) group.add(box(0.03, archY + opening / 2 - 0.2, 0.03, pbr('metal', '#4a4e54'), -opening / 2 + 0.12 + (i * (opening - 0.24)) / 6, 0.15, 0.78));
  const flag = banner(1, '#b3202e');
  flag.position.set(0, height + 0.5 + 0.05, 0);
  group.add(flag);
  return group;
};

export const drawbridge: Builder = (p) => {
  const length = n(p, 'length', 3);
  const width = n(p, 'width', 1.4);
  const wood = pbr('wood', '#6b4a2e', 1);
  const group = new THREE.Group();
  const planks = Math.max(4, Math.round(length / 0.16));
  for (let i = 0; i < planks; i += 1) group.add(box(width, 0.05, (length / planks) * 0.92, wood, 0, 0.04, (i + 0.5) * (length / planks), 0.006));
  for (const side of [-1, 1]) {
    group.add(box(0.07, 0.07, length, pbr('wood', '#4a331f', 1), side * (width / 2), 0.04, length / 2));
    for (let i = 0; i <= 3; i += 1) group.add(cyl(0.02, 0.02, 0.38, pbr('wood', '#4a331f', 1), side * (width / 2), 0.1, (i * length) / 3, 8));
    group.add(box(0.04, 0.04, length, pbr('wood', '#4a331f', 1), side * (width / 2), 0.46, length / 2));
  }
  return group;
};

export const moat: Builder = (p) => {
  const w = n(p, 'w', 14);
  const d = n(p, 'd', 12);
  const ring = n(p, 'ring', 1.4);
  const color = s(p, 'color', '#3f7f93');
  const group = new THREE.Group();
  const water = new THREE.MeshPhysicalMaterial({ color, roughness: 0.05, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.04, envMapIntensity: 1.6, transparent: true, opacity: 0.92 });
  const edge = masonry('#8d8068', 3);
  const strips: [number, number, number, number][] = [
    [w + ring * 2, ring, 0, -(d / 2 + ring / 2)], [w + ring * 2, ring, 0, d / 2 + ring / 2],
    [ring, d, -(w / 2 + ring / 2), 0], [ring, d, w / 2 + ring / 2, 0],
  ];
  for (const [sw, sd, x, z] of strips) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(sw, 0.06, sd), water);
    mesh.position.set(x, 0.04, z);
    mesh.receiveShadow = true;
    group.add(mesh);
  }
  for (const side of [-1, 1]) {
    group.add(box(w + ring * 2 + 0.3, 0.14, 0.14, edge, 0, 0, side * (d / 2 + ring + 0.07), 0.02));
    group.add(box(0.14, 0.14, d + 0.3, edge, side * (w / 2 + ring + 0.07), 0, 0, 0.02));
    group.add(box(w + 0.3, 0.14, 0.14, edge, 0, 0, side * (d / 2 - 0.07), 0.02));
    group.add(box(0.14, 0.14, d - 0.3, edge, side * (w / 2 - 0.07), 0, 0, 0.02));
  }
  return group;
};

export const flag: Builder = (p) => banner(n(p, 'height', 1.6), s(p, 'color', '#b3202e'));

export const hill: Builder = (p, rng) => {
  const radius = n(p, 'radius', 5);
  const height = n(p, 'height', 1.6);
  const profile: THREE.Vector2[] = [];
  const rings = 16;
  for (let i = 0; i <= rings; i += 1) {
    const t = i / rings;
    profile.push(new THREE.Vector2(Math.max(0.001, radius * (1 - t)), height * Math.pow(Math.sin(t * Math.PI * 0.5), 0.9)));
  }
  const geometry = new THREE.LatheGeometry(profile, 56);
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i += 1) {
    const x = position.getX(i);
    const z = position.getZ(i);
    const falloff = Math.min(1, Math.hypot(x, z) / radius);
    position.setY(i, position.getY(i) + (Math.sin(x * 1.3 + z * 0.7) * 0.5 + Math.sin(z * 2.1) * 0.5) * 0.06 * height * (1 - falloff) + range(rng, -0.01, 0.01));
  }
  geometry.computeVertexNormals();
  const group = new THREE.Group();
  group.add(shade(new THREE.Mesh(geometry, pbr('grass', s(p, 'color', '#6f9a3c'), 5))));
  return group;
};
