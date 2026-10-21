import * as THREE from 'three';
import { BrazierFlameShader } from './brazierFlameShader';

export class CathedralSetup {
  public static configureCathedral(
    cathedralScene: THREE.Object3D,
    scene: THREE.Scene,
    flameUniforms: Record<string, { value: unknown }>[]
  ): void {
    const flameCoreShader = BrazierFlameShader.createFlameMaterial({
      baseColor: [1.0, 0.96, 0.72],
      midColor: [1.0, 0.64, 0.12],
      tipColor: [1.0, 0.36, 0.03],
      strength: 1.85,
      opacity: 0.92,
      zMin: 0.60,
      zMax: 1.64,
      layerSeed: 0.0
    }, flameUniforms);

    const flameMidShader = BrazierFlameShader.createFlameMaterial({
      baseColor: [1.0, 0.78, 0.25],
      midColor: [1.0, 0.40, 0.04],
      tipColor: [0.92, 0.16, 0.01],
      strength: 1.35,
      opacity: 0.82,
      zMin: 0.60,
      zMax: 1.52,
      layerSeed: 2.1
    }, flameUniforms);

    const flameOuterShader = BrazierFlameShader.createFlameMaterial({
      baseColor: [1.0, 0.45, 0.06],
      midColor: [0.88, 0.18, 0.015],
      tipColor: [0.45, 0.03, 0.002],
      strength: 0.95,
      opacity: 0.68,
      zMin: 0.60,
      zMax: 1.36,
      layerSeed: 4.4
    }, flameUniforms);

    cathedralScene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const m = child as THREE.Mesh;
        const name = m.name || '';

        if (name === 'Opt8_Brazier_Flame_Core') {
          m.material = flameCoreShader;
          m.castShadow = false;
        } else if (name === 'Opt8_Brazier_Flame_Mid') {
          BrazierFlameShader.stripIcosphereSparks(m.geometry);
          m.material = flameMidShader;
          m.castShadow = false;
        } else if (name === 'Opt8_Brazier_Flame_Outer') {
          m.material = flameOuterShader;
          m.castShadow = false;
        } else {
          m.receiveShadow = true;
          if (name !== 'Opt8_Cathedral_Floor' && name !== 'Opt8_Obsidian_Altar_Table') {
            m.castShadow = true;
          }
        }
      }
    });

    const glowTex = BrazierFlameShader.createSoftGlowTexture();
    const glowMat = new THREE.SpriteMaterial({
      map: glowTex,
      color: 0xffaa44,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending
    });

    [-3.65, 3.65].forEach((bx) => {
      const sprite = new THREE.Sprite(glowMat);
      sprite.position.set(bx, 1.35, 0.0);
      sprite.scale.set(2.4, 2.4, 1);
      scene.add(sprite);
    });

    cathedralScene.position.set(0, 0, -0.65);
    scene.add(cathedralScene);
  }
}
