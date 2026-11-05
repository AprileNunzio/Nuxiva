import type { ConsoleLine } from './types';

export interface FormattedLine {
  readonly key: string;
  readonly time: string;
  readonly level: ConsoleLine['level'];
  readonly stage: string | null;
  readonly messageKey: string;
  readonly params: Readonly<Record<string, string>>;
  readonly detail: string;
}

const pad = (value: number) => String(value).padStart(2, '0');

export function clockTime(epochSeconds: number): string {
  const date = new Date(epochSeconds * 1000);
  return Number.isNaN(date.getTime()) ? '--:--:--' : `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function formatLine(line: ConsoleLine, index: number): FormattedLine {
  const params: Record<string, string> = {};
  const detail: string[] = [];
  for (const [name, value] of Object.entries(line.args ?? {})) {
    if (value === null || value === undefined || value === '') continue;
    const text = String(value);
    params[name] = text;
    detail.push(`${name}=${text}`);
  }
  return {
    key: `${line.t}-${index}`,
    time: clockTime(line.t),
    level: line.level,
    stage: line.stage,
    messageKey: `log_${line.code}`,
    params,
    detail: detail.join(' '),
  };
}

export function stageDuration(started: number | null, finished: number | null, now: number): string | null {
  if (started === null) return null;
  const seconds = Math.max(0, (finished ?? now) - started);
  return seconds < 60 ? `${seconds.toFixed(1)}s` : `${Math.floor(seconds / 60)}m${pad(Math.round(seconds % 60))}s`;
}
