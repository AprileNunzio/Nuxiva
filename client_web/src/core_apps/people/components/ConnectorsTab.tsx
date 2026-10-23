import React, { useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { Connectors, fetchConnectors } from '../data/connectorsApi';
import { usePeopleI18n } from '../scope';
import { GoogleCard } from './GoogleCard';
import { TelegramCard } from './TelegramCard';

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const ConnectorsTab: React.FC<Props> = ({ slug, busy, run }) => {
  const { t } = usePeopleI18n();
  const [state, setState] = useState<Connectors | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchConnectors(slug, controller.signal)
      .then(setState)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_connectors_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  useEffect(() => {
    if (!state?.telegram?.pairCode && !state?.google?.pending) {
      return undefined;
    }
    const timer = window.setInterval(() => setTick((v) => v + 1), 5000);
    return () => window.clearInterval(timer);
  }, [state?.telegram?.pairCode, state?.google?.pending]);

  const act = async (key: string, task: () => Promise<unknown>, code: string) => {
    const ok = await run(key, task, code);
    setTick((v) => v + 1);
    return ok;
  };

  if (!state) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-slate-400">{t('connectors_hint')}</p>
      <div className="grid gap-3 xl:grid-cols-2">
        {state.telegram && <TelegramCard slug={slug} state={state.telegram} busy={busy} run={act} />}
        {state.google && <GoogleCard slug={slug} state={state.google} busy={busy} run={act} />}
      </div>
    </div>
  );
};
