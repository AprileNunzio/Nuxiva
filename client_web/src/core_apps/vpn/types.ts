export interface VpnStatus {
  readonly connected: boolean;
  readonly error?: string;
}

export interface VpnProfile {
  readonly id: string;
  readonly name: string;
  readonly kind: string;
  readonly role: string;
  readonly autostart: boolean;
  readonly kill_switch: boolean;
  readonly wanted: boolean;
  readonly status: VpnStatus;
  readonly settings: Readonly<Record<string, unknown>>;
}

export interface VpnOverview {
  readonly profiles: readonly VpnProfile[];
  readonly tools: Readonly<Record<string, boolean>>;
  readonly guard_error: string;
}

export interface VpnDraft {
  readonly kind: string;
  readonly name: string;
  readonly role: string;
  readonly import?: string;
  readonly settings?: Readonly<Record<string, unknown>>;
  readonly secrets?: Readonly<Record<string, string>>;
}

export interface PeerResult {
  readonly peer: { readonly id: string; readonly name: string };
  readonly config: string;
}
