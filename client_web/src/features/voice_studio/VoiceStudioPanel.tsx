import React, { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { ConfirmDialog } from '../../shared/ui/ConfirmDialog';
import { Btn, Empty, Pill } from '../../core_apps/shared/kit';
import { StudioCreator } from './StudioCreator';
import { StudioStatus, StudioVoice, deleteVoice, fetchStudio, previewVoice, retryStudio, useVoice } from './studioApi';

export const VoiceStudioPanel: React.FC = () => {
  const { t, lang } = useScopedI18n('features/voice_studio');
  const [status, setStatus] = useState<StudioStatus | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const [audio, setAudio] = useState('');
  const [removing, setRemoving] = useState<StudioVoice | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchStudio(controller.signal).then(setStatus).catch((cause) => !controller.signal.aborted && setError(String(cause.message ?? cause)));
    return () => controller.abort();
  }, [tick]);
  useEffect(() => () => { if (audio) URL.revokeObjectURL(audio); }, [audio]);
  const run = async (task: () => Promise<unknown>) => {
    setBusy(true); setError('');
    try { await task(); setTick((current) => current + 1); return true; }
    catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); return false; }
    finally { setBusy(false); }
  };
  return (
    <section className="min-w-0 rounded-xl border border-cyan-500/30 p-3 sm:p-4" aria-label={t('title')}>
      <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-cyan-100">{t('title')}</h3><Btn tone="slate" busy={busy} onClick={() => setTick((current) => current + 1)}><RefreshCw className="h-4 w-4" aria-hidden="true" />{t('refresh')}</Btn></div>
      {error && <p role="alert" className="mt-3 break-words rounded-xl bg-rose-500/10 p-3 text-xs text-rose-200">{error}</p>}
      {!status ? <p className="mt-3 text-xs text-slate-400">{t('loading')}</p> : <>
        <div className="mt-3 flex flex-wrap gap-2"><Pill tone={status.online ? 'emerald' : 'amber'}>{t(status.online ? 'online' : status.enabled ? 'offline' : 'disabled')}</Pill><Pill>{t(status.where === 'remote' ? 'remote' : 'local')}</Pill></div>
        {!status.enabled && <p className="mt-3 text-xs text-slate-400">{t('enable_hint')}</p>}
        {status.enabled && !status.online && <div className="mt-3 space-y-2"><p className="break-words text-xs text-amber-100">{status.error || status.install?.error || status.install?.message || t('waiting')}</p>{status.where !== 'remote' && <Btn busy={busy} onClick={() => void run(retryStudio)}>{t('retry')}</Btn>}</div>}
        {status.online && <>
          {status.voices.length === 0 ? <Empty>{t('empty')}</Empty> : <ul className="mt-3 space-y-2">{status.voices.map((voice) => <li key={voice.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-950 p-3">
            <span className="min-w-0 flex-1 break-words text-sm">{voice.name} {status.nuxiva_voice === voice.id && <Pill tone="emerald">{t('selected')}</Pill>}</span>
            <Btn tone="slate" busy={busy} onClick={() => void run(async () => setAudio(URL.createObjectURL(await previewVoice(voice.id, lang))))}>{t('preview')}</Btn>
            <Btn busy={busy} onClick={() => void run(() => useVoice(voice.id))}>{t('use')}</Btn>
            <Btn tone="rose" busy={busy} onClick={() => setRemoving(voice)}>{t('delete')}</Btn>
          </li>)}</ul>}
          {audio && <audio className="mt-3 w-full" controls src={audio} />}
          <Btn tone="slate" busy={busy} onClick={() => void run(() => useVoice(''))}>{t('restore')}</Btn>
          <StudioCreator status={status} busy={busy} run={run} />
        </>}
      </>}
      {removing && <ConfirmDialog title={t('delete')} body={t('delete_body', { name: removing.name })} confirmLabel={t('delete')} cancelLabel={t('cancel')} pending={busy} tone="danger" onConfirm={() => void run(() => deleteVoice(removing.id)).then((ok) => ok && setRemoving(null))} onCancel={() => setRemoving(null)} />}
    </section>
  );
};
