import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Camera, Layers, Maximize2, Minimize2, SlidersHorizontal, Wand2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { BuildProgress } from './components/BuildProgress';
import { Library } from './components/Library';
import { LookPanel } from './components/LookPanel';
import { PromptBar } from './components/PromptBar';
import { ScenePanel } from './components/ScenePanel';
import { Viewport } from './components/Viewport';
import { useDiorama } from './useDiorama';

const COMPACT_PX = 640;
type Tab = 'scene' | 'look';

export const View: React.FC<{ readonly lite?: boolean }> = ({ lite = false }) => {
  const { t } = useScopedI18n('apps/diorama');
  const state = useDiorama();
  const { current, catalog } = state;
  const root = useRef<HTMLDivElement>(null);
  const take = useRef<() => string>(() => '');
  const [compact, setCompact] = useState(false);
  const [tab, setTab] = useState<Tab>('scene');
  const [panel, setPanel] = useState(true);
  const [selected, setSelected] = useState('');
  const [full, setFull] = useState(false);

  useEffect(() => {
    const element = root.current;
    if (!element) return undefined;
    const observer = new ResizeObserver(() => setCompact(element.clientWidth < COMPACT_PX));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onChange = () => setFull(document.fullscreenElement === root.current);
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const register = useCallback((fn: () => string) => {
    take.current = fn;
  }, []);

  const toggleFull = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void root.current?.requestFullscreen?.();
  };

  const snapshot = () => {
    const data = take.current();
    if (!data) return;
    const link = document.createElement('a');
    link.href = data;
    link.download = `${(current?.title || 'diorama').replace(/[^\w-]+/g, '_')}.png`;
    link.click();
  };

  const stageLabel = useCallback((stage: string) => t(`stage_${stage}`), [t]);
  const examples = useMemo(() => [t('example_1'), t('example_2'), t('example_3')], [t]);
  const errorText = state.error ? t(`error_${state.error}`) !== `error_${state.error}` ? t(`error_${state.error}`) : t('error_request_failed') : '';
  const showPanel = !compact && panel && current && catalog;

  if (!current) {
    return (
      <div ref={root} className="flex h-full w-full flex-col overflow-y-auto bg-gradient-to-b from-white via-slate-50 to-sky-50/60">
        <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col items-center justify-center gap-8 px-5 py-10">
          <div className="text-center">
            <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-amber-400 text-white shadow-lg shadow-sky-200"><Wand2 className="h-7 w-7" /></span>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">{t('title')}</h1>
            <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-slate-500">{t('subtitle')}</p>
          </div>
          <div className="w-full max-w-2xl">
            <PromptBar placeholder={t('prompt_new')} action={t('build')} busy={state.busy} disabled={false} onSubmit={(text) => void state.create(text)} examples={examples} />
            {errorText && <p role="alert" className="mt-3 text-center text-xs font-semibold text-rose-600">{errorText}</p>}
          </div>
          {state.library.length > 0 && (
            <div className="w-full">
              <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-400">{t('library')}</h2>
              <Library rows={state.library} t={t} onOpen={state.open} onDelete={(id) => void state.remove(id)} />
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div ref={root} className="relative flex h-full w-full overflow-hidden bg-white">
      <div className="relative min-w-0 flex-1">
        <Viewport diorama={current} animate={state.loadedOnce && (state.building || current.job.state === 'done')} selected={selected} onPick={setSelected} onSnapshot={register} unsupported={t('webgl_unsupported')} lite={lite} />
        <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between gap-3 p-3 sm:p-4">
          <div className="pointer-events-auto flex min-w-0 items-center gap-2 rounded-2xl border border-slate-200 bg-white/90 py-1.5 pl-1.5 pr-4 shadow-md backdrop-blur">
            <button type="button" onClick={state.close} aria-label={t('back')} className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"><ArrowLeft className="h-4 w-4" /></button>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-slate-900">{current.title || t('untitled')}</p>
              {!compact && current.story && <p className="max-w-md truncate text-[11px] text-slate-500">{current.story}</p>}
            </div>
          </div>
          <div className="pointer-events-auto flex items-center gap-1.5 rounded-2xl border border-slate-200 bg-white/90 p-1.5 shadow-md backdrop-blur">
            <button type="button" onClick={snapshot} aria-label={t('snapshot')} title={t('snapshot')} className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"><Camera className="h-4 w-4" /></button>
            <button type="button" onClick={toggleFull} aria-label={t('fullscreen')} title={t('fullscreen')} className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900">{full ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}</button>
            {!compact && <button type="button" onClick={() => setPanel(!panel)} aria-label={t('panel')} title={t('panel')} className={`rounded-xl p-2 transition ${panel ? 'bg-sky-50 text-sky-700' : 'text-slate-500 hover:bg-slate-100'}`}><SlidersHorizontal className="h-4 w-4" /></button>}
          </div>
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col items-center gap-3 p-3 sm:p-4">
          {(state.building || current.job.mode) && <BuildProgress job={current.job} count={current.items.length} label={stageLabel} itemsLabel={t('items')} fallbackLabel={t('mode_template')} />}
          {errorText && <p role="alert" className="pointer-events-auto rounded-xl bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 shadow">{errorText}</p>}
          <div className="pointer-events-auto w-full max-w-2xl">
            <PromptBar placeholder={t('prompt_refine')} action={t('apply')} busy={state.busy || state.building} disabled={state.building} onSubmit={(text) => void state.refine(text)} />
          </div>
        </div>
      </div>
      {showPanel && (
        <aside className="flex w-80 shrink-0 flex-col border-l border-slate-200 bg-slate-50/80">
          <div className="grid grid-cols-2 gap-1 border-b border-slate-200 bg-white p-2">
            {(['scene', 'look'] as const).map((id) => (
              <button key={id} type="button" onClick={() => setTab(id)} className={`flex items-center justify-center gap-2 rounded-xl py-2 text-xs font-bold transition ${tab === id ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-100'}`}>
                {id === 'scene' ? <Layers className="h-4 w-4" /> : <Camera className="h-4 w-4" />}
                {t(`tab_${id}`)}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {tab === 'scene' ? (
              <ScenePanel catalog={catalog} items={current.items} base={current.base} selected={selected} t={t} onSelect={setSelected} onAdd={(kind) => void state.add(kind, current.items.find((i) => i.id === selected)).then(setSelected)} onPatch={(id, patch) => void state.patchItem(id, patch)} onDrop={(id) => { setSelected(''); void state.dropItem(id); }} />
            ) : (
              <LookPanel look={current.look} base={current.base} t={t} onLook={(patch) => void state.patchLook(patch)} onBase={(patch) => void state.patchBase(patch)} />
            )}
          </div>
        </aside>
      )}
    </div>
  );
};

export default View;
