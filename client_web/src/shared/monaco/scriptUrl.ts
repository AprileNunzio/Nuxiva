export function sameOriginScriptUrl(value: string, origin: string, base: string): string {
  const url = new URL(value, base);
  if (url.origin !== origin) {
    throw new TypeError('monaco.worker.origin');
  }
  return url.href;
}
