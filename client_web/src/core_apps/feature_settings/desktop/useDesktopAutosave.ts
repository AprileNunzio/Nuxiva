import { useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { saveSettings } from '../../shared/featureApi';
import { FeatureRow, FeatureSetting } from '../../shared/featureTypes';

export function useDesktopAutosave(feature: FeatureRow) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(0);
  const [failed, setFailed] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const queue = useRef(Promise.resolve());
  const latest = useRef(new Map<string, number>());
  const confirmed = useRef(new Map<string, string>());
  const current = (setting: FeatureSetting) => draft[setting.key] ?? feature.values[setting.key] ?? setting.default ?? '';

  function change(key: string, value: string) {
    const revision = (latest.current.get(key) ?? 0) + 1;
    latest.current.set(key, revision);
    setDraft((previous) => ({ ...previous, [key]: value }));
    setPending((count) => count + 1);
    setFailed(({ [key]: _, ...other }) => other);
    queue.current = queue.current.then(async () => {
      try {
        await saveSettings(feature.id, { [key]: value });
        confirmed.current.set(key, value);
        setSaved(true);
      } catch (error) {
        reportError('features_settings_failed', error);
        if (latest.current.get(key) === revision) {
          setFailed((previous) => ({ ...previous, [key]: value }));
          setDraft(({ [key]: _, ...other }) => {
            const previous = confirmed.current.get(key);
            return previous === undefined ? other : { ...other, [key]: previous };
          });
        }
      } finally {
        setPending((count) => count - 1);
      }
    });
  }

  return { current, change, pending, failed, saved };
}
