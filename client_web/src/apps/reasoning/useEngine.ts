import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useOSApp } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { statusUrl, tracesUrl } from './api';
import type { Status, Trace } from './types';

export function useEngine() {
  const os = useOSApp();
  const { t, lang } = useScopedI18n('apps/reasoning');
  const status = useResource<Status>(statusUrl, 10000);
  const traces = useResource<{ traces: Trace[] }>(tracesUrl, 10000);
  const { busy, run } = useAction();
  const percent = (bps: number | undefined) => `${((bps ?? 0) / 100).toLocaleString(lang, { maximumFractionDigits: 1 })}%`;
  const time = (ms: number) => new Date(ms).toLocaleString(lang);
  return { os, t, lang, status: status.data, statusResource: status, traces: traces.data?.traces ?? [], busy, run, percent, time };
}

export type EngineModel = ReturnType<typeof useEngine>;
