export interface Floor {
  readonly id: string;
  readonly name: string;
  readonly level: number;
}

export interface Room {
  readonly id: string;
  readonly name: string;
  readonly floor_id: string;
  readonly ha_area: string;
  readonly aliases: readonly string[];
}

export interface Placement {
  readonly key: string;
  readonly room_id: string;
  readonly senses: readonly string[];
}

export interface PlaceDevice {
  readonly key: string;
  readonly name: string;
  readonly kind: string;
  readonly hint: string;
  readonly senses: readonly string[];
  readonly room_id: string;
}

export interface PersonLocation {
  readonly slug: string;
  readonly name: string;
  readonly [key: string]: unknown;
}

export interface PlacesOverview {
  readonly floors: readonly Floor[];
  readonly rooms: readonly Room[];
  readonly placements: readonly Placement[];
  readonly devices: readonly PlaceDevice[];
  readonly people: readonly PersonLocation[];
}
