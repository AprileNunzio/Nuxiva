export interface Entity {
  readonly entity_id: string;
  readonly name: string;
  readonly domain: string;
  readonly area_id?: string;
  readonly state: string;
  readonly controllable: boolean;
  readonly hidden?: boolean;
  readonly category?: string;
  readonly attrs: Record<string, unknown>;
}

export interface Floor {
  readonly floor_id: string;
  readonly name: string;
  readonly level?: number;
}

export interface Area {
  readonly area_id: string;
  readonly name: string;
  readonly floor_id?: string;
}

export interface RoomItem {
  readonly area_id: string;
  readonly room_id: string;
  readonly name: string;
  readonly floor_id: string;
  readonly floor_name: string;
  readonly temperature?: number;
  readonly humidity?: number;
  readonly occupied: boolean;
  readonly last_motion?: number;
  readonly open: readonly string[];
  readonly entities: ReadonlyArray<{
    readonly entity_id: string;
    readonly name: string;
    readonly domain: string;
    readonly state: string;
  }>;
  readonly entities_count: number;
}

export interface AutomationItem {
  readonly id: string;
  readonly entity_id: string;
  readonly alias: string;
  readonly state: string;
  readonly last_triggered?: string | null;
  readonly description?: string;
}

export interface PowerSensor {
  readonly entity_id: string;
  readonly name: string;
  readonly state: number | null;
  readonly unit: string;
  readonly power_w?: number;
  readonly area_id?: string;
  readonly raw_state?: string;
}

export interface EnergySensor {
  readonly entity_id: string;
  readonly name: string;
  readonly state: number | null;
  readonly unit: string;
  readonly energy_kwh?: number;
  readonly raw_state?: string;
}

export interface EnergyData {
  readonly power_sensors: readonly PowerSensor[];
  readonly energy_sensors: readonly EnergySensor[];
  readonly solar_sensors: readonly PowerSensor[];
  readonly summary: {
    readonly total_power_w: number | null;
    readonly total_solar_w: number | null;
    readonly net_power_w: number | null;
  };
}

export interface AssistResult {
  readonly ok: boolean;
  readonly speech: string;
  readonly source?: string;
  readonly response?: Record<string, unknown>;
  readonly error?: string;
}

export interface HomeOverview {
  readonly status: string;
  readonly error?: string;
  readonly ha_version?: string;
  readonly ha_name?: string;
  readonly devices_count?: number;
  readonly entities_count?: number;
  readonly connected_at?: number;
  readonly synced_at?: number;
  readonly url?: string;
}
