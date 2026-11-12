import { useCallback, useEffect, useMemo, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { ControlScope } from '../../console/data/nodeConsoleApi';
import { SettingSpec, effectiveValue, serialize } from '../data/schema';
import { SettingsMap, fetchSettings, saveSettings } from '../data/settingsApi';

export type SettingDraft = Readonly<Record<string, boolean | number | string>>;

export interface NodeSettingsState {
  readonly loading: boolean;
  readonly unavailable: boolean;
  readonly values: SettingDraft;
  readonly inherited: ReadonlySet<string>;
  readonly dirty: boolean;
  readonly saving: boolean;
  readonly saved: boolean;
  readonly change: (key: string, value: boolean | number | string) => void;
  readonly save: () => Promise<void>;
  readonly reset: () => void;
}

function toDraft(specs: readonly SettingSpec[], map: SettingsMap): SettingDraft {
  return Object.fromEntries(specs.map((spec) => [spec.key, effectiveValue(spec, map[spec.key]?.value ?? '')]));
}

export function useNodeSettings(nodeId: string, scope: ControlScope, specs: readonly SettingSpec[]): NodeSettingsState {
  const [remote, setRemote] = useState<SettingsMap | null>(null);
  const [draft, setDraft] = useState<SettingDraft>({});
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetchSettings(nodeId, scope, controller.signal)
      .then((map) => {
        setRemote(map);
        setDraft(toDraft(specs, map));
        setUnavailable(false);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setUnavailable(true);
          if (scope !== 'mesh') {
            reportError('node_settings_unavailable', cause);
          }
        }
      })
      .finally(() => !controller.signal.aborted && setLoading(false));
    return () => controller.abort();
  }, [nodeId, scope, specs]);

  const baseline = useMemo(() => (remote ? toDraft(specs, remote) : {}), [remote, specs]);
  const inherited = useMemo(
    () => new Set(specs.filter((spec) => remote && scope === 'paired' && !remote[spec.key]?.custom).map((spec) => spec.key)),
    [remote, specs, scope],
  );
  const dirty = specs.some((spec) => draft[spec.key] !== baseline[spec.key]);

  const change = useCallback((key: string, value: boolean | number | string) => {
    setSaved(false);
    setDraft((current) => ({ ...current, [key]: value }));
  }, []);

  const reset = useCallback(() => setDraft(baseline), [baseline]);

  const save = useCallback(async () => {
    const updates = Object.fromEntries(
      specs.filter((spec) => draft[spec.key] !== baseline[spec.key]).map((spec) => [spec.key, serialize(spec, draft[spec.key])]),
    );
    setSaving(true);
    try {
      await saveSettings(nodeId, scope, updates);
      setRemote((current) => ({
        ...(current ?? {}),
        ...Object.fromEntries(Object.entries(updates).map(([key, value]) => [key, { value, inherited: '', custom: true }])),
      }));
      setSaved(true);
    } catch (cause) {
      reportError('node_settings_save_failed', cause);
    } finally {
      setSaving(false);
    }
  }, [draft, baseline, nodeId, scope, specs]);

  return { loading, unavailable, values: draft, inherited, dirty, saving, saved, change, save, reset };
}
