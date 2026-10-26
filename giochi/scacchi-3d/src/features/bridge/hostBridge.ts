import { gameState } from '../game/gameState';
import { GameSave } from '../game/types';

interface Controller {
  restoreGame(save: unknown): boolean;
  resetGame(): void;
}

const CHANNEL = 'nuxiva-chess';
const PUBLISH_DELAY_MS = 250;

interface HostMessage {
  channel?: unknown;
  cmd?: unknown;
  save?: unknown;
}

export function initHostBridge(controller: Controller): void {
  if (window.parent === window) return;
  const origin = window.location.origin;
  let timer = 0;
  let muted = false;

  const post = (payload: Record<string, unknown>): void => {
    window.parent.postMessage({ channel: CHANNEL, ...payload }, origin);
  };

  const publish = (): void => {
    const snap = gameState.getSnapshot();
    const save: GameSave = gameState.exportSave();
    post({
      type: 'state',
      save,
      moves: save.moves.length,
      turn: snap.turn,
      over: snap.isCheckmate || snap.isDraw,
      winner: snap.isCheckmate ? (snap.turn === 'white' ? 'black' : 'white') : null
    });
  };

  gameState.subscribe(() => {
    if (muted) return;
    window.clearTimeout(timer);
    timer = window.setTimeout(publish, PUBLISH_DELAY_MS);
  });

  window.addEventListener('message', (event: MessageEvent<HostMessage>) => {
    if (event.origin !== origin || event.source !== window.parent) return;
    const data = event.data;
    if (!data || data.channel !== CHANNEL) return;
    if (data.cmd === 'load') {
      muted = true;
      let ok = false;
      try {
        ok = controller.restoreGame(data.save);
      } catch (error) {
        console.error('Ripristino partita non riuscito', error);
      } finally {
        muted = false;
      }
      post({ type: 'loaded', ok });
      publish();
    } else if (data.cmd === 'new') {
      controller.resetGame();
    }
  });

  post({ type: 'ready' });
}
