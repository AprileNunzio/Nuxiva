export type ParamValue = number | string | boolean;
export type Params = Record<string, ParamValue>;

export interface Item {
  readonly id: string;
  readonly kind: string;
  readonly x: number;
  readonly y: number;
  readonly z: number;
  readonly rot: number;
  readonly scale: number;
  readonly params: Params;
  readonly motion: Motion | null;
}

export interface Motion {
  readonly axis: 'x' | 'z';
  readonly speed: number;
  readonly span: number;
}

export interface Base {
  readonly w: number;
  readonly d: number;
  readonly depth: number;
  readonly soil: string;
  readonly top: string;
}

export type LightId = 'golden_hour' | 'overcast' | 'blue_hour' | 'noon' | 'night';
export type LensId = 'macro' | 'tilt_shift' | 'standard_50mm';

export interface Look {
  readonly light: LightId;
  readonly lens: LensId;
  readonly blur: number;
  readonly mist: number;
  readonly angle: number;
  readonly orbit: boolean;
}

export interface Job {
  readonly state: 'idle' | 'building' | 'done' | 'error';
  readonly stage: string;
  readonly stages: readonly string[];
  readonly mode?: string;
}

export interface Diorama {
  readonly id: string;
  readonly title: string;
  readonly story: string;
  readonly prompt: string;
  readonly base: Base;
  readonly look: Look;
  readonly items: readonly Item[];
  readonly revision: number;
  readonly job: Job;
}

export interface Summary {
  readonly id: string;
  readonly title: string;
  readonly created: number;
  readonly count: number;
}

export interface KindParam {
  readonly type: 'number' | 'color' | 'choice' | 'flag' | 'text';
  readonly min: number;
  readonly max: number;
  readonly default: ParamValue;
  readonly choices: readonly string[];
}

export interface KindInfo {
  readonly id: string;
  readonly label: string;
  readonly group: string;
  readonly hint: string;
  readonly params: Record<string, KindParam>;
}

export interface Catalog {
  readonly kinds: readonly KindInfo[];
  readonly lights: readonly LightId[];
  readonly lenses: readonly LensId[];
}
