import * as THREE from 'three';
import type { Recipe } from '../../types';
import { pbr } from '../materials';
import { box, shade, s, type Builder } from './kit';

export function learnedBuilder(recipe: Recipe): Builder {
  return (p) => {
    const tint = s(p, 'color', '#b0b0b0');
    const group = new THREE.Group();
    for (const part of recipe.parts) {
      const material = pbr(part.material, part.tint ? tint : part.color, 1.5);
      let mesh: THREE.Mesh;
      if (part.shape === 'box') {
        mesh = box(part.w, part.h, part.d, material, part.x, part.y, part.z, 0.01);
      } else if (part.shape === 'sphere') {
        mesh = shade(new THREE.Mesh(new THREE.SphereGeometry(part.r, 20, 14), material));
        mesh.position.set(part.x, part.y + part.r, part.z);
      } else {
        const top = part.shape === 'cone' ? 0 : part.r2;
        mesh = shade(new THREE.Mesh(new THREE.CylinderGeometry(top, part.r, part.h, 24), material));
        mesh.position.set(part.x, part.y + part.h / 2, part.z);
      }
      mesh.rotation.y = THREE.MathUtils.degToRad(part.rot);
      group.add(mesh);
    }
    return group;
  };
}
