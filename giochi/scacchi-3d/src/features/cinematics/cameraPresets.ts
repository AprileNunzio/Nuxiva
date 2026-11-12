import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export type CameraPresetType = 'player' | 'top' | 'side' | 'wide';

export interface CameraPresetConfig {
  pos: THREE.Vector3;
  target: THREE.Vector3;
}

export class CameraPresets {
  private camera: THREE.PerspectiveCamera;
  private controls: OrbitControls;
  private currentPreset: CameraPresetType = 'player';
  private flipState: Record<CameraPresetType, boolean> = {
    player: false,
    top: false,
    side: false,
    wide: false
  };
  private targetPos = new THREE.Vector3();
  private targetLookAt = new THREE.Vector3();
  private isTransitioning = false;

  constructor(camera: THREE.PerspectiveCamera, controls: OrbitControls) {
    this.camera = camera;
    this.controls = controls;
    this.targetPos.copy(camera.position);
    this.targetLookAt.copy(controls.target);
  }

  public setPreset(type: CameraPresetType): void {
    if (this.currentPreset === type) {
      this.flipState[type] = !this.flipState[type];
    } else {
      this.currentPreset = type;
    }

    const flipped = this.flipState[type];
    let pos = new THREE.Vector3();
    let target = new THREE.Vector3(0, 0.85, -0.15);

    if (type === 'player') {
      pos = flipped ? new THREE.Vector3(0, 2.22, -2.72) : new THREE.Vector3(0, 2.22, 2.72);
      target = flipped ? new THREE.Vector3(0, 0.85, 0.15) : new THREE.Vector3(0, 0.85, -0.15);
    } else if (type === 'top') {
      pos = flipped ? new THREE.Vector3(0, 4.4, -0.01) : new THREE.Vector3(0, 4.4, 0.01);
      target = new THREE.Vector3(0, 0.775, 0);
    } else if (type === 'side') {
      pos = flipped ? new THREE.Vector3(-3.2, 1.85, 0) : new THREE.Vector3(3.2, 1.85, 0);
      target = new THREE.Vector3(0, 0.85, 0);
    } else if (type === 'wide') {
      pos = flipped ? new THREE.Vector3(0, 3.8, -7.5) : new THREE.Vector3(0, 3.8, 7.5);
      target = new THREE.Vector3(0, 1.2, 0);
    }

    this.targetPos.copy(pos);
    this.targetLookAt.copy(target);
    this.isTransitioning = true;
  }

  public update(delta: number): void {
    if (!this.isTransitioning) return;
    const factor = Math.min(1, delta * 4.5);
    this.camera.position.lerp(this.targetPos, factor);
    this.controls.target.lerp(this.targetLookAt, factor);
    this.controls.update();

    if (this.camera.position.distanceTo(this.targetPos) < 0.01 &&
        this.controls.target.distanceTo(this.targetLookAt) < 0.01) {
      this.camera.position.copy(this.targetPos);
      this.controls.target.copy(this.targetLookAt);
      this.isTransitioning = false;
    }
  }

  public getCurrentPreset(): CameraPresetType {
    return this.currentPreset;
  }
}
