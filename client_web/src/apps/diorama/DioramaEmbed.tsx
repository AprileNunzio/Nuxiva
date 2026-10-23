import React, { useEffect, useRef, useState } from 'react';
import { getJson } from '../../core_apps/shared/http';
import { BuildProgress } from './components/BuildProgress';
import { Viewport } from './components/Viewport';
import { parseDiorama } from './api';
import type { Diorama } from './types';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

const ID = /^[0-9a-f]{8}$/;
const FAST_MS = 800;
const SLOW_MS = 4000;

export const DioramaEmbed: React.FC = () => {
  const { t } = useScopedI18n('apps/diorama');
  const id = new URLSearchParams(window.location.search).get('id') ?? '';
  const [diorama, setDiorama] = useState<Diorama | null>(null);
  const [failed, setFailed] = useState(false);
  const first = useRef(true);
  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    if (!ID.test(id)) {
      setFailed(true);
      return undefined;
    }
    let alive = true;
    let timer = 0;
    const pull = async () => {
      let delay = SLOW_MS;
      try {
        const next = parseDiorama(await getJson(`/api/diorama/${id}/display`));
        if (!alive) return;
        setDiorama((prev) => (prev && prev.revision === next.revision && prev.job.state === next.job.state && prev.job.stage === next.job.stage ? prev : next));
        if (first.current) {
          first.current = false;
          setAnimate(next.job.state === 'building');
        } else {
          setAnimate(true);
        }
        delay = next.job.state === 'building' ? FAST_MS : SLOW_MS;
        setFailed(false);
      } catch {
        if (alive) setFailed(true);
      }
      if (alive) timer = window.setTimeout(pull, delay);
    };
    void pull();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [id]);

  if (failed && !diorama) return <div className="flex h-screen items-center justify-center bg-white text-sm text-slate-500">{t('error_request_failed')}</div>;
  if (!diorama) return <div className="h-screen w-screen bg-gradient-to-b from-white to-slate-100" />;
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-white">
      <Viewport diorama={diorama} animate={animate} selected="" onPick={() => undefined} onSnapshot={() => undefined} unsupported={t('webgl_unsupported')} />
      <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-center p-4">
        <div className="rounded-2xl border border-slate-200 bg-white/85 px-5 py-2 text-center shadow-md backdrop-blur">
          <p className="text-sm font-bold text-slate-900">{diorama.title || t('untitled')}</p>
          {diorama.story && <p className="max-w-xl text-[11px] text-slate-500">{diorama.story}</p>}
        </div>
      </div>
      {diorama.job.state === 'building' && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center p-4">
          <BuildProgress job={diorama.job} count={diorama.items.length} label={(stage) => t(`stage_${stage}`)} itemsLabel={t('items')} fallbackLabel={t('mode_template')} />
        </div>
      )}
    </div>
  );
};

export default DioramaEmbed;
