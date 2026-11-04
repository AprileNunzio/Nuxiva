import * as THREE from 'three';
import { CathedralBounds, SolidPillar } from './types';
import { BOARD_SURFACE_Y } from '../game/constants';

const CATHEDRAL_BOUNDS: CathedralBounds = {
  minX: -6.65,
  maxX: 6.65,
  minY: 0.34,
  maxY: 8.85,
  minZ: -18.10,
  maxZ: 18.10
};

const CATHEDRAL_COLUMN_ROWS = [
  { z: -16.65, xAbs: 4.25 },
  { z: -11.85, xAbs: 4.25 },
  { z: -6.85,  xAbs: 4.65 },
  { z: 6.85,   xAbs: 4.65 },
  { z: 11.85,  xAbs: 4.25 },
  { z: 16.65,  xAbs: 4.25 }
];

const CATHEDRAL_SOLID_PILLARS: SolidPillar[] = [
  ...CATHEDRAL_COLUMN_ROWS.flatMap(({ z, xAbs }) => [
    { x: -xAbs, z, r: 0.86, maxY: 9.65, isColumn: true },
    { x: xAbs,  z, r: 0.86, maxY: 9.65, isColumn: true }
  ]),
  { x: -3.65, z: 0.00, r: 0.68, maxY: 1.95, isColumn: false },
  { x: 3.65,  z: 0.00, r: 0.68, maxY: 1.95, isColumn: false }
];

const ALTAR_TOP_Y = 0.722;
const ALTAR_HALF_X = 2.48;
const ALTAR_HALF_Z = 2.38;
const BOARD_HALF_XZ = 1.66;

export class BoundsSolver {
  public static clampPointToCathedralRoom(pt: THREE.Vector3, isTarget = false): void {
    const margin = isTarget ? 0.15 : 0.0;
    pt.x = Math.max(CATHEDRAL_BOUNDS.minX - margin, Math.min(CATHEDRAL_BOUNDS.maxX + margin, pt.x));
    pt.z = Math.max(CATHEDRAL_BOUNDS.minZ - margin, Math.min(CATHEDRAL_BOUNDS.maxZ + margin, pt.z));
    const aisleDrop = Math.max(0, Math.abs(pt.x) - 4.15) * 0.55;
    const localMaxY = Math.min(CATHEDRAL_BOUNDS.maxY, 9.05 - aisleDrop);
    const localMinY = isTarget ? 0.20 : CATHEDRAL_BOUNDS.minY;
    pt.y = Math.max(localMinY, Math.min(localMaxY, pt.y));
  }

  public static enforceBoundsAndCollisions(
    prevPos: THREE.Vector3 | null,
    curPos: THREE.Vector3,
    targetPos: THREE.Vector3,
    isAnimatingMove = false
  ): void {
    this.clampPointToCathedralRoom(targetPos, true);
    this.clampPointToCathedralRoom(curPos, false);

    if (isAnimatingMove) {
      if (Math.abs(curPos.x) < 2.48 && Math.abs(curPos.z) < 2.38) {
        curPos.y = Math.max(curPos.y, BOARD_SURFACE_Y + 0.30);
      }
      return;
    }

    const x0 = prevPos ? prevPos.x : curPos.x;
    const z0 = prevPos ? prevPos.z : curPos.z;
    let x1 = curPos.x;
    let z1 = curPos.z;
    const moveDx = x1 - x0;
    const moveDz = z1 - z0;
    const moveLenSq = moveDx * moveDx + moveDz * moveDz;
    const moveLen = Math.sqrt(moveLenSq);
    const isContinuousStep = Boolean(prevPos) && moveLen > 1e-5 && moveLen < 8.0;

    for (const p of CATHEDRAL_SOLID_PILLARS) {
      if (curPos.y > p.maxY) continue;

      let tClosest = 1.0;
      if (isContinuousStep) {
        tClosest = ((p.x - x0) * moveDx + (p.z - z0) * moveDz) / moveLenSq;
        tClosest = Math.max(0.0, Math.min(1.0, tClosest));
      }
      const cxSeg = x0 + moveDx * tClosest;
      const czSeg = z0 + moveDz * tClosest;
      const dSeg = isContinuousStep ? Math.hypot(cxSeg - p.x, czSeg - p.z) : Infinity;
      const dEnd = Math.hypot(x1 - p.x, z1 - p.z);

      if (dSeg < p.r || dEnd < p.r) {
        if (isContinuousStep) {
          const startAng = Math.atan2(z0 - p.z, x0 - p.x);
          const endAng = Math.atan2(z1 - p.z, x1 - p.x);
          let deltaAng = endAng - startAng;
          while (deltaAng > Math.PI) deltaAng -= Math.PI * 2;
          while (deltaAng < -Math.PI) deltaAng += Math.PI * 2;

          const tanX = -Math.sin(startAng);
          const tanZ = Math.cos(startAng);
          let tangMove = moveDx * tanX + moveDz * tanZ;
          if (Math.abs(tangMove) < moveLen * 0.18) {
            const aisleSign = (p.x >= 0 ? -1 : 1) * Math.sign(moveDz || 1);
            tangMove = (tangMove >= 0 ? 1 : aisleSign || 1) * moveLen * 0.65;
          }
          const arcStep = Math.sign(deltaAng || tangMove || 1) * Math.max(Math.abs(deltaAng), Math.min(Math.PI * 0.35, Math.abs(tangMove) / p.r));
          const newAng = startAng + arcStep;
          x1 = p.x + Math.cos(newAng) * p.r;
          z1 = p.z + Math.sin(newAng) * p.r;
        } else {
          const radX = x1 - p.x;
          const radZ = z1 - p.z;
          const radLen = Math.hypot(radX, radZ);
          if (radLen > 1e-4) {
            x1 = p.x + (radX / radLen) * p.r;
            z1 = p.z + (radZ / radLen) * p.r;
          } else {
            x1 = p.x + (p.x >= 0 ? -p.r : p.r);
            z1 = p.z;
          }
        }
      }
    }

    if (Math.abs(targetPos.x) < 2.36 && Math.abs(targetPos.z) < 2.26) {
      const minTargetY =
        Math.abs(targetPos.x) < 1.56 && Math.abs(targetPos.z) < 1.56
          ? BOARD_SURFACE_Y + 0.05
          : ALTAR_TOP_Y + 0.05;
      if (targetPos.y < minTargetY) {
        targetPos.y = minTargetY;
      }
    }

    if (Math.abs(x1) < ALTAR_HALF_X && Math.abs(z1) < ALTAR_HALF_Z) {
      const isOverChessboard = Math.abs(x1) < BOARD_HALF_XZ && Math.abs(z1) < BOARD_HALF_XZ;
      const solidAltarTopY = isOverChessboard ? (BOARD_SURFACE_Y + 0.25) : (ALTAR_TOP_Y + 0.28);
      if (curPos.y < solidAltarTopY) {
        curPos.y = solidAltarTopY;
      }
    }

    curPos.x = x1;
    curPos.z = z1;
  }
}
