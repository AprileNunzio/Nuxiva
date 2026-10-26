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
  golden_hour: { sun: '#ffb877', sunPower: 3.6, elevation: 24, azimuth: 215, hemiSky: '#cfdcf0', hemiGround: '#7a6a58', hemiPower: 0.8, skyTop: '#a9b8cc', skyHorizon: '#c7cdd6', skyGround: '#c7cdd6', fog: '#c7cdd6', exposure: 0.92, lamps: 0, bloom: 0.12, table: '#c7cdd6' },
  overcast: { sun: '#e8eef5', sunPower: 1.3, elevation: 58, azimuth: 200, hemiSky: '#dfe6ee', hemiGround: '#8a8f8a', hemiPower: 1.1, skyTop: '#aeb9c6', skyHorizon: '#cfd5db', skyGround: '#cfd5db', fog: '#cfd5db', exposure: 0.95, lamps: 0, bloom: 0.08, table: '#cfd5db' },
  blue_hour: { sun: '#8aa5e0', sunPower: 1.0, elevation: 9, azimuth: 230, hemiSky: '#6f8ac0', hemiGround: '#2d3140', hemiPower: 0.75, skyTop: '#26355f', skyHorizon: '#8c93b4', skyGround: '#8c93b4', fog: '#7e86a8', exposure: 1.05, lamps: 1, bloom: 0.34, table: '#8c93b4' },
  noon: { sun: '#fff6e5', sunPower: 4.0, elevation: 62, azimuth: 205, hemiSky: '#c4e0ff', hemiGround: '#8a7a5a', hemiPower: 0.7, skyTop: '#8fb6e6', skyHorizon: '#c9d9ea', skyGround: '#c9d9ea', fog: '#c9d9ea', exposure: 0.88, lamps: 0, bloom: 0.06, table: '#c9d9ea' },
  night: { sun: '#a8bcff', sunPower: 0.8, elevation: 38, azimuth: 150, hemiSky: '#26335c', hemiGround: '#0e1220', hemiPower: 0.45, skyTop: '#050914', skyHorizon: '#1a2447', skyGround: '#1a2447', fog: '#121a38', exposure: 1.25, lamps: 1, bloom: 0.5, table: '#1a2447' },
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
