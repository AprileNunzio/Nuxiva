import * as THREE from 'three';
import { clone as cloneSkeleton } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { PieceColor, PieceType } from '../game/types';
import { MaterialFactory } from '../scene/materials';
import { MoveAnimator } from '../cinematics/moveAnimator';

const PIECE_SCALES: Record<PieceType, number> = {
  pawn: 0.30,
  knight: 0.30,
  bishop: 0.30,
  rook: 0.30,
  queen: 0.32,
  king: 0.32
};

export class PieceRenderer {
  private templates: Map<string, THREE.Object3D> = new Map();
  private activeMeshes: Map<string, THREE.Object3D> = new Map();

  public registerTemplate(name: string, scene: THREE.Object3D): void {
    this.templates.set(name, scene);
  }

  public createPieceMesh(type: PieceType, color: PieceColor, id: string): THREE.Object3D | null {
    const template = this.templates.get(`${type}_white`);
    if (!template) return null;

    const cloned = cloneSkeleton(template) as THREE.Object3D;
    const scale = PIECE_SCALES[type] || 0.30;
    cloned.scale.set(scale, scale, scale);

    cloned.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const m = child as THREE.Mesh;
        m.castShadow = true;
        m.receiveShadow = true;

        const processMaterial = (mat: THREE.Material): THREE.Material => {
          const name = (mat.name || '').toLowerCase();
          if (name.includes('gold') || name.includes('trim')) {
            return MaterialFactory.getAntiqueGoldMaterial(color === 'black');
          }
          if (name.includes('steel') || name.includes('silver')) {
            return MaterialFactory.getForgedSteelMaterial(color === 'black');
          }
          if (name.includes('glow')) {
            return MaterialFactory.getRuneGlowMaterial(color === 'black');
          }
          return color === 'white'
            ? MaterialFactory.getWhiteMarbleMaterial()
            : MaterialFactory.getBlackObsidianMaterial();
        };

        if (Array.isArray(m.material)) {
          m.material = m.material.map(processMaterial);
        } else if (m.material) {
          m.material = processMaterial(m.material);
        }
      }
    });

    const rotY = color === 'white' ? Math.PI : 0;
    cloned.rotation.y = rotY;
    cloned.userData = { pieceId: id, pieceType: type, pieceColor: color };
    this.activeMeshes.set(id, cloned);
    return cloned;
  }

  public getMesh(id: string): THREE.Object3D | undefined {
    return this.activeMeshes.get(id);
  }

  public removeMesh(id: string, scene: THREE.Scene): void {
    const m = this.activeMeshes.get(id);
    if (m) {
      scene.remove(m);
      this.activeMeshes.delete(id);
    }
  }

  public positionPiece(mesh: THREE.Object3D, row: number, col: number): void {
    const pos = MoveAnimator.boardToWorld(row, col);
    mesh.position.copy(pos);
  }
}
