import * as THREE from 'three';
import { BOARD_SQ_SIZE, BOARD_SURFACE_Y } from '../game/constants';
import { ChessMove } from '../game/types';

export interface ActiveMoveAnimation {
  mesh: THREE.Object3D;
  startPos: THREE.Vector3;
  endPos: THREE.Vector3;
  duration: number;
  elapsed: number;
  move: ChessMove;
  onComplete: () => void;
}

export class MoveAnimator {
  private activeAnimation: ActiveMoveAnimation | null = null;
  private kingFallMesh: THREE.Object3D | null = null;
  private kingFallElapsed = 0;
  private kingFallDuration = 1.4;

  public static boardToWorld(row: number, col: number): THREE.Vector3 {
    return new THREE.Vector3(
      (col - 3.5) * BOARD_SQ_SIZE,
      BOARD_SURFACE_Y,
      (row - 3.5) * BOARD_SQ_SIZE
    );
  }

  public animateMove(
    mesh: THREE.Object3D,
    move: ChessMove,
    onComplete: () => void
  ): void {
    const startPos = MoveAnimator.boardToWorld(move.fromRow, move.fromCol);
    const endPos = MoveAnimator.boardToWorld(move.toRow, move.toCol);
    this.activeAnimation = {
      mesh,
      startPos,
      endPos,
      duration: 0.55,
      elapsed: 0,
      move,
      onComplete
    };
  }

  public startKingFall(kingMesh: THREE.Object3D): void {
    this.kingFallMesh = kingMesh;
    this.kingFallElapsed = 0;
  }

  public isBusy(): boolean {
    return this.activeAnimation !== null;
  }

  public update(delta: number): void {
    if (this.activeAnimation) {
      const anim = this.activeAnimation;
      anim.elapsed += delta;
      const progress = Math.min(1, anim.elapsed / anim.duration);
      const eased = progress < 0.5
        ? 4 * progress * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 3) / 2;

      anim.mesh.position.lerpVectors(anim.startPos, anim.endPos, eased);
      const arcHeight = Math.sin(progress * Math.PI) * 0.18;
      anim.mesh.position.y = BOARD_SURFACE_Y + arcHeight;

      if (progress >= 1) {
        anim.mesh.position.copy(anim.endPos);
        const doneCb = anim.onComplete;
        this.activeAnimation = null;
        doneCb();
      }
    }

    if (this.kingFallMesh) {
      this.kingFallElapsed += delta;
      const progress = Math.min(1, this.kingFallElapsed / this.kingFallDuration);
      const tiltAngle = progress * (Math.PI / 2.1);
      this.kingFallMesh.rotation.z = tiltAngle;
      if (progress >= 1) {
        this.kingFallMesh = null;
      }
    }
  }
}
