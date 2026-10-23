import * as THREE from 'three';
import { glow, pbr } from '../materials';
import { type Rng } from '../rng';
import { b, box, cyl, instanced, n, place, s, shade, type Builder } from './kit';

const GAUGE = 0.16;
const SPACING = 1.1;

export const rails: Builder = (p) => {
  const length = n(p, 'length', 24);
  const tracks = Math.round(n(p, 'tracks', 1));
  const group = new THREE.Group();
  const steel = pbr('metal', '#9aa0a6');
  const sleeperCount = Math.floor(length / 0.2);
  for (let t = 0; t < tracks; t += 1) {
    const z = (t - (tracks - 1) / 2) * SPACING;
    if (b(p, 'ballast', true)) group.add(box(length, 0.07, 0.62, pbr('stone', '#8d8982', Math.max(2, length / 2)), 0, 0, z, 0.02));
    const sleepers = instanced(new THREE.BoxGeometry(0.09, 0.04, 0.5), pbr('wood', '#4b3f36'), sleeperCount);
    const e = new THREE.Euler();
    for (let i = 0; i < sleeperCount; i += 1) place(sleepers, i, new THREE.Vector3(-length / 2 + 0.1 + i * 0.2, 0.09, z), e, new THREE.Vector3(1, 1, 1));
    group.add(sleepers);
    for (const side of [-1, 1]) {
      group.add(box(length, 0.06, 0.022, steel, 0, 0.1, z + side * GAUGE));
      group.add(box(length, 0.012, 0.045, steel, 0, 0.1, z + side * GAUGE));
    }
  }
  return group;
};

export const platform: Builder = (p) => {
  const length = n(p, 'length', 14);
  const width = n(p, 'width', 3);
  const height = n(p, 'height', 0.45);
  const group = new THREE.Group();
  group.add(box(length, height, width, pbr('concrete', s(p, 'color', '#b9b7ae'), Math.max(2, length / 3)), 0, 0, 0, 0.02));
  group.add(box(length, 0.035, 0.12, pbr('concrete', '#8c8a83'), 0, height, width / 2 - 0.06));
  group.add(box(length - 0.04, 0.006, 0.05, pbr('paint', '#f2c230'), 0, height + 0.035, width / 2 - 0.3));
  const dots = instanced(new THREE.CylinderGeometry(0.012, 0.012, 0.01, 6), pbr('paint', '#e9b920'), Math.floor(length / 0.07));
  const e = new THREE.Euler();
  for (let i = 0; i < Math.floor(length / 0.07); i += 1) place(dots, i, new THREE.Vector3(-length / 2 + 0.05 + i * 0.07, height + 0.038, width / 2 - 0.42), e, new THREE.Vector3(1, 1, 1));
  group.add(dots);
  group.add(box(length, 0.08, 0.3, pbr('concrete', '#a09e96'), 0, 0, -width / 2 - 0.14));
  return group;
};

function car(length: number, body: THREE.Material, stripe: THREE.Material, cab: boolean, front: number): THREE.Group {
  const g = new THREE.Group();
  const glass = pbr('glass', '#27323d');
  const height = 0.78;
  const width = 0.84;
  const y0 = 0.17;
  g.add(box(length, height, width, body, 0, y0, 0, 0.08));
  g.add(box(length + 0.002, 0.07, width + 0.004, stripe, 0, y0 + 0.2, 0, 0.02));
  g.add(box(length + 0.002, 0.03, width + 0.004, stripe, 0, y0 + 0.08, 0, 0.01));
  g.add(box(length - 0.1, 0.03, width - 0.1, pbr('paint', '#b9bdc0'), 0, y0 + height, 0, 0.012));
  g.add(box(length * 0.4, 0.08, width * 0.5, pbr('metal', '#8a9097'), -length * 0.12, y0 + height + 0.03, 0, 0.02));
  const windows = Math.max(2, Math.floor((length - (cab ? 1.1 : 0.4)) / 0.58));
  const span = (windows - 1) * 0.56;
  const offset = cab ? -front * 0.28 : 0;
  for (let i = 0; i < windows; i += 1) {
    for (const side of [-1, 1]) g.add(box(0.44, 0.26, 0.012, glass, i * 0.56 - span / 2 + offset, y0 + 0.42, side * (width / 2 + 0.004)));
  }
  for (const side of [-1, 1]) {
    for (const x of [-length / 2 + 0.55, length / 2 - 0.55]) {
      if (!cab || Math.sign(x) !== front) g.add(box(0.26, 0.5, 0.012, pbr('glass', '#3b4a56'), x, y0 + 0.14, side * (width / 2 + 0.005)));
    }
  }
  for (const x of [-length / 2 + 0.6, length / 2 - 0.6]) {
    g.add(box(0.7, 0.1, 0.6, pbr('metal', '#2a2d31'), x, 0.05, 0));
    for (const side of [-1, 1]) for (const dx of [-0.2, 0.2]) {
      const wheel = cyl(0.07, 0.07, 0.03, pbr('metal', '#1d1f22'), x + dx, 0.0, side * GAUGE, 14);
      wheel.rotation.x = Math.PI / 2;
      wheel.position.y = 0.1;
      g.add(wheel);
    }
  }
  if (cab) {
    const nose = box(0.3, height * 0.9, width * 0.96, body, front * (length / 2 + 0.08), y0 + 0.02, 0, 0.12);
    g.add(nose);
    const shield = box(0.012, 0.3, width * 0.7, glass, front * (length / 2 + 0.24), y0 + 0.42, 0);
    g.add(shield);
    for (const side of [-1, 1]) g.add(box(0.014, 0.05, 0.1, glow('#fff3c4', 3), front * (length / 2 + 0.235), y0 + 0.16, side * 0.28));
  }
  return g;
}

export const train: Builder = (p, _rng: Rng) => {
  const cars = Math.round(n(p, 'cars', 3));
  const length = n(p, 'car_length', 3.6);
  const group = new THREE.Group();
  const body = pbr('paint', s(p, 'color', '#e8e6e1'));
  const stripe = pbr('paint', s(p, 'stripe', '#2b7a4b'));
  const total = cars * (length + 0.06);
  for (let i = 0; i < cars; i += 1) {
    const unit = car(length, body, stripe, i === 0 || i === cars - 1, i === 0 ? -1 : 1);
    unit.position.x = -total / 2 + length / 2 + i * (length + 0.06);
    group.add(unit);
  }
  return shade(group);
};

export const crossing: Builder = (p) => {
  const width = n(p, 'width', 3);
  const group = new THREE.Group();
  const metal = pbr('metal', '#d9dadc');
  const red = pbr('paint', '#d93a2b');
  const white = pbr('paint', '#f4f2ea');
  const open = b(p, 'open', false);
  for (const side of [-1, 1]) {
    const post = new THREE.Group();
    post.position.set(-side * (width / 2 + 0.12), 0, side * 0.62);
    post.add(cyl(0.025, 0.03, 0.62, metal, 0, 0, 0, 10));
    post.add(box(0.12, 0.1, 0.05, pbr('paint', '#222428'), 0, 0.52, 0));
    for (const dz of [-0.03, 0.03]) post.add(shade(new THREE.Mesh(new THREE.SphereGeometry(0.025, 12, 8), glow('#ff3b2f', open ? 0.2 : 3.5)))).position.set(0, 0.55, dz);
    const arm = new THREE.Group();
    arm.position.set(0, 0.34, 0);
    const length = width / 2 + 0.05;
    const segments = 8;
    for (let i = 0; i < segments; i += 1) arm.add(box(length / segments, 0.028, 0.028, i % 2 ? white : red, 0, 0, 0));
    arm.children.forEach((c, i) => { c.position.x = side * (0.03 + (i + 0.5) * (length / segments)); });
    arm.rotation.z = open ? side * 1.1 : 0;
    post.add(arm);
    group.add(post);
  }
  return group;
};
