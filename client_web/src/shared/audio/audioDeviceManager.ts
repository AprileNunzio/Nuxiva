export type DeviceSelectionMode = 'HIERARCHICAL_FALLBACK' | 'MULTI_MIC_PROXIMITY';

export interface AudioDevice {
  readonly id: string;
  readonly nameKey: string;
  readonly priority: number;
  readonly isConnected: boolean;
  readonly isBluetooth: boolean;
  readonly batteryLevel?: number;
}

export interface SatelliteAudioReport {
  readonly satelliteId: string;
  readonly timestampMs: number;
  readonly snrDb: number;
  readonly energyRms: number;
  readonly speechConfidence: number;
}

export interface MediaPlaybackState {
  readonly isActive: boolean;
  readonly sourceId: string;
  readonly streamType: 'NONE' | 'MUSIC' | 'IPTV_LIVE' | 'VIDEO_ON_DEMAND';
  readonly volumeNormalized: number;
}

export class AudioDeviceManager {
  private devices: AudioDevice[] = [];
  private mode: DeviceSelectionMode = 'HIERARCHICAL_FALLBACK';
  private activeWinnerId: string | null = null;
  private lastWinningScore = 0;
  private readonly hysteresisMargin: number;

  public constructor(hysteresisMargin = 3.5) {
    this.hysteresisMargin = hysteresisMargin;
  }

  public setMode(mode: DeviceSelectionMode): void {
    this.mode = mode;
  }

  public getMode(): DeviceSelectionMode {
    return this.mode;
  }

  public registerDevice(device: AudioDevice): void {
    this.devices = this.devices.filter(d => d.id !== device.id);
    this.devices.push(device);
    this.devices.sort((a, b) => a.priority - b.priority);
  }

  public updateDeviceConnection(deviceId: string, isConnected: boolean): void {
    const dev = this.devices.find(d => d.id === deviceId);
    if (dev) {
      const idx = this.devices.indexOf(dev);
      this.devices[idx] = { ...dev, isConnected };
    }
  }

  public resolveActiveDevice(): AudioDevice | null {
    const target = this.devices.find(d => d.isConnected);
    return target ?? null;
  }

  public electBestSource(reports: readonly SatelliteAudioReport[]): string | null {
    if (reports.length === 0) {
      return this.activeWinnerId;
    }

    let bestId: string | null = null;
    let bestScore = -1;

    for (const report of reports) {
      const snrPart = Math.max(0, Math.min(50, report.snrDb)) * 0.45;
      const energyPart = Math.max(0, Math.min(50, report.energyRms * 100)) * 0.35;
      const confPart = Math.max(0, Math.min(1, report.speechConfidence)) * 20;
      const score = snrPart + energyPart + confPart;

      if (score > bestScore) {
        bestScore = score;
        bestId = report.satelliteId;
      }
    }

    if (this.activeWinnerId && bestId) {
      if (bestId !== this.activeWinnerId) {
        if (bestScore > this.lastWinningScore + this.hysteresisMargin) {
          this.activeWinnerId = bestId;
          this.lastWinningScore = bestScore;
        }
      } else {
        this.lastWinningScore = bestScore;
      }
    } else if (bestId) {
      this.activeWinnerId = bestId;
      this.lastWinningScore = bestScore;
    }

    return this.activeWinnerId;
  }

  public reset(): void {
    this.activeWinnerId = null;
    this.lastWinningScore = 0;
  }
}
