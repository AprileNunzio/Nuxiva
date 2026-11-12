const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const assert = require('node:assert/strict');

function load(path) {
  const module = { exports: {} };
  vm.runInNewContext(
    ts.transpileModule(readFileSync(resolve(__dirname, '../src', path), 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS },
    }).outputText,
    { module, exports: module.exports }
  );
  return module.exports;
}

const { evaluateSpatialArbitration } = load('shared/spatial/spatialArbiter.ts');
const {
  IDLE_CONTEXT_MANIFEST,
  CHESS_CONTEXT_MANIFEST,
  CAD3D_CONTEXT_MANIFEST,
} = load('shared/spatial/contextManifest.ts');

const p0Event = {
  id: 'evt-smoke',
  priority: 'P0_CRITICAL',
  titleKey: 'alarm_fire',
  messageKey: 'sensor_smoke',
  sourceModule: 'sensor.smoke',
  timestampMs: 1000,
};

const resP0Chess = evaluateSpatialArbitration(p0Event, CHESS_CONTEXT_MANIFEST);
assert.equal(resP0Chess.action, 'PREEMPTION_TOTAL');
assert.equal(resP0Chess.suspendPrimaryStage, true);
assert.equal(resP0Chess.targetLayer, 'Z4_CriticalInterrupt');
assert.equal(resP0Chess.shouldDefer, false);
assert.equal(resP0Chess.reasonCode, 'p0_preemption');

const resP0Cad = evaluateSpatialArbitration(p0Event, CAD3D_CONTEXT_MANIFEST);
assert.equal(resP0Cad.action, 'PREEMPTION_TOTAL');
assert.equal(resP0Cad.suspendPrimaryStage, true);

const p1Event = {
  id: 'evt-intercom',
  priority: 'P1_HIGH',
  titleKey: 'intercom_ring',
  messageKey: 'doorbell_event',
  sourceModule: 'intercom',
  timestampMs: 1001,
};

const resP1Chess = evaluateSpatialArbitration(p1Event, CHESS_CONTEXT_MANIFEST);
assert.equal(resP1Chess.action, 'SMART_PIP');
assert.equal(resP1Chess.assignedSafeZone, 'TOP_RIGHT');
assert.equal(resP1Chess.suspendPrimaryStage, false);

const resP1Cad = evaluateSpatialArbitration(p1Event, CAD3D_CONTEXT_MANIFEST);
assert.equal(resP1Cad.action, 'VOICE_INTERJECT');
assert.equal(resP1Cad.targetMorphology, 'AMBIENT_STREAM');
assert.equal(resP1Cad.suspendPrimaryStage, false);

const p2Event = {
  id: 'evt-render',
  priority: 'P2_NORMAL',
  titleKey: 'render_done',
  messageKey: 'mesh_exported',
  sourceModule: 'blender',
  timestampMs: 1002,
};

const resP2Chess = evaluateSpatialArbitration(p2Event, CHESS_CONTEXT_MANIFEST);
assert.equal(resP2Chess.action, 'DEFERRAL');
assert.equal(resP2Chess.shouldDefer, true);

const resP2Idle = evaluateSpatialArbitration(p2Event, IDLE_CONTEXT_MANIFEST);
assert.equal(resP2Idle.action, 'SMART_PIP');
assert.equal(resP2Idle.shouldDefer, false);
