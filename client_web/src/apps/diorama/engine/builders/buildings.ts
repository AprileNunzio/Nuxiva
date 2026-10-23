import * as THREE from 'three';
import { glow, pbr } from '../materials';
import { board, box, cyl, gableRoof, n, s, shade, type Builder } from './kit';

function windows(group: THREE.Group, w: number, h: number, z: number, count: number, frame: THREE.Material, glass: THREE.Material, back = false): void {
  const step = w / count;
  for (let i = 0; i < count; i += 1) {
    const x = -w / 2 + step * (i + 0.5);
    const sign = back ? -1 : 1;
    group.add(box(step * 0.62, h * 0.34, 0.03, frame, x, h * 0.42, z * sign));
    group.add(box(step * 0.54, h * 0.28, 0.034, glass, x, h * 0.45, z * sign));
    group.add(box(0.015, h * 0.28, 0.04, frame, x, h * 0.45, z * sign));
  }
}

export const stationBuilding: Builder = (p) => {
  const w = n(p, 'w', 7);
  const d = n(p, 'd', 4);
  const h = n(p, 'h', 3);
  const style = s(p, 'style', 'japanese');
  const group = new THREE.Group();
  const wall = pbr(style === 'wood' ? 'wood' : 'concrete', s(p, 'wall', '#d9d2c3'), 2);
  const roof = pbr('tile', s(p, 'roof', '#3c4a57'), 4);
  const frame = pbr('metal', '#3a3f45');
  const glass = pbr('glass', '#9fc3d6');
  group.add(box(w + 0.1, 0.18, d + 0.1, pbr('concrete', '#8f8c85'), 0, 0, 0, 0.02));
  group.add(box(w, h, d, wall, 0, 0.18, 0, 0.02));
  const front = d / 2 + 0.018;
  windows(group, w, h, front, Math.max(2, Math.round(w / 1.6)), frame, glass);
  windows(group, w, h, -front, Math.max(2, Math.round(w / 1.6)), frame, glass, true);
  const doorW = Math.min(1.5, w * 0.25);
  group.add(box(doorW + 0.1, h * 0.62, 0.05, frame, 0, 0.18, front));
  group.add(box(doorW, h * 0.58, 0.056, glass, 0, 0.2, front));
  group.add(box(0.02, h * 0.58, 0.06, frame, 0, 0.2, front));
  if (style === 'modern') {
    group.add(box(w + 0.5, 0.14, d + 0.5, pbr('concrete', '#6e737a'), 0, h + 0.18, 0, 0.02));
    group.add(box(w + 0.5, 0.12, 0.08, pbr('metal', '#caced2'), 0, h + 0.32, d / 2 + 0.25));
  } else {
    const lift = new THREE.Group();
    lift.position.y = h + 0.18;
    lift.add(gableRoof(w, d, Math.min(1.5, h * 0.55), roof, 0.42));
    group.add(lift);
    const eave = box(doorW + 1.2, 0.05, 0.7, roof, 0, h * 0.7, front + 0.34);
    eave.rotation.x = 0.16;
    group.add(eave);
    for (const side of [-1, 1]) group.add(cyl(0.035, 0.035, h * 0.52, pbr('wood', '#5a3f2a'), side * (doorW / 2 + 0.55), 0.18, front + 0.62, 10));
  }
  const sign = board(Math.min(3.4, w * 0.5), 0.46, s(p, 'sign', 'SAKURA'), '#f4f1e8', '#1f3a5f');
  sign.position.set(0, h * 0.82 + 0.18, front + (style === 'modern' ? 0.04 : 0.06));
  group.add(sign);
  group.add(box(0.24, 0.5, 0.12, glow('#fff0c0', 1.2), -doorW / 2 - 0.45, h * 0.5, front + 0.07));
  group.add(box(0.5, 0.3, 0.4, pbr('metal', '#c8ccd0'), w / 2 - 0.5, h + 0.18, -d / 4));
  return group;
};

export const canopy: Builder = (p) => {
  const length = n(p, 'length', 10);
  const width = n(p, 'width', 3.4);
  const height = n(p, 'height', 2.4);
  const group = new THREE.Group();
  const roof = box(length, 0.07, width, pbr('paint', s(p, 'color', '#cfd3d6')), 0, height, 0, 0.02);
  roof.rotation.x = 0.03;
  group.add(roof);
  group.add(box(length + 0.04, 0.16, 0.06, pbr('paint', '#f1f3f4'), 0, height - 0.06, width / 2));
  const metal = pbr('metal', '#9da3a8');
  const columns = Math.max(2, Math.round(length / 2.4) + 1);
  for (let i = 0; i < columns; i += 1) {
    const x = -length / 2 + 0.2 + (i * (length - 0.4)) / (columns - 1);
    group.add(cyl(0.035, 0.04, height, metal, x, 0, width / 2 - 0.25, 12));
    group.add(box(0.08, 0.06, width * 0.92, metal, x, height - 0.06, 0));
    group.add(box(0.28, 0.02, 0.1, glow('#fffaf0', 1.4), x + 0.4, height - 0.075, 0));
  }
  return group;
};

export const footbridge: Builder = (p) => {
  const length = n(p, 'length', 9);
  const height = n(p, 'height', 3.2);
  const group = new THREE.Group();
  const paint = pbr('paint', s(p, 'color', '#d8d4cb'));
  const dark = pbr('metal', '#4a4f55');
  const glass = pbr('glass', '#9fc3d6');
  const w = 0.9;
  group.add(box(length, 0.12, w, pbr('concrete', '#8e8b84'), 0, height, 0, 0.02));
  for (const side of [-1, 1]) {
    group.add(box(length, 0.55, 0.04, paint, 0, height + 0.12, side * (w / 2)));
    group.add(box(length - 0.1, 0.42, 0.03, glass, 0, height + 0.67, side * (w / 2)));
    group.add(box(length, 0.05, 0.06, dark, 0, height + 1.09, side * (w / 2)));
  }
  const roof = box(length + 0.3, 0.05, w + 0.3, pbr('tile', '#3c4a57', 4), 0, height + 1.1, 0);
  group.add(roof);
  for (const x of [-length / 2 + 0.5, length / 2 - 0.5]) {
    for (const side of [-1, 1]) group.add(cyl(0.05, 0.06, height, paint, x + side * 0.0, 0, side * (w / 2 - 0.02), 12));
  }
  const steps = 14;
  const run = 2.6;
  for (const end of [-1, 1]) {
    for (let i = 0; i < steps; i += 1) {
      const t = i / steps;
      group.add(box(run / steps + 0.01, 0.05, w - 0.1, pbr('concrete', '#a8a59d'), end * (length / 2 + run * (1 - t) - run / steps / 2 + 0.08), height * t, 0));
    }
    const stringer = box(Math.hypot(run, height), 0.07, 0.04, dark, 0, 0, 0);
    for (const side of [-1, 1]) {
      const rail = stringer.clone();
      rail.position.set(end * (length / 2 + run / 2), height / 2 + 0.2, side * (w / 2 - 0.02));
      rail.rotation.z = -end * Math.atan2(height, run);
      group.add(rail);
    }
  }
  return shade(group);
};

export const house: Builder = (p) => {
  const w = n(p, 'w', 3.2);
  const d = n(p, 'd', 2.8);
  const h = n(p, 'h', 1.9);
  const group = new THREE.Group();
  const wall = pbr('concrete', s(p, 'wall', '#e4dccb'), 2);
  group.add(box(w + 0.08, 0.14, d + 0.08, pbr('concrete', '#8f8c85'), 0, 0, 0));
  group.add(box(w, h, d, wall, 0, 0.14, 0, 0.02));
  const lift = new THREE.Group();
  lift.position.y = h + 0.14;
  lift.add(gableRoof(w, d, h * 0.45, pbr('tile', s(p, 'roof', '#4f5b66'), 4), 0.3));
  group.add(lift);
  const glass = pbr('glass', '#a9cadb');
  const frame = pbr('paint', '#f3f1ea');
  for (const x of [-w * 0.28, w * 0.28]) {
    group.add(box(0.5, 0.52, 0.04, frame, x, h * 0.4, d / 2 + 0.005));
    group.add(box(0.42, 0.44, 0.045, glass, x, h * 0.4 + 0.04, d / 2 + 0.008));
  }
  group.add(box(0.46, 0.9, 0.05, pbr('wood', '#6a4630'), 0, 0.14, d / 2 + 0.01));
  group.add(box(0.36, 0.5, 0.2, pbr('concrete', '#c7c3b8'), w / 2 - 0.45, h + 0.4, -0.2));
  return group;
};
