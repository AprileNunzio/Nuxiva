type Listener = () => void;

const listeners = new Set<Listener>();

export function emitSessionExpired(): void {
  listeners.forEach((listener) => listener());
}

export function onSessionExpired(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
