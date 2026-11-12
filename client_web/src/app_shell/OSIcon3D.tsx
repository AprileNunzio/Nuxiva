import React, { useEffect, useState } from 'react';
import { adminPath } from '../shared/http/basePath';
const pending = new Map<string, Promise<void>>();
export function prefetchIcon3D(source: string) {
  if (!pending.has(source)) pending.set(source, new Promise<void>(resolve => {
    const image = new Image(); image.onload = () => resolve(); image.onerror = () => { pending.delete(source); resolve(); }; image.src = source;
  }));
  return pending.get(source)!;
}
export function OSIcon3D({ name, source: raw, symbol, size = 'md' }: { name: string; source?: string; symbol?: string; size?: 'sm' | 'md' | 'lg' }) {
  const source = raw ? adminPath(raw) : raw;
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); if (source) void prefetchIcon3D(source); }, [source]);
  return source && !failed ? <img className={`os-icon os-icon-${size}`} src={source} alt="" aria-hidden="true" draggable={false} onError={() => setFailed(true)} />
    : <span className={`os-icon os-icon-${size} os-app-mark`} aria-hidden="true">{symbol?.trim() || name.slice(0, 1).toLocaleUpperCase()}</span>;
}
