import React, { useEffect, useMemo, useState } from 'react';
import { Database, HardDrive, SlidersHorizontal, Sparkles } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Loading, Panel, Unreachable } from '../shared/kit';
import { FeatureRow } from '../shared/featureTypes';
import { SettingsEditor } from '../shared/SettingsEditor';
import { useAction, useResource } from '../shared/useResource';
import { useFeature } from '../shared/useFeature';
import {
  clearVaultClips,
  deleteVaultClip,
  downloadVoice,
  fetchElevenLabsStatus,
  fetchElevenLabsVoices,
  fetchEngineSettings,
  fetchVaultClips,
  fetchVaultStats,
  parseOverview,
  pregenerateVaultClips,
  removeVoice,
  saveEngineSettings,
  saveElevenLabsKey,
  saveOrder,
  setLanguageVoice,
  speakToRoom,
  testElevenLabsSpeech,
} from './api';
import { EngineStrategySelector } from './components/EngineStrategySelector';
import { ElevenLabsConfigPanel } from './components/ElevenLabsConfigPanel';
import { AudioVaultPanel } from './components/AudioVaultPanel';
import { LocalCatalogPanel } from './components/LocalCatalogPanel';
import { TestBenchBox } from './components/TestBenchBox';
import { usePreview } from './usePreview';
import {
  AudioVaultClip,
  AudioVaultStats,
  ElevenLabsSubscription,
  ElevenLabsVoice,
  EngineMode,
  EngineSettings,
  VoiceItem,
} from './types';

const REFRESH_MS = 6000;
const SETTING_KEYS = ['NUXIVA_VOICE_SPEED', 'NUXIVA_VOICE_PITCH', 'NUXIVA_VOICE_VOLUME', 'NUXIVA_VOICE_ONLINE', 'NUXIVA_VOICE_AUTO_DOWNLOAD'];

const narrow = (feature: FeatureRow): FeatureRow => ({
  ...feature,
  settings: feature.settings.filter((setting) => SETTING_KEYS.includes(setting.key)),
});

type TabType = 'engine' | 'vault' | 'catalog';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/voice_manager');
  const [activeTab, setActiveTab] = useState<TabType>('engine');
  const [showSettings, setShowSettings] = useState(false);

  // Risorse e stato
  const { data, error, loading, reload } = useResource<unknown>('/api/voices', REFRESH_MS);
  const { feature, reload: reloadFeature } = useFeature('voices', 0);
  const { busy, run } = useAction(reload);
  const preview = usePreview();
  const overview = useMemo(() => (data === null ? null : parseOverview(data)), [data]);

  // Stato specifico ElevenLabs e Configurazione Motore
  const [engineSettings, setEngineSettings] = useState<EngineSettings>({
    engine_mode: 'hybrid',
    elevenlabs_voice_id: '21m00Tcm4TlvDq8ikWAM',
    fallback_local: 'if_sara',
    elevenlabs_configured: false,
    speed: 1.0,
    pitch: 0.0,
    volume: 1.0,
    stability: 0.65,
    similarity_boost: 0.75,
  });

  const [elevenStatus, setElevenStatus] = useState<ElevenLabsSubscription | null>(null);
  const [elevenVoices, setElevenVoices] = useState<ElevenLabsVoice[]>([]);
  const [vaultStats, setVaultStats] = useState<AudioVaultStats | null>(null);
  const [vaultClips, setVaultClips] = useState<AudioVaultClip[]>([]);
  const [isTestingSpeech, setIsTestingSpeech] = useState(false);

  // Caricamento iniziale e rinfresco
  const refreshEngineAndVault = async () => {
    try {
      const [settings, status, voices, vStats, vClips] = await Promise.all([
        fetchEngineSettings().catch(() => null),
        fetchElevenLabsStatus().catch(() => null),
        fetchElevenLabsVoices().catch(() => []),
        fetchVaultStats().catch(() => null),
        fetchVaultClips().catch(() => []),
      ]);
      if (settings) setEngineSettings(settings);
      if (status) setElevenStatus(status);
      if (voices) setElevenVoices(voices);
      if (vStats) setVaultStats(vStats);
      if (vClips) setVaultClips(vClips);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    void refreshEngineAndVault();
  }, [data]);

  // Gestione cambio strategia
  const handleSelectMode = async (mode: EngineMode) => {
    const updated = { ...engineSettings, engine_mode: mode };
    setEngineSettings(updated);
    await run(async () => {
      await saveEngineSettings(updated);
      void refreshEngineAndVault();
    }, 'voice_manager_failed');
  };

  // Salvataggio chiave ElevenLabs
  const handleSaveElevenKey = async (key: string) => {
    await run(async () => {
      await saveElevenLabsKey(key);
      void refreshEngineAndVault();
    }, 'voice_manager_failed');
  };

  // Aggiornamento parametri motore
  const handleUpdateSettings = async (patch: Partial<EngineSettings>) => {
    const updated = { ...engineSettings, ...patch };
    setEngineSettings(updated);
    await run(async () => {
      await saveEngineSettings(updated);
      void refreshEngineAndVault();
    }, 'voice_manager_failed');
  };

  // Test di sintesi live
  const handleTestSpeech = async (text: string) => {
    setIsTestingSpeech(true);
    try {
      if (engineSettings.engine_mode === 'local') {
        const fallback = overview?.order[0]?.id || 'if_sara';
        await preview.play(fallback);
      } else {
        const audioBlob = await testElevenLabsSpeech(text, engineSettings.elevenlabs_voice_id);
        const url = URL.createObjectURL(audioBlob);
        const audio = new Audio(url);
        audio.onended = () => {
          setIsTestingSpeech(false);
          URL.revokeObjectURL(url);
        };
        audio.onerror = () => setIsTestingSpeech(false);
        await audio.play();
        void refreshEngineAndVault();
        return;
      }
    } catch {
      // ignore
    } finally {
      setIsTestingSpeech(false);
    }
  };

  // Pronuncia direttamente nella stanza
  const handleSpeakToRoom = async (text: string) => {
    await run(async () => {
      const voice = engineSettings.engine_mode === 'local' ? undefined : `eleven_${engineSettings.elevenlabs_voice_id}`;
      await speakToRoom(text, voice);
      void refreshEngineAndVault();
    }, 'voice_manager_failed');
  };

  // Azioni Audio Vault
  const handlePlayVaultClip = (clipId: string) => {
    const audio = new Audio(`/api/voices/vault/clips/${encodeURIComponent(clipId)}/audio`);
    void audio.play();
  };

  const handleDeleteVaultClip = async (clipId: string) => {
    await run(async () => {
      await deleteVaultClip(clipId);
      void refreshEngineAndVault();
    }, 'voice_manager_failed');
  };

  const handlePregenerateVault = async () => {
    await run(async () => {
      const targetVoice = engineSettings.engine_mode === 'local' ? undefined : `eleven_${engineSettings.elevenlabs_voice_id}`;
      await pregenerateVaultClips(targetVoice);
      void refreshEngineAndVault();
    }, 'voice_manager_failed');
  };

  const handleClearVault = async () => {
    await run(async () => {
      await clearVaultClips();
      void refreshEngineAndVault();
    }, 'voice_manager_failed');
  };

  const handleSearchVault = async (q: string) => {
    const res = await fetchVaultClips(q).catch(() => []);
    setVaultClips(res);
  };

  if (loading && !overview) return <Loading label={t('loading')} />;
  if (!overview) return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;

  const installed = overview.voices.filter((voice) => voice.installed).length;
  const prefer = (voice: VoiceItem) => void run(() => setLanguageVoice(voice.lang, voice.preferred ? '' : voice.id), 'voice_manager_failed');

  // Calcolo nome voce attiva in primo piano
  const activeVoiceName =
    engineSettings.engine_mode === 'local'
      ? overview.order[0]?.name || 'Sara (Kokoro Locale)'
      : elevenVoices.find((v) => v.id === engineSettings.elevenlabs_voice_id)?.name
      ? `${elevenVoices.find((v) => v.id === engineSettings.elevenlabs_voice_id)?.name} (ElevenLabs)`
      : 'Rachel (ElevenLabs)';

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={() => {
        reload();
        void refreshEngineAndVault();
      }}
      actions={
        <Btn tone="slate" onClick={() => setShowSettings((value) => !value)}>
          <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          {t(showSettings ? 'settings_close' : 'settings_open')}
        </Btn>
      }
    >
      {/* HERO STATUS HUD: Identità Vocale Attuale */}
      <div className="rounded-xl border border-cyan-500/30 bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800 p-4 shadow-lg flex flex-col cq-md:flex-row items-start cq-md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-cyan-500/20 border border-cyan-400 flex items-center justify-center text-2xl shadow-[0_0_15px_rgba(6,182,212,0.25)]">
            🗣️
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-white tracking-wide">{t('current_speaking_voice')}</span>
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                  engineSettings.engine_mode === 'hybrid'
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                    : engineSettings.engine_mode === 'elevenlabs'
                    ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                }`}
              >
                ● {t(`engine_mode_${engineSettings.engine_mode}`)}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {t('voice_name')}: <strong className="text-cyan-300">{activeVoiceName}</strong>
              {engineSettings.engine_mode === 'hybrid' ? ` · ${t('fallback_on')} ${overview.order[0]?.name || 'Kokoro'}` : ''}
            </p>
          </div>
        </div>

        {/* METRICHE RAPIDE IN HERO */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="text-right">
            <div className="text-slate-400 text-[10px]">{t('vault_credits_saved')}</div>
            <div className="text-emerald-400 font-bold">+{vaultStats?.total_chars_saved.toLocaleString() || 0} char</div>
          </div>
          <div className="text-right">
            <div className="text-slate-400 text-[10px]">{t('elevenlabs_remaining')}</div>
            <div className="text-purple-300 font-bold">
              {elevenStatus?.configured ? `${elevenStatus.remaining_characters.toLocaleString()} char` : t('not_configured')}
            </div>
          </div>
        </div>
      </div>

      {/* BARRA TAB DI NAVIGAZIONE */}
      <div className="flex items-center gap-1 border-b border-slate-800 pt-3">
        <button
          type="button"
          onClick={() => setActiveTab('engine')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold transition-all border-b-2 -mb-[1px] ${
            activeTab === 'engine'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          {t('tab_voice_and_engine')}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('vault')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold transition-all border-b-2 -mb-[1px] ${
            activeTab === 'vault'
              ? 'border-emerald-400 text-emerald-300 bg-emerald-500/10 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          {t('tab_audio_vault')}
          {vaultStats && vaultStats.total_clips > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 bg-emerald-500/20 text-emerald-300 rounded-full border border-emerald-500/30">
              {vaultStats.total_clips}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold transition-all border-b-2 -mb-[1px] ${
            activeTab === 'catalog'
              ? 'border-purple-400 text-purple-300 bg-purple-500/10 rounded-t-lg'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <HardDrive className="w-3.5 h-3.5" />
          {t('tab_local_catalog')}
        </button>
      </div>

      {showSettings && feature && (
        <Panel title={t('settings_title')}>
          <SettingsEditor feature={narrow(feature)} busy={busy} t={t} run={run} />
        </Panel>
      )}

      {/* CONTENUTO TAB */}
      <div className="pt-2 space-y-6">
        {/* TAB 1: STRATEGIA MOTORE & ELEVENLABS & TEST BENCH */}
        {activeTab === 'engine' && (
          <div className="space-y-6">
            <EngineStrategySelector
              mode={engineSettings.engine_mode}
              onChange={handleSelectMode}
              t={t}
            />

            {(engineSettings.engine_mode === 'elevenlabs' || engineSettings.engine_mode === 'hybrid') && (
              <ElevenLabsConfigPanel
                status={elevenStatus}
                voices={elevenVoices}
                settings={engineSettings}
                busy={busy}
                playingVoiceId={preview.playing}
                onSaveKey={handleSaveElevenKey}
                onSaveSettings={handleUpdateSettings}
                onPreviewVoice={(vid) => preview.play(`eleven_${vid}`)}
                t={t}
              />
            )}

            <TestBenchBox
              settings={engineSettings}
              isSpeaking={isTestingSpeech}
              busy={busy}
              onTestSpeech={handleTestSpeech}
              onSpeakToRoom={handleSpeakToRoom}
              onUpdateTuning={handleUpdateSettings}
              t={t}
            />
          </div>
        )}

        {/* TAB 2: CASSAFORTE AUDIO & RISPARMIO CREDITI/TOKEN */}
        {activeTab === 'vault' && (
          <Panel title={t('tab_audio_vault_title')}>
            <AudioVaultPanel
              stats={vaultStats}
              clips={vaultClips}
              busy={busy}
              onPlayClip={handlePlayVaultClip}
              onDeleteClip={handleDeleteVaultClip}
              onPregenerate={handlePregenerateVault}
              onClear={handleClearVault}
              onSearch={handleSearchVault}
              t={t}
            />
          </Panel>
        )}

        {/* TAB 3: CATALOGO MODELLI LOCALI */}
        {activeTab === 'catalog' && (
          <LocalCatalogPanel
            overview={overview}
            installed={installed}
            busy={busy}
            playing={preview.playing}
            t={t}
            onSaveOrder={(next) => void run(() => saveOrder(next), 'voice_manager_failed')}
            onPlay={(id) => void preview.play(id)}
            onDownload={(id) => void run(() => downloadVoice(id), 'voice_manager_failed')}
            onRemove={(id) => void run(() => removeVoice(id), 'voice_manager_failed')}
            onPrefer={prefer}
          />
        )}
      </div>
    </AppFrame>
  );
};

export default View;
