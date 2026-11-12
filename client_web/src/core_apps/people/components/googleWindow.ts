const GOOGLE = /^https:\/\/accounts\.google\.com\//;

export function reserveWindow(): Window | null {
  const win = window.open('', '_blank');
  if (win) {
    win.opener = null;
  }
  return win;
}

export function sendWindow(win: Window | null, url: string): boolean {
  if (!GOOGLE.test(url)) {
    win?.close();
    return false;
  }
  if (win && !win.closed) {
    win.location.replace(url);
    return true;
  }
  return window.open(url, '_blank', 'noopener,noreferrer') !== null;
}

export function dropWindow(win: Window | null): void {
  if (win && !win.closed) {
    win.close();
  }
}
