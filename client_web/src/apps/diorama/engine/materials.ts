import * as THREE from 'three';
import { surface, type Surface } from './textures';

interface Spec {
  readonly surface: Surface;
  readonly rough: number;
  readonly metal: number;
  readonly bump: number;
  readonly repeat: number;
}

const SPECS: Record<string, Spec> = {
  concrete: { surface: 'concrete', rough: 0.92, metal: 0, bump: 0.5, repeat: 1.5 }, wood: { surface: 'wood', rough: 0.78, metal: 0, bump: 0.7, repeat: 1.2 },
  metal: { surface: 'metal', rough: 0.38, metal: 0.85, bump: 0.15, repeat: 1 }, plastic: { surface: 'plain', rough: 0.45, metal: 0, bump: 0, repeat: 1 },
  brick: { surface: 'brick', rough: 0.88, metal: 0, bump: 1.2, repeat: 1 }, tile: { surface: 'tile', rough: 0.35, metal: 0.05, bump: 1.4, repeat: 2 },
  glass: { surface: 'plain', rough: 0.05, metal: 0, bump: 0, repeat: 1 }, grass: { surface: 'grass', rough: 0.95, metal: 0, bump: 0.8, repeat: 3 },
  soil: { surface: 'soil', rough: 0.98, metal: 0, bump: 1.4, repeat: 2 }, asphalt: { surface: 'asphalt', rough: 0.96, metal: 0, bump: 0.9, repeat: 2 },
  paint: { surface: 'plain', rough: 0.4, metal: 0.1, bump: 0, repeat: 1 }, stone: { surface: 'stone', rough: 0.85, metal: 0, bump: 1.1, repeat: 1.5 },
  bark: { surface: 'bark', rough: 0.95, metal: 0, bump: 1.6, repeat: 1 }, foliage: { surface: 'plain', rough: 0.85, metal: 0, bump: 0, repeat: 1 },
};

const cache = new Map<string, THREE.Material>();

export function pbr(kind: string, color: string, repeat = 0): THREE.MeshStandardMaterial {
  const spec = SPECS[kind] ?? SPECS.concrete;
  const key = `${kind}|${color}|${repeat}`;
  const hit = cache.get(key);
  if (hit) return hit as THREE.MeshStandardMaterial;
  const maps = surface(spec.surface);
  const bump = maps.bump.clone();
  const rough = maps.rough.clone();
  const tiling = repeat || spec.repeat;
  for (const texture of [bump, rough]) {
    texture.repeat.set(tiling, tiling);
    texture.needsUpdate = true;
  }
  const params: THREE.MeshPhysicalMaterialParameters = {
    color: new THREE.Color(color), roughness: spec.rough, metalness: spec.metal, roughnessMap: spec.bump > 0 ? rough : null,
    bumpMap: spec.bump > 0 ? bump : null, bumpScale: spec.bump * 0.02,
  };
  const material = kind === 'glass'
    ? new THREE.MeshPhysicalMaterial({ ...params, transmission: 0.55, transparent: true, opacity: 0.55, ior: 1.45, thickness: 0.02, envMapIntensity: 1.4 })
    : new THREE.MeshStandardMaterial(params);
  material.userData.shared = true;
  cache.set(key, material);
  return material;
}

export function glow(color: string, intensity = 2.2): THREE.MeshStandardMaterial {
  const key = `glow|${color}|${intensity}`;
  const hit = cache.get(key);
  if (hit) return hit as THREE.MeshStandardMaterial;
  const material = new THREE.MeshStandardMaterial({ color: '#fff7dc', emissive: new THREE.Color(color), emissiveIntensity: intensity, roughness: 0.4 });
  material.userData.shared = true;
  cache.set(key, material);
  return material;
}

export function leaf(color: string, jitter = 0): THREE.MeshStandardMaterial {
  const key = `leaf|${color}|${jitter}`;
  const hit = cache.get(key);
  if (hit) return hit as THREE.MeshStandardMaterial;
  const material = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.88, metalness: 0, side: THREE.DoubleSide });
  material.userData.shared = true;
  cache.set(key, material);
  return material;
}

export function releaseMaterials(): void {
  cache.forEach((m) => m.dispose());
  cache.clear();
}
