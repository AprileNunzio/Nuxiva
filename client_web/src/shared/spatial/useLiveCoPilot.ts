import { useCallback, useState } from 'react';
import { AssistantMorphology } from './contextManifest';

export type CoPilotActionKind =
  | 'SpeakInsight'
  | 'SuggestMove'
  | 'SilentObserve'
  | 'PreemptAlert';

export interface CoPilotAction {
  actionKind: CoPilotActionKind;
  insightKey: string;
  suggestedMove?: string | null;
  confidence: number;
  targetMorphology: AssistantMorphology;
  targetLayer: string;
}

export interface LiveCoPilotState {
  isLive: boolean;
  gameId: string;
  turnCount: number;
  historyMoves: string[];
  lastBoardState: string;
  currentAction: CoPilotAction | null;
}

export function evaluateCoPilotMove(
  turnCount: number,
  moveKey: string,
  _boardState: string
): CoPilotAction {
  const nextTurn = turnCount + 1;
  if (nextTurn <= 2) {
    return {
      actionKind: 'SpeakInsight',
      insightKey: 'copilot.opening_acknowledged',
      suggestedMove: moveKey,
      confidence: 0.95,
      targetMorphology: 'FLOATING_ORB',
      targetLayer: 'Z2ContextualHud',
    };
  }

  if (nextTurn % 3 === 0) {
    return {
      actionKind: 'SuggestMove',
      insightKey: 'copilot.tactical_suggestion',
      suggestedMove: 'e2e4',
      confidence: 0.88,
      targetMorphology: 'FLOATING_ORB',
      targetLayer: 'Z2ContextualHud',
    };
  }

  return {
    actionKind: 'SilentObserve',
    insightKey: 'copilot.turn_observed',
    suggestedMove: null,
    confidence: 0.9,
    targetMorphology: 'AMBIENT_STREAM',
    targetLayer: 'Z2ContextualHud',
  };
}

export function useLiveCoPilot() {
  const [state, setState] = useState<LiveCoPilotState>({
    isLive: false,
    gameId: '',
    turnCount: 0,
    historyMoves: [],
    lastBoardState: '',
    currentAction: null,
  });

  const startSession = useCallback((gameId: string, initialState: string) => {
    const startAction: CoPilotAction = {
      actionKind: 'SpeakInsight',
      insightKey: 'copilot.game_started',
      suggestedMove: null,
      confidence: 1.0,
      targetMorphology: 'FLOATING_ORB',
      targetLayer: 'Z2ContextualHud',
    };

    setState({
      isLive: true,
      gameId,
      turnCount: 0,
      historyMoves: [],
      lastBoardState: initialState,
      currentAction: startAction,
    });

    return startAction;
  }, []);

  const applyMove = useCallback(
    (moveKey: string, boardState: string) => {
      let action: CoPilotAction = {
        actionKind: 'SilentObserve',
        insightKey: 'copilot.inactive',
        suggestedMove: null,
        confidence: 0.0,
        targetMorphology: 'AMBIENT_STREAM',
        targetLayer: 'Z0Ambient',
      };

      setState((prev) => {
        if (!prev.isLive) {
          return prev;
        }

        action = evaluateCoPilotMove(prev.turnCount, moveKey, boardState);
        return {
          ...prev,
          turnCount: prev.turnCount + 1,
          historyMoves: [...prev.historyMoves, moveKey],
          lastBoardState: boardState,
          currentAction: action,
        };
      });

      return action;
    },
    []
  );

  const endSession = useCallback(() => {
    const endAction: CoPilotAction = {
      actionKind: 'SpeakInsight',
      insightKey: 'copilot.game_ended',
      suggestedMove: null,
      confidence: 1.0,
      targetMorphology: 'CORE_HERO',
      targetLayer: 'Z3Assistant',
    };

    setState((prev) => ({
      ...prev,
      isLive: false,
      currentAction: endAction,
    }));

    return endAction;
  }, []);

  return {
    isLive: state.isLive,
    gameId: state.gameId,
    turnCount: state.turnCount,
    historyMoves: state.historyMoves,
    lastBoardState: state.lastBoardState,
    currentAction: state.currentAction,
    startSession,
    applyMove,
    endSession,
  };
}
