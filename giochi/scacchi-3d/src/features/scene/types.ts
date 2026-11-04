import * as THREE from 'three';

export interface CathedralBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  minZ: number;
  maxZ: number;
}

export interface SolidPillar {
  x: number;
  z: number;
  r: number;
  maxY: number;
  isColumn: boolean;
}

export interface BrazierConfig {
  pos: [number, number, number];
  baseIntensity: number;
  dist: number;
}
