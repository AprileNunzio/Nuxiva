import type { LensId, LightId } from '../types';

export interface LightPreset {
  readonly sun: string;
  readonly sunPower: number;
  readonly elevation: number;
  readonly azimuth: number;
  readonly hemiSky: string;
  readonly hemiGround: string;
  readonly hemiPower: number;
  readonly skyTop: string;
  readonly skyHorizon: string;
  readonly skyGround: string;
  readonly fog: string;
  readonly exposure: number;
  readonly lamps: number;
  readonly bloom: number;
  readonly table: string;
}

export const LIGHTS: Record<LightId, LightPreset> = {
  golden_hour: { sun: '#ffb36b', sunPower: 4.2, elevation: 15, azimuth: 215, hemiSky: '#ffdcb8', hemiGround: '#6b5440', hemiPower: 0.65, skyTop: '#7fa6d8', skyHorizon: '#ffc79a', skyGround: '#c8a88a', fog: '#f4d2ae', exposure: 1.08, lamps: 0, bloom: 0.22, table: '#e8dfd0' },
  overcast: { sun: '#e8eef5', sunPower: 1.1, elevation: 58, azimuth: 200, hemiSky: '#e2e8ef', hemiGround: '#8a8f8a', hemiPower: 1.25, skyTop: '#b3bfcb', skyHorizon: '#e4e8ec', skyGround: '#b8bcbd', fog: '#dfe3e6', exposure: 1.0, lamps: 0, bloom: 0.1, table: '#e6e4df' },
  blue_hour: { sun: '#8aa5e0', sunPower: 0.9, elevation: 7, azimuth: 230, hemiSky: '#6f8ac0', hemiGround: '#2d3140', hemiPower: 0.7, skyTop: '#20305c', skyHorizon: '#e39a7a', skyGround: '#3a3a4d', fog: '#8f97b8', exposure: 1.18, lamps: 1, bloom: 0.38, table: '#9a9fb0' },
  noon: { sun: '#fff6e5', sunPower: 4.8, elevation: 62, azimuth: 205, hemiSky: '#c4e0ff', hemiGround: '#8a7a5a', hemiPower: 0.75, skyTop: '#4d8ee0', skyHorizon: '#c4e0ff', skyGround: '#b9b19a', fog: '#d6e8f8', exposure: 0.95, lamps: 0, bloom: 0.08, table: '#ece8df' },
  night: { sun: '#a8bcff', sunPower: 0.75, elevation: 38, azimuth: 150, hemiSky: '#26335c', hemiGround: '#0e1220', hemiPower: 0.45, skyTop: '#050914', skyHorizon: '#1f2a4f', skyGround: '#0a0e1c', fog: '#0f1630', exposure: 1.35, lamps: 1, bloom: 0.55, table: '#1b2038' },
};

export interface LensPreset {
  readonly fov: number;
  readonly blur: number;
  readonly band: number;
  readonly fit: number;
  readonly bokeh: number;
}

export const LENSES: Record<LensId, LensPreset> = {
  macro: { fov: 20, blur: 3.4, band: 0.1, fit: 0.5, bokeh: 1.0 },
  tilt_shift: { fov: 30, blur: 2.4, band: 0.2, fit: 0.62, bokeh: 0.8 },
  standard_50mm: { fov: 40, blur: 0.5, band: 0.42, fit: 0.7, bokeh: 0.25 },
};
