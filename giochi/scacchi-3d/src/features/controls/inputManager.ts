import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { BOARD_SQ_SIZE } from '../game/constants';
import { BoundsSolver } from '../scene/boundsSolver';

export class InputManager {
  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  private controls: OrbitControls;
  private raycaster = new THREE.Raycaster();
  private mouse = new THREE.Vector2();
  private keysDown: Record<string, boolean> = {};
  private onSquareClick: (row: number, col: number) => void;

  constructor(
    camera: THREE.PerspectiveCamera,
    domElement: HTMLElement,
    controls: OrbitControls,
    onSquareClick: (row: number, col: number) => void
  ) {
    this.camera = camera;
    this.domElement = domElement;
    this.controls = controls;
    this.onSquareClick = onSquareClick;

    this.bindEvents();
  }

  private bindEvents(): void {
    window.addEventListener('keydown', (e) => {
      this.keysDown[e.key.toLowerCase()] = true;
    });

    window.addEventListener('keyup', (e) => {
      this.keysDown[e.key.toLowerCase()] = false;
    });

    this.domElement.addEventListener('pointerup', (e) => {
      const rect = this.domElement.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -0.775);
      const intersection = new THREE.Vector3();

      if (this.raycaster.ray.intersectPlane(plane, intersection)) {
        const c = Math.floor(intersection.x / BOARD_SQ_SIZE + 4);
        const r = Math.floor(intersection.z / BOARD_SQ_SIZE + 4);
        if (r >= 0 && r < 8 && c >= 0 && c < 8) {
          this.onSquareClick(r, c);
        }
      }
    });
  }

  public update(delta: number): void {
    const moveSpeed = 2.4 * delta;
    const forward = new THREE.Vector3();
    this.camera.getWorldDirection(forward);
    forward.y = 0;
    forward.normalize();

    const right = new THREE.Vector3();
    right.crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

    const prevPos = this.camera.position.clone();
    const move = new THREE.Vector3();

    if (this.keysDown['w']) move.addScaledVector(forward, moveSpeed);
    if (this.keysDown['s']) move.addScaledVector(forward, -moveSpeed);
    if (this.keysDown['d']) move.addScaledVector(right, moveSpeed);
    if (this.keysDown['a']) move.addScaledVector(right, -moveSpeed);
    if (this.keysDown['r']) move.y += moveSpeed;
    if (this.keysDown['f']) move.y -= moveSpeed;

    if (move.lengthSq() > 0) {
      this.camera.position.add(move);
      this.controls.target.add(move);
      BoundsSolver.enforceBoundsAndCollisions(prevPos, this.camera.position, this.controls.target);
      this.controls.update();
    }
  }
}
