export const BRAIN_CHANNEL = 'nuxiva-brain';
export const BRAIN_EVENT = 'nuxiva:brain-changed';

export interface BrainChange {
  readonly source: string;
  readonly at: number;
}

type Listener = (change: BrainChange) => void;

const channel: BroadcastChannel | null = typeof BroadcastChannel === 'function' ? new BroadcastChannel(BRAIN_CHANNEL) : null;

const isChange = (value: unknown): value is BrainChange =>
  typeof value === 'object' &&
  value !== null &&
  typeof (value as BrainChange).source === 'string' &&
  typeof (value as BrainChange).at === 'number';

export function newSourceId(): string {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

export function publishBrainChange(source: string): BrainChange {
  const change: BrainChange = { source, at: Date.now() };
  channel?.postMessage(change);
  window.dispatchEvent(new CustomEvent<BrainChange>(BRAIN_EVENT, { detail: change }));
  return change;
}

export function subscribeBrainChanges(source: string, listener: Listener): () => void {
  const accept = (value: unknown) => {
    if (isChange(value) && value.source !== source) {
      listener(value);
    }
  };
  const onMessage = (event: MessageEvent) => accept(event.data);
  const onEvent = (event: Event) => accept((event as CustomEvent<unknown>).detail);
  channel?.addEventListener('message', onMessage);
  window.addEventListener(BRAIN_EVENT, onEvent);
  return () => {
    channel?.removeEventListener('message', onMessage);
    window.removeEventListener(BRAIN_EVENT, onEvent);
  };
}
