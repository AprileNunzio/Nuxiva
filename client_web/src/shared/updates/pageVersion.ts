const ENTRY = /<script[^>]*\stype="module"[^>]*\ssrc="([^"]+)"/i;
const FALLBACK_ENTRY = /<script[^>]*\ssrc="([^"]+)"[^>]*\stype="module"/i;

export function entryOf(html: string): string | null {
  const match = ENTRY.exec(html) ?? FALLBACK_ENTRY.exec(html);
  return match ? match[1] : null;
}

export function loadedEntry(doc: Document = document): string | null {
  const script = doc.querySelector<HTMLScriptElement>('script[type="module"][src]');
  return script ? new URL(script.src, doc.baseURI).pathname : null;
}

export function isNewer(loaded: string | null, served: string | null): boolean {
  if (!loaded || !served) {
    return false;
  }
  return new URL(served, 'http://local').pathname !== loaded;
}
