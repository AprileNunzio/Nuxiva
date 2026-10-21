import * as THREE from 'three';

export interface DebrisParticle {
  mesh: THREE.Mesh;
  velocity: THREE.Vector3;
  rotVelocity: THREE.Vector3;
  life: number;
  maxLife: number;
}

export class ShatterPhysics {
  private particles: DebrisParticle[] = [];
  private group: THREE.Group;
  private boxGeo: THREE.BoxGeometry;
  private whiteMat: THREE.MeshStandardMaterial;
  private blackMat: THREE.MeshStandardMaterial;

  constructor(scene: THREE.Scene) {
    this.group = new THREE.Group();
    scene.add(this.group);
    this.boxGeo = new THREE.BoxGeometry(0.045, 0.045, 0.045);
    this.whiteMat = new THREE.MeshStandardMaterial({
      color: 0xede8dc,
      roughness: 0.7,
      metalness: 0.1
    });
    this.blackMat = new THREE.MeshStandardMaterial({
      color: 0x23272f,
      roughness: 0.7,
      metalness: 0.2
    });
  }

  public spawnShatter(position: THREE.Vector3, color: 'white' | 'black', count = 28): void {
    const mat = color === 'white' ? this.whiteMat : this.blackMat;
    for (let i = 0; i < count; i++) {
      const pMesh = new THREE.Mesh(this.boxGeo, mat);
      pMesh.position.copy(position);
      pMesh.position.x += (Math.random() - 0.5) * 0.12;
      pMesh.position.y += Math.random() * 0.2;
      pMesh.position.z += (Math.random() - 0.5) * 0.12;
      pMesh.castShadow = true;

      const angle = Math.random() * Math.PI * 2;
      const speed = 0.8 + Math.random() * 2.2;
      const vy = 1.2 + Math.random() * 2.8;

      const velocity = new THREE.Vector3(
        Math.cos(angle) * speed,
        vy,
        Math.sin(angle) * speed
      );
      const rotVelocity = new THREE.Vector3(
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 12
      );

      this.group.add(pMesh);
      this.particles.push({
        mesh: pMesh,
        velocity,
        rotVelocity,
        life: 0,
        maxLife: 1.6 + Math.random() * 0.8
      });
    }
  }

  public update(delta: number): void {
    const gravity = -9.8;
    const floorY = 0.775;

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.life += delta;
      if (p.life >= p.maxLife) {
        this.group.remove(p.mesh);
        this.particles.splice(i, 1);
        continue;
      }

      p.velocity.y += gravity * delta;
      p.mesh.position.addScaledVector(p.velocity, delta);

      if (p.mesh.position.y < floorY) {
        p.mesh.position.y = floorY;
        p.velocity.y = -p.velocity.y * 0.35;
        p.velocity.x *= 0.65;
        p.velocity.z *= 0.65;
      }

      p.mesh.rotation.x += p.rotVelocity.x * delta;
      p.mesh.rotation.y += p.rotVelocity.y * delta;
      p.mesh.rotation.z += p.rotVelocity.z * delta;

      const scale = Math.max(0, 1 - p.life / p.maxLife);
      p.mesh.scale.setScalar(scale);
    }
  }

  public dispose(): void {
    for (const p of this.particles) {
      this.group.remove(p.mesh);
    }
    this.particles = [];
    this.boxGeo.dispose();
  }
}
