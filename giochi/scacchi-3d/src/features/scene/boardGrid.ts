import * as THREE from 'three';
import { BOARD_SQ_SIZE, BOARD_SURFACE_Y } from '../game/constants';
import { MoveAnimator } from '../cinematics/moveAnimator';

export class BoardGrid {
  public static buildGrid(boardGroup: THREE.Group, boardSquareMeshes: THREE.Mesh[]): void {
    const tileH = 0.036;
    const sqGeo = new THREE.BoxGeometry(BOARD_SQ_SIZE * 0.985, tileH, BOARD_SQ_SIZE * 0.985);
    const lightSqMat = new THREE.MeshStandardMaterial({
      color: 0xdcd3c2,
      roughness: 0.38,
      metalness: 0.06
    });
    const darkSqMat = new THREE.MeshStandardMaterial({
      color: 0x14171f,
      roughness: 0.28,
      metalness: 0.18
    });
    const goldTrimMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      roughness: 0.32,
      metalness: 0.88
    });

    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const isLight = (r + c) % 2 === 0;
        const sqMesh = new THREE.Mesh(sqGeo, isLight ? lightSqMat : darkSqMat);
        const pos = MoveAnimator.boardToWorld(r, c);
        sqMesh.position.set(pos.x, BOARD_SURFACE_Y - tileH * 0.5, pos.z);
        sqMesh.receiveShadow = true;
        sqMesh.userData = { r, c, isSquare: true };
        boardGroup.add(sqMesh);
        boardSquareMeshes.push(sqMesh);
      }
    }

    const halfB = 4.0 * BOARD_SQ_SIZE;
    const rimW = 0.06;
    const rimH = 0.042;
    const horizGeo = new THREE.BoxGeometry(halfB * 2 + rimW * 2, rimH, rimW);
    const vertGeo = new THREE.BoxGeometry(rimW, rimH, halfB * 2);

    for (const s of [-1, 1]) {
      const hBar = new THREE.Mesh(horizGeo, goldTrimMat);
      hBar.position.set(0, BOARD_SURFACE_Y - rimH * 0.45, s * (halfB + rimW * 0.5));
      hBar.receiveShadow = true;
      boardGroup.add(hBar);

      const vBar = new THREE.Mesh(vertGeo, goldTrimMat);
      vBar.position.set(s * (halfB + rimW * 0.5), BOARD_SURFACE_Y - rimH * 0.45, 0);
      vBar.receiveShadow = true;
      boardGroup.add(vBar);
    }
  }
}
