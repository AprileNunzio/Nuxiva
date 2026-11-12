import * as THREE from 'three';
import { glow, pbr } from '../materials';
import { ball, board, box, cyl, n, s, shade, b, type Builder } from './kit';

export const lamp: Builder = (p, _rng, ctx) => {
  const height = n(p, 'height', 2);
  const group = new THREE.Group();
  const metal = pbr('metal', s(p, 'color', '#454a50'));
  group.add(cyl(0.05, 0.07, 0.12, metal, 0, 0, 0, 12));
  group.add(cyl(0.022, 0.03, height, metal, 0, 0.1, 0, 10));
  group.add(box(0.28, 0.02, 0.025, metal, 0.12, height + 0.06, 0));
  const lit = b(p, 'lit', true);
  group.add(box(0.2, 0.05, 0.1, pbr('paint', '#2d3135'), 0.26, height + 0.04, 0, 0.01));
  group.add(box(0.18, 0.02, 0.08, glow('#ffe7a8', lit ? 4 : 0.15), 0.26, height + 0.015, 0));
  if (lit && ctx.lamps.left > 0) {
    ctx.lamps.left -= 1;
    const light = new THREE.PointLight('#ffd58a', 0, 3.2, 1.6);
    light.userData.night = 2.2;
    light.position.set(0.26, height - 0.1, 0);
    group.add(light);
  }
  return group;
};

export const bench: Builder = (p) => {
  const length = n(p, 'length', 1.2);
  const group = new THREE.Group();
  const wood = pbr('wood', s(p, 'color', '#8a5a35'), 1);
  const metal = pbr('metal', '#33373c');
  for (let i = 0; i < 3; i += 1) group.add(box(length, 0.025, 0.06, wood, 0, 0.26, -0.1 + i * 0.075, 0.006));
  for (let i = 0; i < 3; i += 1) {
    const slat = box(length, 0.06, 0.02, wood, 0, 0.36 + i * 0.075, -0.17, 0.006);
    slat.rotation.x = -0.18;
    group.add(slat);
  }
  for (const x of [-length / 2 + 0.07, length / 2 - 0.07]) {
    group.add(box(0.025, 0.28, 0.025, metal, x, 0, -0.12));
    group.add(box(0.025, 0.28, 0.025, metal, x, 0, 0.1));
    group.add(box(0.025, 0.02, 0.32, metal, x, 0.26, -0.03));
    group.add(box(0.025, 0.35, 0.025, metal, x, 0.26, -0.19));
  }
  return group;
};

export const fence: Builder = (p) => {
  const length = n(p, 'length', 6);
  const height = n(p, 'height', 0.8);
  const material = pbr(s(p, 'material', 'metal'), s(p, 'color', '#5b6168'), 1);
  const group = new THREE.Group();
  const posts = Math.max(2, Math.round(length / 1.0) + 1);
  const gap = length / (posts - 1);
  for (let i = 0; i < posts; i += 1) group.add(box(0.05, height, 0.05, material, -length / 2 + i * gap, 0, 0));
  group.add(box(length, 0.035, 0.04, material, 0, height - 0.04, 0));
  group.add(box(length, 0.03, 0.03, material, 0, height * 0.35, 0));
  const bars = Math.round(length / 0.12);
  for (let i = 0; i <= bars; i += 1) group.add(box(0.014, height * 0.9, 0.014, material, -length / 2 + (i * length) / bars, 0, 0));
  return group;
};

export const vending: Builder = (p) => {
  const group = new THREE.Group();
  const body = pbr('paint', s(p, 'color', '#c0392b'));
  group.add(box(0.42, 0.72, 0.3, body, 0, 0, 0, 0.02));
  group.add(box(0.32, 0.42, 0.012, glow('#fdfcf2', 1.1), -0.03, 0.22, 0.156));
  const rows = 4;
  for (let r = 0; r < rows; r++) for (let c = 0; c < 5; c++) {
    group.add(box(0.034, 0.07, 0.018, pbr('plastic', ['#e74c3c', '#2ecc71', '#3498db', '#f1c40f', '#ecf0f1'][(r + c) % 5]), -0.15 + c * 0.057, 0.34 + r * 0.1 - 0.05, 0.165));
  }
  group.add(box(0.07, 0.3, 0.012, pbr('metal', '#2e3135'), 0.155, 0.28, 0.156));
  group.add(box(0.2, 0.08, 0.012, pbr('metal', '#1d1f22'), -0.03, 0.06, 0.156));
  return group;
};

export const sign: Builder = (p) => {
  const height = n(p, 'height', 1.4);
  const group = new THREE.Group();
  group.add(cyl(0.015, 0.018, height, pbr('metal', '#8c9298'), 0, 0, 0, 10));
  const panel = board(0.62, 0.2, s(p, 'text', 'PLATFORM 1'), '#ffffff', s(p, 'color', '#1b5fa6'));
  panel.position.set(0, height - 0.04, 0.03);
  group.add(panel);
  return group;
};

export const person: Builder = (p, rng) => {
  const height = n(p, 'height', 0.75);
  const k = height / 0.75;
  const group = new THREE.Group();
  const cloth = new THREE.MeshStandardMaterial({ color: s(p, 'color', '#3b6ea5'), roughness: 0.8 });
  const pants = new THREE.MeshStandardMaterial({ color: ['#2a2f3a', '#3a3a3a', '#4b4033'][Math.floor(rng() * 3)], roughness: 0.85 });
  const skin = new THREE.MeshStandardMaterial({ color: ['#e8c4a0', '#d9a77f', '#c68e66'][Math.floor(rng() * 3)], roughness: 0.65 });
  const hair = new THREE.MeshStandardMaterial({ color: ['#1c1a19', '#3a2a1e', '#6b5a43'][Math.floor(rng() * 3)], roughness: 0.9 });
  for (const side of [-1, 1]) group.add(cyl(0.035 * k, 0.03 * k, 0.34 * k, pants, side * 0.04 * k, 0.02 * k, 0, 10));
  group.add(cyl(0.07 * k, 0.08 * k, 0.3 * k, cloth, 0, 0.34 * k, 0, 14));
  for (const side of [-1, 1]) {
    const arm = cyl(0.022 * k, 0.02 * k, 0.28 * k, cloth, side * 0.105 * k, 0.37 * k, 0, 8);
    arm.rotation.z = side * 0.06;
    group.add(arm);
    group.add(ball(0.022 * k, skin, side * 0.115 * k, 0.36 * k, 0));
  }
  group.add(ball(0.055 * k, skin, 0, 0.7 * k, 0));
  const cap = ball(0.058 * k, hair, 0, 0.714 * k, -0.006 * k);
  cap.scale.set(1, 0.72, 1);
  group.add(cap);
  return shade(group);
};

export const car: Builder = (p) => {
  const group = new THREE.Group();
  const paint = pbr('paint', s(p, 'color', '#d9d9d9'));
  const glass = pbr('glass', '#2b3640');
  group.add(box(1.5, 0.28, 0.68, paint, 0, 0.1, 0, 0.08));
  group.add(box(0.86, 0.26, 0.6, paint, -0.08, 0.36, 0, 0.1));
  group.add(box(0.8, 0.2, 0.62, glass, -0.08, 0.39, 0, 0.06));
  for (const x of [-0.5, 0.5]) for (const z of [-0.33, 0.33]) {
    const wheel = cyl(0.12, 0.12, 0.09, pbr('metal', '#16181a'), x, 0, z, 18);
    wheel.rotation.x = Math.PI / 2;
    wheel.position.y = 0.12;
    group.add(wheel);
  }
  for (const z of [-0.24, 0.24]) group.add(box(0.02, 0.05, 0.1, glow('#fff3c4', 2.5), 0.75, 0.22, z));
  return shade(group);
};
