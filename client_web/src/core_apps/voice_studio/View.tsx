import React, { useEffect, useState } from 'react';
import { Radio, Sliders, Wand2, Mic, Sparkles, Check, Trash2, Volume2, ShieldCheck, Cpu, RefreshCw } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { ConfirmDialog } from '../../shared/ui/ConfirmDialog';
import { Empty, Pill, OSAppLayout } from '../shared/kit';
import { useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
import { StudioCreator } from './StudioCreator';
import { EqualizerController } from './EqualizerController';
import { LiveMicrophoneCloner } from './LiveMicrophoneCloner';
import { TestLaboratory } from './TestLaboratory';
import { WaveformPlayer } from './WaveformPlayer';
import {
  StudioStatus,
  StudioVoice,
  StudioEQ,
  StudioFX,
  deleteVoice,
  fetchStudio,
  previewVoice,
  useVoice,
  saveVoiceSettings,
} from './studioApi';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/voice_studio');
  const [status, setStatus] = useState<StudioStatus | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const [audioUrl, setAudioUrl] = useState('');
  const [removing, setRemoving] = useState<StudioVoice | null>(null);

  // Navigazione schede
  const [activeTab, setActiveTab] = useState<'library' | 'eq' | 'design' | 'clone' | 'test'>('library');
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>('');

  // Parametri EQ e FX attivi
  const defaultEQ: StudioEQ = { bass: 0, low_mid: 0, mid: 0, presence: 0, air: 0 };
  const defaultFX: StudioFX = { pitch: 0, speed: 1.0, deesser: 0, reverb: 0, compressor: 0 };
  const [currentEQ, setCurrentEQ] = useState<StudioEQ>(defaultEQ);
  const [currentFX, setCurrentFX] = useState<StudioFX>(defaultFX);

  useWindowToolbar((actionId) => {
    if (actionId === 'refresh') {
      setTick((c) => c + 1);
    }
  });

  useEffect(() => {
    const controller = new AbortController();
    fetchStudio(controller.signal)
      .then((res) => {
        setStatus(res);
        if (res.voices.length > 0 && !selectedVoiceId) {
          const match = res.voices.find((v) => v.id === res.nuxiva_voice) || res.voices[0];
          setSelectedVoiceId(match.id);
          if (match.eq) setCurrentEQ({ ...defaultEQ, ...match.eq });
          if (match.fx) setCurrentFX({ ...defaultFX, ...match.fx });
        }
      })
      .catch((cause) => !controller.signal.aborted && setError(String(cause.message ?? cause)));
    return () => controller.abort();
  }, [tick]);

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const run = async (task: () => Promise<unknown>) => {
    setBusy(true);
    setError('');
    try {
      await task();
      setTick((current) => current + 1);
      return true;
    } catch (cause: any) {
      setError(cause instanceof Error ? cause.message : String(cause));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const handleSelectVoiceForEQ = (voice: StudioVoice) => {
    setSelectedVoiceId(voice.id);
    if (voice.eq) setCurrentEQ({ ...defaultEQ, ...voice.eq });
    else setCurrentEQ(defaultEQ);
    if (voice.fx) setCurrentFX({ ...defaultFX, ...voice.fx });
    else setCurrentFX(defaultFX);
    setActiveTab('eq');
  };

  const applyPreset = (presetKey: string) => {
    if (!status?.presets || !status.presets[presetKey]) return;
    const p = status.presets[presetKey];
    setCurrentEQ({
      bass: p.bass ?? 0,
      low_mid: p.low_mid ?? 0,
      mid: p.mid ?? 0,
      presence: p.presence ?? 0,
      air: p.air ?? 0,
    });
    setCurrentFX((prev) => ({
      ...prev,
      deesser: p.deesser ?? 0,
      reverb: p.reverb ?? 0,
      compressor: p.compressor ?? 0,
    }));
  };

  const handlePreviewEQ = async () => {
    const targetVoice = selectedVoiceId || status?.voices[0]?.id || '';
    if (!targetVoice) return;
    await run(async () => {
      const blob = await previewVoice(targetVoice, lang, {
        eq: currentEQ,
        fx: currentFX,
      });
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(URL.createObjectURL(blob));
    });
  };

  const handleSaveEQ = async () => {
    if (!selectedVoiceId) return;
    await run(async () => {
      await saveVoiceSettings(selectedVoiceId, currentEQ, currentFX);
    });
  };

  const activeVoiceObj = status?.voices.find((v) => v.id === selectedVoiceId);

  return (
    <OSAppLayout
      content={
        <div className="flex flex-col h-full overflow-y-auto p-4 sm:p-6 lg:p-8 bg-white text-slate-900">
          <div className="space-y-6 w-full flex-1 min-h-0">
            {/* Intestazione Applicazione ad Alto Contrasto */}
            <header className="flex flex-wrap items-center justify-between gap-4 border-b border-cyan-300 pb-5">
          <div>
            <h1 className="flex items-center gap-3 text-2xl font-extrabold tracking-tight text-slate-950">
              <Radio className="h-7 w-7 text-cyan-600" aria-hidden="true" />
              {t('title')}
            </h1>
            <p className="mt-1 text-sm font-medium text-slate-700">
              {t('suite_description')}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {status && (
              <>
                <Pill tone={status.online ? 'emerald' : 'amber'}>
                  <span className="flex items-center gap-1.5 font-bold">
                    <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                    {status.engine === 'container' ? t('engine_container') : t('engine_native')}
                  </span>
                </Pill>
                <Pill>
                  <span className="flex items-center gap-1.5 font-bold">
                    <Cpu className="h-4 w-4" aria-hidden="true" />
                    {t(status.where === 'remote' ? 'remote' : 'local')}
                  </span>
                </Pill>
              </>
            )}

            <button
              type="button"
              disabled={busy}
              onClick={() => setTick((c) => c + 1)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-100 hover:bg-slate-200 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:text-cyan-800 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} aria-hidden="true" />
              {t('refresh')}
            </button>
          </div>
        </header>

        {error && (
          <div role="alert" className="rounded-2xl border border-rose-300 bg-rose-100 p-4 text-sm font-semibold text-rose-800 shadow-lg">
            {error}
          </div>
        )}

        {!status ? (
          <p className="text-sm font-medium text-slate-700">{t('loading')}</p>
        ) : (
          <>
            {/* Navigazione Schede (Tablist Accessibile) */}
            <nav
              role="tablist"
              aria-label="Sezioni Studio delle Voci"
              className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-md"
            >
              {[
                { id: 'library', label: t('tab_library'), icon: Radio },
                { id: 'eq', label: t('tab_eq'), icon: Sliders },
                { id: 'design', label: t('tab_design'), icon: Wand2 },
                { id: 'clone', label: t('tab_clone'), icon: Mic },
                { id: 'test', label: t('tab_test'), icon: Sparkles },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    id={`tab-${tab.id}`}
                    aria-controls={`panel-${tab.id}`}
                    aria-selected={isActive}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${
                      isActive
                        ? 'bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/30 font-extrabold'
                        : 'text-slate-800 hover:bg-slate-100 hover:text-slate-950'
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>

            {/* Scheda 1: Libreria Voci */}
            {activeTab === 'library' && (
              <section
                id="panel-library"
                role="tabpanel"
                aria-labelledby="tab-library"
                className="space-y-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="text-sm font-bold text-slate-950">
                    {status.voices.length} {t('voices_registered')}
                  </span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void run(() => useVoice(''))}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-100 hover:bg-slate-200 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:text-cyan-800 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:opacity-50"
                  >
                    {t('restore')}
                  </button>
                </div>

                {status.voices.length === 0 ? (
                  <Empty>{t('empty')}</Empty>
                ) : (
                  <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                    {status.voices.map((voice) => {
                      const isSelected = status.nuxiva_voice === voice.id;
                      return (
                        <div
                          key={voice.id}
                          className={`flex flex-col justify-between rounded-2xl border p-5 shadow-lg transition ${
                            isSelected
                              ? 'border-emerald-300 bg-gradient-to-b from-emerald-950/40 to-white shadow-emerald-500/10'
                              : 'border-slate-300 bg-white hover:border-cyan-300 hover:bg-slate-850/90'
                          }`}
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-base font-extrabold text-slate-950 truncate">{voice.name}</span>
                              {isSelected && (
                                <span className="inline-flex items-center rounded-md border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-700">
                                  {t('selected')}
                                </span>
                              )}
                            </div>
                            <span className="mt-1 block text-xs font-medium text-slate-700">
                              Lingua: {voice.language.toUpperCase()} • Tipo: {voice.kind === 'clone' ? 'Clonata da Microfono' : 'Creata con AI'}
                            </span>
                          </div>

                          <div className="mt-5 flex flex-wrap items-center gap-2 pt-3 border-t border-slate-200">
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                void run(async () => {
                                  const blob = await previewVoice(voice.id, lang, { eq: voice.eq, fx: voice.fx });
                                  if (audioUrl) URL.revokeObjectURL(audioUrl);
                                  setAudioUrl(URL.createObjectURL(blob));
                                })
                              }
                              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 text-xs font-bold text-slate-950 transition hover:text-cyan-800 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:opacity-50"
                            >
                              <Volume2 className="h-4 w-4" aria-hidden="true" />
                              {t('preview')}
                            </button>

                            {isSelected ? (
                              <span className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-300 bg-emerald-100 px-3 py-1.5 text-xs font-bold text-emerald-700 shadow-sm cursor-default">
                                <Check className="h-4 w-4" aria-hidden="true" />
                                {t('selected')}
                              </span>
                            ) : (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => void run(() => useVoice(voice.id))}
                                className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-3 py-1.5 text-xs font-bold text-slate-950 shadow-md shadow-cyan-500/20 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-50"
                              >
                                <Check className="h-4 w-4" aria-hidden="true" />
                                {t('use')}
                              </button>
                            )}

                            <button
                              type="button"
                              onClick={() => handleSelectVoiceForEQ(voice)}
                              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 text-xs font-bold text-slate-950 transition hover:text-cyan-800 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                            >
                              <Sliders className="h-4 w-4" aria-hidden="true" />
                              {t('edit_eq')}
                            </button>

                            <button
                              type="button"
                              disabled={busy}
                              aria-label={`Elimina ${voice.name}`}
                              onClick={() => setRemoving(voice)}
                              className="inline-flex items-center justify-center rounded-xl border border-rose-300 bg-rose-100 hover:bg-rose-600 hover:text-white p-2 text-xs font-bold text-rose-800 transition shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 disabled:opacity-50"
                            >
                              <Trash2 className="h-4 w-4" aria-hidden="true" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            )}

            {/* Scheda 2: Equalizzatore & Voice Controller */}
            {activeTab === 'eq' && (
              <section id="panel-eq" role="tabpanel" aria-labelledby="tab-eq">
                <EqualizerController
                  eq={currentEQ}
                  fx={currentFX}
                  onChangeEQ={setCurrentEQ}
                  onChangeFX={setCurrentFX}
                  onApplyPreset={applyPreset}
                  onReset={() => {
                    setCurrentEQ(defaultEQ);
                    setCurrentFX(defaultFX);
                  }}
                  onPreview={handlePreviewEQ}
                  onSave={selectedVoiceId ? handleSaveEQ : undefined}
                  busy={busy}
                  selectedVoiceName={activeVoiceObj?.name}
                />
              </section>
            )}

            {/* Scheda 3: Crea Voce AI (Voice Designer) */}
            {activeTab === 'design' && (
              <section id="panel-design" role="tabpanel" aria-labelledby="tab-design">
                <StudioCreator
                  status={status}
                  busy={busy}
                  run={run}
                  onSuccess={() => setActiveTab('library')}
                />
              </section>
            )}

            {/* Scheda 4: Clona da Microfono */}
            {activeTab === 'clone' && (
              <section id="panel-clone" role="tabpanel" aria-labelledby="tab-clone">
                <LiveMicrophoneCloner
                  sentences={status.sentences}
                  busy={busy}
                  run={run}
                  onSuccess={() => setActiveTab('library')}
                />
              </section>
            )}

            {/* Scheda 5: Laboratorio di Test & Waveform */}
            {activeTab === 'test' && (
              <section id="panel-test" role="tabpanel" aria-labelledby="tab-test">
                <TestLaboratory
                  voices={status.voices}
                  defaultVoiceId={selectedVoiceId}
                  eq={currentEQ}
                  fx={currentFX}
                />
              </section>
            )}

            {/* Player Waveform Fisso in Basso se c'è un'anteprima */}
            {audioUrl && activeTab !== 'test' && (
              <div className="pt-4 border-t border-cyan-300">
                <WaveformPlayer src={audioUrl} />
              </div>
            )}
          </>
        )}

        {/* Dialogo di Conferma Eliminazione Voce */}
        {removing && (
          <ConfirmDialog
            title={t('delete')}
            body={t('delete_body', { name: removing.name })}
            confirmLabel={t('delete')}
            cancelLabel={t('cancel')}
            pending={busy}
            tone="danger"
            onConfirm={() =>
              void run(() => deleteVoice(removing.id)).then((ok) => ok && setRemoving(null))
            }
            onCancel={() => setRemoving(null)}
          />
        )}
      </div>
    </div>
      }
    />
  );
};
