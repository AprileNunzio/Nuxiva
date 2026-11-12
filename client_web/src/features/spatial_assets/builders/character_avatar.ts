import * as THREE from 'three';

export class NuxivaAvatarBuilder {
  
  static buildAvatar(): {
    rootGroup: THREE.Group;
    rightHandSlot: THREE.Group;
    headGroup: THREE.Group;
    coreLight: THREE.PointLight;
    energyRings: THREE.Group;
    updateAnimation: (delta: number, isSpeaking: boolean, isThinking: boolean) => void;
  } {
    const root = new THREE.Group();
    root.name = "nuxiva_avatar";

    const torsoGeo = new THREE.CylinderGeometry(0.35, 0.25, 0.9, 16);
    const armorMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.85,
      roughness: 0.2
    });
    const torso = new THREE.Mesh(torsoGeo, armorMat);
    torso.position.y = 1.6;
    root.add(torso);

    const coreGeo = new THREE.SphereGeometry(0.12, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.position.set(0, 1.7, 0.22);
    root.add(coreMesh);

    const coreLight = new THREE.PointLight(0x00f0ff, 2.0, 4.0);
    coreLight.position.set(0, 1.7, 0.3);
    root.add(coreLight);

    const energyRings = new THREE.Group();
    energyRings.position.set(0, 1.7, 0);
    const ringGeo1 = new THREE.TorusGeometry(0.2, 0.015, 8, 32);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
    const ring1 = new THREE.Mesh(ringGeo1, ringMat);
    energyRings.add(ring1);

    const ringGeo2 = new THREE.TorusGeometry(0.25, 0.012, 8, 32);
    const ring2 = new THREE.Mesh(ringGeo2, ringMat);
    ring2.rotation.x = Math.PI / 3;
    energyRings.add(ring2);
    root.add(energyRings);

    const headGroup = new THREE.Group();
    headGroup.position.set(0, 2.3, 0);

    const headGeo = new THREE.SphereGeometry(0.24, 24, 24);
    headGeo.scale(0.9, 1.0, 1.0);
    const headMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.9, roughness: 0.15 });
    const head = new THREE.Mesh(headGeo, headMat);
    headGroup.add(head);

    const visorGeo = new THREE.BoxGeometry(0.32, 0.08, 0.1);
    const visorMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const visor = new THREE.Mesh(visorGeo, visorMat);
    visor.position.set(0, 0.04, 0.2);
    headGroup.add(visor);
    root.add(headGroup);

    const rightArmGroup = new THREE.Group();
    rightArmGroup.position.set(0.48, 1.9, 0);

    const armGeo = new THREE.CylinderGeometry(0.06, 0.05, 0.5, 12);
    const upperArm = new THREE.Mesh(armGeo, armorMat);
    upperArm.position.y = -0.25;
    rightArmGroup.add(upperArm);

    const forearmGroup = new THREE.Group();
    forearmGroup.position.set(0, -0.5, 0);
    const forearm = new THREE.Mesh(armGeo, armorMat);
    forearm.position.y = -0.25;
    forearmGroup.add(forearm);

    const rightHandSlot = new THREE.Group();
    rightHandSlot.name = "right_hand_slot";
    rightHandSlot.position.set(0, -0.5, 0.1);
    forearmGroup.add(rightHandSlot);

    rightArmGroup.add(forearmGroup);
    root.add(rightArmGroup);

    const leftArmGroup = new THREE.Group();
    leftArmGroup.position.set(-0.48, 1.9, 0);
    const leftArm = new THREE.Mesh(armGeo, armorMat);
    leftArm.position.y = -0.25;
    leftArmGroup.add(leftArm);
    root.add(leftArmGroup);

    const floatBaseGeo = new THREE.CylinderGeometry(0.2, 0.05, 0.6, 16);
    const floatBase = new THREE.Mesh(floatBaseGeo, armorMat);
    floatBase.position.y = 0.9;
    root.add(floatBase);

    const levRingGeo = new THREE.TorusGeometry(0.4, 0.02, 8, 32);
    levRingGeo.rotateX(Math.PI / 2);
    const levRingMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const levRing = new THREE.Mesh(levRingGeo, levRingMat);
    levRing.position.y = 0.4;
    root.add(levRing);

    let time = 0;
    const updateAnimation = (delta: number, isSpeaking: boolean, isThinking: boolean) => {
      time += delta;

      root.position.y = Math.sin(time * 2.0) * 0.06;

      energyRings.rotation.y += delta * (isThinking ? 4.0 : 1.2);
      energyRings.rotation.z += delta * (isThinking ? 3.0 : 0.8);

      if (isSpeaking) {
        coreLight.intensity = 2.0 + Math.sin(time * 12.0) * 1.5;
        visor.scale.x = 1.0 + Math.sin(time * 8.0) * 0.15;
      } else if (isThinking) {
        coreLight.intensity = 1.5 + Math.sin(time * 6.0) * 0.8;
      } else {
        coreLight.intensity = 1.8 + Math.sin(time * 2.0) * 0.3;
        visor.scale.x = 1.0;
      }

      headGroup.rotation.y = Math.sin(time * 0.8) * 0.1;
      headGroup.rotation.x = Math.sin(time * 1.2) * 0.05;
    };

    return {
      rootGroup: root,
      rightHandSlot,
      headGroup,
      coreLight,
      energyRings,
      updateAnimation
    };
  }
}
