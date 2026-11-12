import React, { useEffect, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import './boot.css';

export function BootScreen({ onReady }: { onReady: () => void }) {
  const { t } = useScopedI18n('app_shell/boot');
  const [stage, setStage] = useState(0);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let readyTimer: ReturnType<typeof setTimeout>;
    let active = true;
    setFailed(false); setStage(0);
    const timeout = setTimeout(() => controller.abort(), 12000);
    async function boot() {
      try {
        const response = await fetch('/healthz', { signal: controller.signal, cache:'no-store' });
        if (!response.ok) throw new Error('health_unavailable');
        if (!active) return;
        setStage(1);
        await document.fonts.ready;
        if (!active) return;
        setStage(2);
        readyTimer = setTimeout(onReady, 650);
      } catch { if (active) setFailed(true); }
      finally { clearTimeout(timeout); }
    }
    void boot();
    return () => { active = false; controller.abort(); clearTimeout(timeout); clearTimeout(readyTimer); };
  }, [attempt, onReady]);
  return <main className="os-boot"><div className="os-boot-logo">Nuxiva<span>by NunzioTech</span></div>
    <div className="os-boot-progress" role="progressbar" aria-valuenow={failed ? 0 : (stage+1)*100/3} aria-valuemin={0} aria-valuemax={100} aria-label={t('starting')}><i style={{width:`${(stage+1)*100/3}%`}} /></div>
    <p role="status">{t(failed ? 'unavailable' : ['connecting','assets','ready'][stage])}</p>
    {failed && <button onClick={() => setAttempt(v=>v+1)}>{t('retry')}</button>}
    <footer>{t('workspace')}</footer>
  </main>;
}
