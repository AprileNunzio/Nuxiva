const SCRIPT_TAG = /<script\b[^>]*>/gi;
const MODULE_TYPE = /\stype\s*=\s*["']module["']/i;
const SOURCE = /\ssrc\s*=\s*["']([^"']+)["']/i;
const MOUNT = '/admin';

function pathOf(source: string): string | null {
  try {
    return new URL(source, 'http://local').pathname;
  } catch {
    return null;
  }
}

export function bundleDir(entry: string | null): string | null {
  if (!entry) {
    return null;
  }
  const cut = entry.lastIndexOf('/');
  return cut > 0 ? entry.slice(0, cut + 1) : null;
}

export function appRoot(pathname: string): string {
  return pathname === MOUNT || pathname.startsWith(`${MOUNT}/`) ? `${MOUNT}/` : '/';
}

export function entryOf(html: string, dir: string | null = null): string | null {
  for (const match of html.matchAll(SCRIPT_TAG)) {
    const tag = match[0];
    if (!MODULE_TYPE.test(tag)) {
      continue;
    }
    const source = SOURCE.exec(tag);
    const path = source ? pathOf(source[1]) : null;
    if (path && (!dir || path.startsWith(dir))) {
      return path;
    }
  }
  return null;
}

export function loadedEntry(doc: Document = document): string | null {
  const script = doc.querySelector<HTMLScriptElement>('script[type="module"][src]');
  return script ? new URL(script.src, doc.baseURI).pathname : null;
}

export function isNewer(loaded: string | null, served: string | null): boolean {
  if (!loaded || !served) {
    return false;
  }
  const dir = bundleDir(loaded);
  const target = pathOf(served);
  return Boolean(dir && target && target.startsWith(dir) && target !== loaded);
}
