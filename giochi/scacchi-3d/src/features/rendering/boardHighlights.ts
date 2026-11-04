import * as THREE from 'three';
import { BOARD_SQ_SIZE, BOARD_SURFACE_Y } from '../game/constants';
import { ChessMove } from '../game/types';

export class BoardHighlights {
  private group: THREE.Group;
  private selectionMesh: THREE.Mesh;
  private moveMeshes: THREE.Mesh[] = [];
  private ringGeo: THREE.RingGeometry;
  private dotGeo: THREE.CircleGeometry;
  private selectMat: THREE.MeshBasicMaterial;
  private moveMat: THREE.MeshBasicMaterial;
  private captureMat: THREE.MeshBasicMaterial;

  constructor(scene: THREE.Scene) {
    this.group = new THREE.Group();
    scene.add(this.group);

    this.ringGeo = new THREE.RingGeometry(BOARD_SQ_SIZE * 0.32, BOARD_SQ_SIZE * 0.44, 32);
    this.ringGeo.rotateX(-Math.PI / 2);

    this.dotGeo = new THREE.CircleGeometry(BOARD_SQ_SIZE * 0.16, 24);
    this.dotGeo.rotateX(-Math.PI / 2);

    this.selectMat = new THREE.MeshBasicMaterial({
      color: 0xf5d76e,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide,
      depthWrite: false
    });

    this.moveMat = new THREE.MeshBasicMaterial({
      color: 0x4ea8de,
      transparent: true,
      opacity: 0.65,
      side: THREE.DoubleSide,
      depthWrite: false
    });

    this.captureMat = new THREE.MeshBasicMaterial({
      color: 0xe63946,
      transparent: true,
      opacity: 0.75,
      side: THREE.DoubleSide,
      depthWrite: false
    });

    this.selectionMesh = new THREE.Mesh(this.ringGeo, this.selectMat);
    this.selectionMesh.visible = false;
    this.selectionMesh.position.y = BOARD_SURFACE_Y + 0.003;
    this.group.add(this.selectionMesh);
  }

  public setSelection(row: number, col: number): void {
    this.selectionMesh.position.x = (col - 3.5) * BOARD_SQ_SIZE;
    this.selectionMesh.position.z = (row - 3.5) * BOARD_SQ_SIZE;
    this.selectionMesh.position.y = BOARD_SURFACE_Y + 0.003;
    this.selectionMesh.visible = true;
  }

  public clearSelection(): void {
    this.selectionMesh.visible = false;
  }

  public showValidMoves(moves: ChessMove[]): void {
    this.clearMoves();
    for (const m of moves) {
      const isCapture = Boolean(m.captured);
      const mesh = new THREE.Mesh(
        isCapture ? this.ringGeo : this.dotGeo,
        isCapture ? this.captureMat : this.moveMat
      );
      mesh.position.x = (m.toCol - 3.5) * BOARD_SQ_SIZE;
      mesh.position.z = (m.toRow - 3.5) * BOARD_SQ_SIZE;
      mesh.position.y = BOARD_SURFACE_Y + 0.003;
      this.group.add(mesh);
      this.moveMeshes.push(mesh);
    }
  }

  public clearMoves(): void {
    for (const m of this.moveMeshes) {
      this.group.remove(m);
    }
    this.moveMeshes = [];
  }

  public dispose(): void {
    this.clearSelection();
    this.clearMoves();
    this.ringGeo.dispose();
    this.dotGeo.dispose();
    this.selectMat.dispose();
    this.moveMat.dispose();
    this.captureMat.dispose();
  }
}
