const assert = require('assert');

class AudioDeviceManager {
  constructor(hysteresisMargin = 3.5) {
    this.devices = [];
    this.mode = 'HIERARCHICAL_FALLBACK';
    this.activeWinnerId = null;
    this.lastWinningScore = 0;
    this.hysteresisMargin = hysteresisMargin;
  }

  setMode(mode) {
    this.mode = mode;
  }

  getMode() {
    return this.mode;
  }

  registerDevice(device) {
    this.devices = this.devices.filter(d => d.id !== device.id);
    this.devices.push(device);
    this.devices.sort((a, b) => a.priority - b.priority);
  }

  updateDeviceConnection(deviceId, isConnected) {
    const dev = this.devices.find(d => d.id === deviceId);
    if (dev) {
      dev.isConnected = isConnected;
    }
  }

  resolveActiveDevice() {
    return this.devices.find(d => d.isConnected) || null;
  }

  electBestSource(reports) {
    if (!reports || reports.length === 0) {
      return this.activeWinnerId;
    }

    let bestId = null;
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
}

function runTests() {
  const manager = new AudioDeviceManager();

  const bt = {
    id: 'bt_buds',
    nameKey: 'device.bluetooth.buds',
    priority: 1,
    isConnected: true,
    isBluetooth: true,
    batteryLevel: 90,
  };

  const builtin = {
    id: 'builtin_mic',
    nameKey: 'device.builtin.array',
    priority: 2,
    isConnected: true,
    isBluetooth: false,
  };

  manager.registerDevice(bt);
  manager.registerDevice(builtin);

  let active = manager.resolveActiveDevice();
  assert(active !== null);
  assert.strictEqual(active.id, 'bt_buds');

  manager.updateDeviceConnection('bt_buds', false);
  active = manager.resolveActiveDevice();
  assert(active !== null);
  assert.strictEqual(active.id, 'builtin_mic');

  manager.setMode('MULTI_MIC_PROXIMITY');
  assert.strictEqual(manager.getMode(), 'MULTI_MIC_PROXIMITY');

  const near = {
    satelliteId: 'sat_desk',
    timestampMs: 1000,
    snrDb: 25.0,
    energyRms: 0.05,
    speechConfidence: 0.9,
  };

  const far = {
    satelliteId: 'sat_tv_room',
    timestampMs: 1000,
    snrDb: 7.0,
    energyRms: 0.01,
    speechConfidence: 0.25,
  };

  const winner = manager.electBestSource([near, far]);
  assert.strictEqual(winner, 'sat_desk');
}

runTests();
