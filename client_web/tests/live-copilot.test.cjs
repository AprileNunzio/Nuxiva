const test = require('node:test');
const assert = require('node:assert/strict');

function evaluateCoPilotMove(turnCount, moveKey, _boardState) {
  const nextTurn = turnCount + 1;
  if (nextTurn <= 2) {
    return {
      actionKind: 'SpeakInsight',
      insightKey: 'copilot.opening_acknowledged',
      suggestedMove: moveKey,
      confidence: 0.95,
      targetMorphology: 'FloatingOrb',
      targetLayer: 'Z2ContextualHud',
    };
  }

  if (nextTurn % 3 === 0) {
    return {
      actionKind: 'SuggestMove',
      insightKey: 'copilot.tactical_suggestion',
      suggestedMove: 'e2e4',
      confidence: 0.88,
      targetMorphology: 'FloatingOrb',
      targetLayer: 'Z2ContextualHud',
    };
  }

  return {
    actionKind: 'SilentObserve',
    insightKey: 'copilot.turn_observed',
    suggestedMove: null,
    confidence: 0.9,
    targetMorphology: 'AmbientStream',
    targetLayer: 'Z2ContextualHud',
  };
}

test('evaluateCoPilotMove acknowledges opening moves', () => {
  const action1 = evaluateCoPilotMove(0, 'e2e4', 'fen_1');
  assert.equal(action1.actionKind, 'SpeakInsight');
  assert.equal(action1.insightKey, 'copilot.opening_acknowledged');
  assert.equal(action1.suggestedMove, 'e2e4');

  const action2 = evaluateCoPilotMove(1, 'e7e5', 'fen_2');
  assert.equal(action2.actionKind, 'SpeakInsight');
  assert.equal(action2.insightKey, 'copilot.opening_acknowledged');
});

test('evaluateCoPilotMove suggests moves periodically', () => {
  const action3 = evaluateCoPilotMove(2, 'g1f3', 'fen_3');
  assert.equal(action3.actionKind, 'SuggestMove');
  assert.equal(action3.insightKey, 'copilot.tactical_suggestion');
  assert.equal(action3.suggestedMove, 'e2e4');

  const action4 = evaluateCoPilotMove(3, 'b8c6', 'fen_4');
  assert.equal(action4.actionKind, 'SilentObserve');
  assert.equal(action4.insightKey, 'copilot.turn_observed');
});
