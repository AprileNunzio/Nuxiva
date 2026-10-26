import * as THREE from 'three';

export class Props3DBuilder {
  
  static buildUmbrella(): THREE.Group {
    const umbrellaGroup = new THREE.Group();
    umbrellaGroup.name = "prop_umbrella";

    const canopyGeo = new THREE.ConeGeometry(1.6, 0.6, 24, 1, true);
    canopyGeo.rotateX(Math.PI);
    const canopyMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.2,
      metalness: 0.8,
      side: THREE.DoubleSide
    });
    const canopy = new THREE.Mesh(canopyGeo, canopyMat);
    canopy.position.y = 1.3;
    umbrellaGroup.add(canopy);

    const ringGeo = new THREE.TorusGeometry(1.6, 0.02, 8, 32);
    ringGeo.rotateX(Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.position.y = 1.0;
    umbrellaGroup.add(ring);

    const shaftGeo = new THREE.CylinderGeometry(0.025, 0.025, 2.0, 16);
    const shaftMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      metalness: 0.9,
      roughness: 0.1
    });
    const shaft = new THREE.Mesh(shaftGeo, shaftMat);
    shaft.position.y = 0.5;
    umbrellaGroup.add(shaft);

    const tipGeo = new THREE.ConeGeometry(0.04, 0.2, 12);
    const tipMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, metalness: 0.9, roughness: 0.1 });
    const tip = new THREE.Mesh(tipGeo, tipMat);
    tip.position.y = 1.6;
    umbrellaGroup.add(tip);

    const handleGeo = new THREE.TorusGeometry(0.12, 0.03, 8, 16, Math.PI);
    handleGeo.rotateZ(Math.PI);
    const handleMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.4 });
    const handle = new THREE.Mesh(handleGeo, handleMat);
    handle.position.set(-0.12, -0.45, 0);
    umbrellaGroup.add(handle);

    umbrellaGroup.rotation.z = 0.2;
    umbrellaGroup.rotation.y = 0.4;
    return umbrellaGroup;
  }

  
  static buildCadWorkbench(): THREE.Group {
    const benchGroup = new THREE.Group();
    benchGroup.name = "tool_cad_workbench";

    const tableTopGeo = new THREE.BoxGeometry(3.0, 0.1, 1.8);
    const tableTopMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.7, roughness: 0.3 });
    const tableTop = new THREE.Mesh(tableTopGeo, tableTopMat);
    tableTop.position.y = 1.0;
    benchGroup.add(tableTop);

    const edgeGeo = new THREE.BoxGeometry(3.04, 0.02, 1.84);
    const edgeMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4 });
    const edge = new THREE.Mesh(edgeGeo, edgeMat);
    edge.position.y = 1.05;
    benchGroup.add(edge);

    const legGeo = new THREE.CylinderGeometry(0.06, 0.06, 1.0, 12);
    const legMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.9, roughness: 0.2 });
    const legPositions = [
      [-1.35, 0.5, -0.75],
      [1.35, 0.5, -0.75],
      [-1.35, 0.5, 0.75],
      [1.35, 0.5, 0.75]
    ];
    legPositions.forEach(([x, y, z]) => {
      const leg = new THREE.Mesh(legGeo, legMat);
      leg.position.set(x, y, z);
      benchGroup.add(leg);
    });

    const flangeGroup = new THREE.Group();
    flangeGroup.name = "cad_floating_flange";
    flangeGroup.position.set(0, 1.6, 0);

    const flangeBodyGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.12, 32);
    const flangeMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      metalness: 0.85,
      roughness: 0.15,
      wireframe: false
    });
    const flangeBody = new THREE.Mesh(flangeBodyGeo, flangeMat);
    flangeGroup.add(flangeBody);

    const collarGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.3, 32);
    const collar = new THREE.Mesh(collarGeo, flangeMat);
    flangeGroup.add(collar);

    const wireGeo = new THREE.WireframeGeometry(flangeBodyGeo);
    const wireMat = new THREE.LineBasicMaterial({ color: 0x38bdf8 });
    const wire = new THREE.LineSegments(wireGeo, wireMat);
    flangeGroup.add(wire);

    benchGroup.add(flangeGroup);
    return benchGroup;
  }

  
  static buildHologramTablet(): THREE.Group {
    const tabletGroup = new THREE.Group();
    tabletGroup.name = "tool_hologram_tablet";

    const frameGeo = new THREE.BoxGeometry(1.4, 0.9, 0.03);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.9, roughness: 0.1 });
    const frame = new THREE.Mesh(frameGeo, frameMat);
    tabletGroup.add(frame);

    const screenGeo = new THREE.PlaneGeometry(1.3, 0.8);
    const screenMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide
    });
    const screen = new THREE.Mesh(screenGeo, screenMat);
    screen.position.z = 0.02;
    tabletGroup.add(screen);

    for (let i = 0; i < 6; i++) {
      const lineGeo = new THREE.PlaneGeometry(0.8 - Math.random() * 0.3, 0.03);
      const lineMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
      const line = new THREE.Mesh(lineGeo, lineMat);
      line.position.set(-0.2 + (Math.random() * 0.1), 0.25 - (i * 0.1), 0.025);
      tabletGroup.add(line);
    }

    return tabletGroup;
  }

  
  static buildServerRack(): THREE.Group {
    const rackGroup = new THREE.Group();
    rackGroup.name = "device_server_rack";

    const bodyGeo = new THREE.BoxGeometry(1.2, 2.6, 1.2);
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x0b1120, roughness: 0.5, metalness: 0.6 });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 1.3;
    rackGroup.add(body);

    for (let slot = 0; slot < 8; slot++) {
      const bladeGeo = new THREE.BoxGeometry(1.0, 0.22, 0.05);
      const bladeMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.3 });
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.position.set(0, 0.35 + slot * 0.28, 0.61);
      rackGroup.add(blade);

      const ledGeo = new THREE.BoxGeometry(0.04, 0.04, 0.02);
      const ledMat = new THREE.MeshBasicMaterial({ color: slot % 2 === 0 ? 0x10b981 : 0x06b6d4 });
      const led = new THREE.Mesh(ledGeo, ledMat);
      led.position.set(-0.4, 0.35 + slot * 0.28, 0.64);
      rackGroup.add(led);
    }

    return rackGroup;
  }

  
  static buildDrone(): THREE.Group {
    const droneGroup = new THREE.Group();
    droneGroup.name = "veh_surveillance_drone";

    const bodyGeo = new THREE.SphereGeometry(0.3, 16, 16);
    bodyGeo.scale(1.2, 0.4, 1.2);
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.8, roughness: 0.2 });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    droneGroup.add(body);

    const eyeGeo = new THREE.SphereGeometry(0.1, 16, 16);
    const eyeMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const eye = new THREE.Mesh(eyeGeo, eyeMat);
    eye.position.set(0, 0, 0.3);
    droneGroup.add(eye);

    const armGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.8, 8);
    armGeo.rotateZ(Math.PI / 2);
    const armMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.9, roughness: 0.1 });

    const arm1 = new THREE.Mesh(armGeo, armMat);
    arm1.rotation.y = Math.PI / 4;
    droneGroup.add(arm1);

    const arm2 = new THREE.Mesh(armGeo, armMat);
    arm2.rotation.y = -Math.PI / 4;
    droneGroup.add(arm2);

    const rotorGeo = new THREE.CylinderGeometry(0.2, 0.2, 0.01, 16);
    const rotorMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.6 });
    const rotorPositions = [
      [0.3, 0.08, 0.3],
      [-0.3, 0.08, 0.3],
      [0.3, 0.08, -0.3],
      [-0.3, 0.08, -0.3]
    ];
    rotorPositions.forEach(([x, y, z]) => {
      const rotor = new THREE.Mesh(rotorGeo, rotorMat);
      rotor.position.set(x, y, z);
      droneGroup.add(rotor);
    });

    return droneGroup;
  }

  
  static buildSmartLight(isOn: boolean = true, color: number = 0x38bdf8): THREE.Group {
    const lampGroup = new THREE.Group();
    lampGroup.name = "device_smart_light";

    const baseGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.05, 24);
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.2 });
    const base = new THREE.Mesh(baseGeo, baseMat);
    lampGroup.add(base);

    const stemGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.6, 16);
    const stem = new THREE.Mesh(stemGeo, baseMat);
    stem.position.y = 0.8;
    lampGroup.add(stem);

    const bulbGeo = new THREE.SphereGeometry(0.25, 24, 24);
    const bulbMat = new THREE.MeshStandardMaterial({
      color: isOn ? color : 0x334155,
      emissive: isOn ? color : 0x000000,
      emissiveIntensity: isOn ? 0.9 : 0.0,
      roughness: 0.2
    });
    const bulb = new THREE.Mesh(bulbGeo, bulbMat);
    bulb.position.y = 1.65;
    lampGroup.add(bulb);

    if (isOn) {
      const pointLight = new THREE.PointLight(color, 2.5, 8.0);
      pointLight.position.y = 1.65;
      lampGroup.add(pointLight);
    }

    return lampGroup;
  }
}
