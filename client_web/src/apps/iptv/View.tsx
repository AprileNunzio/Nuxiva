import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  OSAppLayout,
  OSSidebar,
  OSInspector,
  Loading,
  Empty,
  useOSFileUpload,
} from '../shared/kit';
import {
  TvOverview,
  TvChannel,
  TvChannelPage,
  TvTarget,
  TvTuner,
  TvEpgData,
  TvSettings,
} from './types';
import {
  addPlaylist,
  refreshPlaylist,
  removePlaylist,
  uploadPlaylistFile,
  setFavorite,
  fetchTuners,
  discoverTuners,
  addTuner,
  removeTuner,
  scanTuner,
  fetchEpg,
  refreshEpg,
  fetchSettings,
  updateSettings,
  play,
  stop,
  getLiveStreamUrl,
} from './api';
import { ChannelLogo } from './ChannelLogo';
import { useHlsPlayer } from './useHlsPlayer';
import {
  Tv,
  MonitorPlay,
  Calendar,
  Radio,
  ListVideo,
  Sliders,
  Star,
  Search,
  Play,
  Square,
  Volume2,
  VolumeX,
  Maximize2,
  ExternalLink,
  RefreshCw,
  Trash2,
  UploadCloud,
  Check,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Plus,
  AlertTriangle,
  Cast,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useAction, useResource } from '../shared/useResource';
import { asList } from '../shared/http';
import { CastModal } from './CastModal';

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/iptv');
  const os = useOSApp();

  const [activeTab, setActiveTab] = useState<'live' | 'epg' | 'tuners' | 'playlists' | 'settings'>('live');
  const [query, setQuery] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('');
  const [onlyFavorites, setOnlyFavorites] = useState(false);
  const [selectedTarget, setSelectedTarget] = useState('display');

  // Selezione canale e ispettore
  const [selectedChannel, setSelectedChannel] = useState<TvChannel | null>(null);
  const [channelEpg, setChannelEpg] = useState<TvEpgData | null>(null);
  const [epgLoading, setEpgLoading] = useState(false);

  // Live video player interno
  const [activeStreamChannel, setActiveStreamChannel] = useState<TvChannel | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [aspectRatio, setAspectRatio] = useState<'16/9' | '4/3' | 'cover'>('16/9');
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.85);

  // Tuner state
  const [tunersList, setTunersList] = useState<readonly TvTuner[]>([]);
  const [scanningTunerId, setScanningTunerId] = useState<string | null>(null);
  const [discoveringTuners, setDiscoveringTuners] = useState(false);
  const [showAddTunerModal, setShowAddTunerModal] = useState(false);
  const [newTunerName, setNewTunerName] = useState('');
  const [newTunerType, setNewTunerType] = useState('dvb_t2');
  const [newTunerDevice, setNewTunerDevice] = useState('');

  // Settings & VPN state
  const [tvSettings, setTvSettings] = useState<TvSettings>({
    vpn_required: false,
    vpn_profile: '',
    epg_url: '',
    epg_auto_refresh: true,
    buffer_size: 'medium',
  });
  const [epgRefreshing, setEpgRefreshing] = useState(false);
  const [epgStatusMessage, setEpgStatusMessage] = useState<string | null>(null);

  // Riproduzione HLS avanzata con gestione automatica buffer e VPN
  const {
    videoRef,
    streamError: hlsError,
    isLoading: streamLoading,
    isPlaying: streamPlaying,
  } = useHlsPlayer(activeStreamChannel?.id ?? null, tvSettings.vpn_required);

  // New Playlist form
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [newPlaylistUrl, setNewPlaylistUrl] = useState('');
  const [isCastOpen, setIsCastOpen] = useState(false);

  // Upload status
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  // Paginazione canali
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(60);

  useEffect(() => {
    setPage(1);
  }, [query, selectedGroup, onlyFavorites, pageSize]);

  // Resources
  const overview = useResource<TvOverview>('/api/tv');
  const params = new URLSearchParams({
    q: query.trim().slice(0, 80),
    group: selectedGroup,
    fav: String(onlyFavorites),
    page: String(page),
    limit: String(pageSize),
  });
  const channels = useResource<TvChannelPage>(`/api/tv/channels?${params.toString()}`);
  const targets = useResource<{ targets: TvTarget[] }>('/api/tv/targets');

  const totalChannels = channels.data?.total ?? 0;
  const totalPages = channels.data?.pages ?? (pageSize > 0 ? Math.max(1, Math.ceil(totalChannels / pageSize)) : 1);
  const currentPage = channels.data?.page ?? page;

  const { busy, run } = useAction(() => {
    overview.reload();
    channels.reload();
  });

  // Carica i tuner reali
  const reloadTuners = useCallback(async () => {
    try {
      const res = await fetchTuners();
      if (res && res.tuners) {
        setTunersList(res.tuners);
      }
    } catch {
      // Ignora errori
    }
  }, []);

  // Carica impostazioni TV
  const reloadSettings = useCallback(async () => {
    try {
      const res = await fetchSettings();
      if (res) {
        setTvSettings(res);
      }
    } catch {
      // Ignora errori
    }
  }, []);

  useEffect(() => {
    void reloadTuners();
    void reloadSettings();
  }, [reloadTuners, reloadSettings]);

  // Carica l'EPG quando viene selezionato un canale
  useEffect(() => {
    if (!selectedChannel) {
      setChannelEpg(null);
      return;
    }
    let cancelled = false;
    setEpgLoading(true);
    fetchEpg(selectedChannel.id)
      .then((data) => {
        if (!cancelled) {
          setChannelEpg(data);
          setEpgLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setChannelEpg(null);
          setEpgLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedChannel]);

  // Gestione File Upload Drag & Drop nativo
  const handleFilesUpload = async (files: File[]) => {
    const valid = files.filter((f) =>
      f.name.toLowerCase().endsWith('.m3u') || f.name.toLowerCase().endsWith('.m3u8')
    );
    if (!valid.length) return;
    setUploadStatus(t('uploading_playlist'));
    setUploadProgress(20);
    try {
      for (let i = 0; i < valid.length; i++) {
        await uploadPlaylistFile(valid[i]);
        setUploadProgress(Math.round(((i + 1) / valid.length) * 100));
      }
      setUploadStatus(t('upload_success'));
      overview.reload();
      channels.reload();
      setTimeout(() => {
        setUploadStatus(null);
        setUploadProgress(null);
      }, 3000);
    } catch (err: any) {
      setUploadStatus(err?.message || t('upload_failed'));
      setTimeout(() => setUploadStatus(null), 5000);
    }
  };

  const { openPicker, fileInput } = useOSFileUpload(
    (files) => {
      void handleFilesUpload(files);
    },
    { accept: '.m3u,.m3u8' }
  );

  // Discovery hardware e di rete reale
  const handleDiscoverTuners = async () => {
    setDiscoveringTuners(true);
    try {
      const res = await discoverTuners();
      if (res && res.tuners) {
        setTunersList(res.tuners);
      }
      overview.reload();
    } catch {
      // Ignora errori
    } finally {
      setDiscoveringTuners(false);
    }
  };

  // Aggiunta manuale di un tuner
  const handleAddTunerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTunerName.trim() || !newTunerDevice.trim()) return;
    try {
      await addTuner({
        name: newTunerName.trim(),
        type: newTunerType,
        device: newTunerDevice.trim(),
      });
      setNewTunerName('');
      setNewTunerDevice('');
      setShowAddTunerModal(false);
      await reloadTuners();
      overview.reload();
    } catch {
      // Ignora errori
    }
  };

  // Rimozione tuner
  const handleRemoveTuner = async (tid: string) => {
    try {
      await removeTuner(tid);
      await reloadTuners();
      overview.reload();
    } catch {
      // Ignora errori
    }
  };

  // Scansione frequenze reale
  const handleScanTuner = async (tid: string) => {
    setScanningTunerId(tid);
    try {
      await scanTuner(tid);
      await reloadTuners();
      overview.reload();
      channels.reload();
    } catch {
      // Ignora errori
    } finally {
      setScanningTunerId(null);
    }
  };

  // Aggiornamento impostazioni VPN
  const handleToggleVpnRequired = async (enabled: boolean) => {
    const updated = { ...tvSettings, vpn_required: enabled };
    setTvSettings(updated);
    try {
      await updateSettings({ vpn_required: enabled });
    } catch {
      void reloadSettings();
    }
  };

  const handleUpdateVpnProfile = async (profile: string) => {
    const updated = { ...tvSettings, vpn_profile: profile };
    setTvSettings(updated);
    try {
      await updateSettings({ vpn_profile: profile });
    } catch {
      void reloadSettings();
    }
  };

  // Aggiornamento EPG da URL
  const handleRefreshEpgNow = async () => {
    setEpgRefreshing(true);
    setEpgStatusMessage(t('epg_refreshing'));
    try {
      const res = await refreshEpg(tvSettings.epg_url);
      setEpgStatusMessage(`${res.total_programs} programmi caricati per ${res.channels_with_epg} canali.`);
      if (selectedChannel) {
        const d = await fetchEpg(selectedChannel.id);
        setChannelEpg(d);
      }
    } catch (err: any) {
      setEpgStatusMessage(err?.message || 'Errore aggiornamento EPG');
    } finally {
      setEpgRefreshing(false);
      setTimeout(() => setEpgStatusMessage(null), 6000);
    }
  };

  const handleToggleFavorite = async (ch: TvChannel) => {
    await run(() => setFavorite(ch.id, !ch.favorite));
    channels.reload();
    overview.reload();
  };

  const handlePlayInApp = (channel: TvChannel) => {
    setStreamError(null);
    setActiveStreamChannel(channel);
    setSelectedChannel(channel);
  };

  const handleCastPlay = async (channel: TvChannel, targetDevice: string) => {
    try {
      await run(() => play(channel.id, targetDevice));
    } catch (err: any) {
      if (err?.message?.includes('VPN_REQUIRED')) {
        alert(t('vpn_block_alert'));
      }
    }
  };

  const handleStopAll = async () => {
    setActiveStreamChannel(null);
    setStreamError(null);
    await run(stop);
  };

  const data = overview.data;
  const channelRows = channels.data?.channels ?? [];
  const targetList = asList<TvTarget>(targets.data?.targets);

  const groupsList = useMemo(() => {
    return data?.groups ?? [];
  }, [data?.groups]);

  const sidebarNavItems = [
    {
      id: 'live',
      label: t('tab_live'),
      icon: <MonitorPlay className="h-4 w-4" />,
      count: activeStreamChannel ? 1 : undefined,
    },
    {
      id: 'epg',
      label: t('tab_epg'),
      icon: <Calendar className="h-4 w-4" />,
    },
    {
      id: 'tuners',
      label: t('tab_tuners'),
      icon: <Radio className="h-4 w-4" />,
      count: tunersList.length,
    },
    {
      id: 'playlists',
      label: t('tab_playlists'),
      icon: <ListVideo className="h-4 w-4" />,
      count: data?.playlists?.length,
    },
    {
      id: 'settings',
      label: t('tab_settings'),
      icon: <Sliders className="h-4 w-4" />,
    },
  ];

  return (
    <div className="relative h-full w-full select-none overflow-hidden bg-slate-50 text-slate-900">
      {fileInput}
      {/* Banner di caricamento in corso */}
      {uploadStatus && (
        <div className="absolute top-4 right-4 z-40 flex items-center gap-3 rounded-xl border border-cyan-500/40 bg-white/90 backdrop-blur-md px-4 py-2.5 shadow-xl">
          <RefreshCw className="h-4 w-4 text-cyan-600 animate-spin" />
          <div className="text-xs">
            <p className="font-semibold text-slate-900">{uploadStatus}</p>
            {uploadProgress !== null && (
              <div className="mt-1 h-1 w-32 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-cyan-400 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      <OSAppLayout
        sidebar={
          <OSSidebar
            title={t('title')}
            items={sidebarNavItems}
            activeId={activeTab}
            onSelect={(id) => setActiveTab(id as any)}
            footer={
              <div className="flex flex-col gap-2 pt-2 border-t border-slate-200">
                <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  {t('playback_target')}
                </span>
                <select
                  value={selectedTarget}
                  onChange={(e) => setSelectedTarget(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-cyan-500 focus:outline-none"
                >
                  <option value="display">{t('this_display')}</option>
                  {targetList.map((tgt) => (
                    <option key={tgt.id} value={tgt.id}>
                      {tgt.name} ({tgt.kind})
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={openPicker}
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 transition"
                >
                  <UploadCloud className="h-3.5 w-3.5 text-cyan-600" />
                  <span>{t('load_m3u_file')}</span>
                </button>

                {activeStreamChannel && (
                  <button
                    type="button"
                    onClick={handleStopAll}
                    className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-lg bg-rose-500/20 border border-rose-500/30 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-500/30 transition"
                  >
                    <Square className="h-3.5 w-3.5 fill-rose-400" />
                    <span>{t('stop_stream')}</span>
                  </button>
                )}
              </div>
            }
          />
        }
        content={
          <div className="flex h-full flex-col overflow-hidden">
            {/* Topbar: Ricerca e Filtri */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-slate-50/60 p-3 backdrop-blur-sm">
              <div className="flex items-center gap-2 flex-1 max-w-md">
                <div className="relative w-full">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={t('search_channels')}
                    className="w-full rounded-xl border border-slate-200 bg-white/80 pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                  {query && (
                    <button
                      type="button"
                      onClick={() => setQuery('')}
                      className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-900"
                    >
                      ×
                    </button>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {groupsList.length > 0 && (
                  <select
                    value={selectedGroup}
                    onChange={(e) => setSelectedGroup(e.target.value)}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="">{t('all_categories')}</option>
                    {groupsList.map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                )}

                <button
                  type="button"
                  onClick={() => setOnlyFavorites(!onlyFavorites)}
                  className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                    onlyFavorites
                      ? 'border-amber-500/50 bg-amber-500/20 text-amber-700'
                      : 'border-slate-200 bg-white text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Star className={`h-3.5 w-3.5 ${onlyFavorites ? 'fill-amber-400 text-amber-600' : ''}`} />
                  <span>{t('favorites_only')}</span>
                </button>
              </div>
            </div>

            {/* Area Contenuto */}
            <div className="flex-1 overflow-y-auto p-4">
              {/* TAB 1: IN DIRETTA (CANALI E PLAYER INTERNO) */}
              {activeTab === 'live' && (
                <div className="flex flex-col gap-4">
                  {/* Player Video Streaming Live */}
                  {activeStreamChannel && (
                    <div className="relative rounded-2xl overflow-hidden border border-slate-300/80 bg-black shadow-2xl">
                      {streamError || hlsError ? (
                        <div className="flex flex-col items-center justify-center p-8 text-center bg-rose-950/40 border border-rose-500/50 rounded-2xl m-2">
                          <AlertTriangle className="h-10 w-10 text-rose-600 mb-2 animate-bounce" />
                          <h4 className="text-sm font-bold text-slate-900 mb-1">Errore Riproduzione</h4>
                          <p className="text-xs text-rose-800 max-w-md mb-4">{streamError || hlsError}</p>
                          {(streamError || hlsError || '').includes('VPN') ? (
                            <button
                              type="button"
                              onClick={() => setActiveTab('settings')}
                              className="rounded-xl bg-gradient-to-r from-rose-600 to-rose-500 px-5 py-2 text-xs font-bold text-white shadow-lg shadow-rose-600/30 hover:brightness-110 transition"
                            >
                              Configura Connessione VPN
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handlePlayInApp(activeStreamChannel)}
                              className="rounded-xl bg-slate-100 border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-200 transition"
                            >
                              Riprova Connessione
                            </button>
                          )}
                        </div>
                      ) : (
                        <div
                          className={`relative w-full bg-black flex items-center justify-center ${
                            aspectRatio === '16/9'
                              ? 'aspect-video'
                              : aspectRatio === '4/3'
                              ? 'aspect-[4/3]'
                              : 'h-96'
                          }`}
                        >
                          {streamLoading && (
                            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
                              <RefreshCw className="h-8 w-8 text-cyan-600 animate-spin mb-2" />
                              <span className="text-xs font-medium text-slate-600">Connessione allo stream HLS in corso...</span>
                            </div>
                          )}
                          <video
                            ref={videoRef}
                            controls
                            muted={isMuted}
                            className={`h-full w-full ${
                              aspectRatio === 'cover' ? 'object-cover' : 'object-contain'
                            }`}
                          />
                        </div>
                      )}

                      {/* Header Player Controls */}
                      <div className="flex items-center justify-between border-t border-slate-200 bg-white/90 px-4 py-3">
                        <div className="flex items-center gap-3">
                          <ChannelLogo url={activeStreamChannel.logo} name={activeStreamChannel.name} size="sm" />
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-slate-900">{activeStreamChannel.name}</span>
                              <span className="flex items-center gap-1 rounded-full bg-emerald-500/20 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-bold text-emerald-600">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                                LIVE HLS
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-500">
                              {activeStreamChannel.group || t('generic_category')}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <select
                            value={aspectRatio}
                            onChange={(e) => setAspectRatio(e.target.value as any)}
                            className="rounded-lg border border-slate-300 bg-slate-100 px-2.5 py-1 text-xs text-slate-800 focus:outline-none"
                          >
                            <option value="16/9">16:9</option>
                            <option value="4/3">4:3</option>
                            <option value="cover">Riempi</option>
                          </select>

                          <button
                            type="button"
                            onClick={() => setIsMuted(!isMuted)}
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition"
                          >
                            {isMuted ? <VolumeX className="h-4 w-4 text-rose-600" /> : <Volume2 className="h-4 w-4" />}
                          </button>

                          <button
                            type="button"
                            onClick={() => setIsCastOpen(true)}
                            className="rounded-lg p-1.5 text-cyan-600 hover:bg-slate-100 hover:text-cyan-700 transition"
                            title="Trasmetti su Dispositivo (Chromecast, Sonos, Bose, Smart TV)"
                          >
                            <Cast className="h-4 w-4" />
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              if (videoRef.current?.requestFullscreen) {
                                void videoRef.current.requestFullscreen();
                              }
                            }}
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition"
                            title={t('fullscreen')}
                          >
                            <Maximize2 className="h-4 w-4" />
                          </button>

                          <button
                            type="button"
                            onClick={handleStopAll}
                            className="ml-2 rounded-xl bg-rose-600/80 hover:bg-rose-600 px-3 py-1.5 text-xs font-bold text-white shadow-md shadow-rose-600/30 transition"
                          >
                            {t('close_player')}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* BARRA PAGINAZIONE SUPERIORE */}
                  {totalChannels > 0 && (
                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white/70 px-4 py-2.5 text-xs text-slate-600">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold text-slate-900">
                          {t('total_channels', { count: totalChannels })}
                        </span>
                        <span className="text-slate-500">|</span>
                        <div className="flex items-center gap-1">
                          {[60, 120].map((sz) => (
                            <button
                              key={sz}
                              type="button"
                              onClick={() => setPageSize(sz)}
                              className={`rounded-lg px-2.5 py-1 font-semibold transition ${
                                pageSize === sz
                                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                                  : 'bg-slate-100/80 text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                              }`}
                            >
                              {t('per_page', { count: sz })}
                            </button>
                          ))}
                          <button
                            type="button"
                            onClick={() => setPageSize(0)}
                            className={`rounded-lg px-2.5 py-1 font-semibold transition ${
                              pageSize === 0
                                ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                                : 'bg-slate-100/80 text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                            }`}
                          >
                            {t('all_channels_btn', { total: totalChannels })}
                          </button>
                        </div>
                      </div>

                      {pageSize > 0 && totalPages > 1 && (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            disabled={currentPage <= 1}
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            className="flex items-center gap-1 rounded-lg border border-slate-300 bg-slate-100 px-2.5 py-1 font-medium text-slate-800 transition hover:bg-slate-200 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <ChevronLeft className="h-3.5 w-3.5" />
                            <span>{t('page_prev')}</span>
                          </button>
                          <span className="font-semibold text-cyan-700 px-1">
                            {t('page_info', { page: currentPage, pages: totalPages })}
                          </span>
                          <button
                            type="button"
                            disabled={currentPage >= totalPages}
                            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            className="flex items-center gap-1 rounded-lg border border-slate-300 bg-slate-100 px-2.5 py-1 font-medium text-slate-800 transition hover:bg-slate-200 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <span>{t('page_next')}</span>
                            <ChevronRight className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {/* GRIGLIA CANALI */}
                  {channelRows.length === 0 ? (
                    <div className="py-12 text-center">
                      <Empty>
                        {data?.count === 0 ? t('no_channels_add_playlist') : t('no_channels_found')}
                      </Empty>
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                        {channelRows.map((channel, idx) => (
                          <div
                            key={channel.id}
                            onClick={() => setSelectedChannel(channel)}
                            className={`group relative flex flex-col justify-between overflow-hidden rounded-2xl border p-3.5 transition-all duration-200 cursor-pointer ${
                              selectedChannel?.id === channel.id
                                ? 'border-cyan-500/80 bg-gradient-to-b from-cyan-950/30 to-slate-50/90 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/50'
                                : 'border-slate-850 bg-white/60 hover:border-slate-300 hover:bg-slate-100/80 hover:shadow-md'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              {/* Logo Canale */}
                              <ChannelLogo url={channel.logo} name={channel.name} size="md" />

                              {/* Azioni rapide */}
                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    void handleToggleFavorite(channel);
                                  }}
                                  className={`rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-amber-400 transition ${
                                    channel.favorite ? 'text-amber-600' : ''
                                  }`}
                                  title={t('favorite')}
                                >
                                  <Star className={`h-4 w-4 ${channel.favorite ? 'fill-amber-400' : ''}`} />
                                </button>
                              </div>
                            </div>

                            <div className="mt-2.5">
                              <h4 className="text-xs font-bold text-slate-900 truncate group-hover:text-cyan-700 transition">
                                {channel.name}
                              </h4>
                              <p className="text-[10px] text-slate-500 truncate mt-0.5">
                                {channel.group || t('generic_category')}
                              </p>
                            </div>

                            {/* Hover Play Button */}
                            <div className="mt-3 flex items-center justify-between gap-1 border-t border-slate-200/80 pt-2">
                              <span className="text-[10px] font-mono text-slate-500">
                                LCN {pageSize > 0 ? (currentPage - 1) * pageSize + idx + 1 : idx + 1}
                              </span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handlePlayInApp(channel);
                                }}
                                className="flex items-center gap-1 rounded-md bg-cyan-500/20 px-2 py-1 text-[10px] font-bold text-cyan-700 hover:bg-cyan-500/30 transition"
                              >
                                <Play className="h-3 w-3 fill-cyan-400" />
                                <span>{t('watch')}</span>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* BARRA PAGINAZIONE INFERIORE */}
                      {pageSize > 0 && totalPages > 1 && (
                        <div className="mt-4 flex items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white/60 p-3 text-xs">
                          <button
                            type="button"
                            disabled={currentPage <= 1}
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            className="flex items-center gap-1 rounded-lg border border-slate-300 bg-slate-100 px-3 py-1.5 font-medium text-slate-800 transition hover:bg-slate-200 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <ChevronLeft className="h-4 w-4" />
                            <span>{t('page_prev')}</span>
                          </button>
                          <span className="font-bold text-cyan-700 px-2">
                            {t('page_info', { page: currentPage, pages: totalPages })}
                          </span>
                          <button
                            type="button"
                            disabled={currentPage >= totalPages}
                            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            className="flex items-center gap-1 rounded-lg border border-slate-300 bg-slate-100 px-3 py-1.5 font-medium text-slate-800 transition hover:bg-slate-200 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <span>{t('page_next')}</span>
                            <ChevronRight className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* TAB 2: GUIDA TV (EPG) */}
              {activeTab === 'epg' && (
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white/50 p-4">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 mb-1">{t('epg_title')}</h3>
                      <p className="text-xs text-slate-500">{t('epg_description')}</p>
                    </div>
                    {tvSettings.epg_url && (
                      <button
                        type="button"
                        disabled={epgRefreshing}
                        onClick={handleRefreshEpgNow}
                        className="flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-700 hover:bg-cyan-500/20 transition disabled:opacity-50"
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${epgRefreshing ? 'animate-spin' : ''}`} />
                        <span>{t('refresh')}</span>
                      </button>
                    )}
                  </div>

                  {epgStatusMessage && (
                    <div className="rounded-lg bg-cyan-950/40 border border-cyan-500/30 px-3 py-2 text-xs text-cyan-700">
                      {epgStatusMessage}
                    </div>
                  )}

                  <div className="flex flex-col gap-3">
                    {channelRows.slice(0, 30).map((channel) => (
                      <div
                        key={channel.id}
                        onClick={() => setSelectedChannel(channel)}
                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-slate-200/80 bg-white/60 p-3 hover:border-slate-300 transition cursor-pointer"
                      >
                        <div className="flex items-center gap-3 min-w-[200px]">
                          <ChannelLogo url={channel.logo} name={channel.name} size="sm" />
                          <div>
                            <h4 className="text-xs font-bold text-slate-900">{channel.name}</h4>
                            <span className="text-[10px] text-cyan-600">{channel.group || 'TV'}</span>
                          </div>
                        </div>

                        {/* Palinsesto reale o stato vuoto chiaro */}
                        <div className="flex-1 flex flex-col gap-1 max-w-lg">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-semibold text-slate-800">
                              {channelEpg?.channel_id === channel.id && channelEpg.now
                                ? channelEpg.now.title
                                : t('live_broadcast_title', { name: channel.name })}
                            </span>
                            <span className="text-slate-500 text-[10px]">
                              {channelEpg?.channel_id === channel.id && channelEpg.now?.time_remaining_min
                                ? `${channelEpg.now.time_remaining_min} min rimasti`
                                : 'In diretta'}
                            </span>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                              style={{
                                width: `${
                                  channelEpg?.channel_id === channel.id && channelEpg.now?.progress
                                    ? channelEpg.now.progress
                                    : 50
                                }%`,
                              }}
                            />
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handlePlayInApp(channel);
                            }}
                            className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 transition"
                          >
                            <Play className="h-3.5 w-3.5 fill-white" />
                            <span>{t('tune')}</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: SORGENTI & TUNER REALI */}
              {activeTab === 'tuners' && (
                <div className="flex flex-col gap-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white/50 p-4">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 mb-1">{t('tuners_title')}</h3>
                      <p className="text-xs text-slate-500">{t('tuners_description')}</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={discoveringTuners}
                        onClick={handleDiscoverTuners}
                        className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-200 disabled:opacity-50 transition"
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${discoveringTuners ? 'animate-spin text-cyan-600' : ''}`} />
                        <span>{discoveringTuners ? t('discovering_tuners') : t('discover_tuners')}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setShowAddTunerModal(true)}
                        className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 transition shadow-sm"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        <span>{t('add_tuner_manual')}</span>
                      </button>
                    </div>
                  </div>

                  {/* Form Modale / Inline per aggiungere un tuner manuale */}
                  {showAddTunerModal && (
                    <div className="rounded-xl border border-cyan-500/40 bg-white/90 p-4 shadow-xl">
                      <h4 className="text-xs font-bold text-slate-900 mb-3 flex items-center justify-between">
                        <span>{t('add_tuner_manual')}</span>
                        <button
                          type="button"
                          onClick={() => setShowAddTunerModal(false)}
                          className="text-slate-500 hover:text-slate-900"
                        >
                          ×
                        </button>
                      </h4>
                      <form onSubmit={handleAddTunerSubmit} className="flex flex-col gap-3">
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div>
                            <label className="block text-[11px] font-bold text-slate-500 mb-1">{t('tuner_name')}</label>
                            <input
                              type="text"
                              required
                              value={newTunerName}
                              onChange={(e) => setNewTunerName(e.target.value)}
                              placeholder="es. Ricevitore USB DVB-T2"
                              className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                            />
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-slate-500 mb-1">{t('tuner_type')}</label>
                            <select
                              value={newTunerType}
                              onChange={(e) => setNewTunerType(e.target.value)}
                              className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                            >
                              <option value="dvb_t2">DVB-T / DVB-T2 (Digitale Terrestre)</option>
                              <option value="hdhomerun">HDHomeRun (Sintonizzatore di Rete)</option>
                              <option value="sat_ip">SAT&gt;IP (Satellite / Terrestre IP)</option>
                              <option value="enigma2">Enigma2 / Dreambox OpenWebif</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-[11px] font-bold text-slate-500 mb-1">{t('tuner_device')}</label>
                            <input
                              type="text"
                              required
                              value={newTunerDevice}
                              onChange={(e) => setNewTunerDevice(e.target.value)}
                              placeholder="/dev/dvb/adapter0 oppure 192.168.1.150:65001"
                              className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                            />
                          </div>
                        </div>

                        <div className="flex justify-end gap-2 mt-2">
                          <button
                            type="button"
                            onClick={() => setShowAddTunerModal(false)}
                            className="rounded-lg border border-slate-300 bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600"
                          >
                            Annulla
                          </button>
                          <button
                            type="submit"
                            className="rounded-lg bg-cyan-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-cyan-500"
                          >
                            {t('save_tuner')}
                          </button>
                        </div>
                      </form>
                    </div>
                  )}

                  {/* Lista Tuner o Empty State reale */}
                  {tunersList.length === 0 ? (
                    <div className="rounded-xl border border-slate-200/80 bg-white/40 p-8 text-center">
                      <Radio className="mx-auto h-12 w-12 text-slate-600 mb-3" />
                      <h4 className="text-sm font-bold text-slate-900 mb-1">Nessun Tuner Rilevato</h4>
                      <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">{t('tuners_empty')}</p>
                      <div className="flex items-center justify-center gap-3">
                        <button
                          type="button"
                          onClick={handleDiscoverTuners}
                          className="rounded-lg border border-slate-300 bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-900 hover:bg-slate-200 transition"
                        >
                          {t('discover_tuners')}
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowAddTunerModal(true)}
                          className="rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition"
                        >
                          {t('add_tuner_manual')}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {tunersList.map((tuner) => (
                        <div
                          key={tuner.id}
                          className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm"
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <Radio className="h-5 w-5 text-emerald-600" />
                                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                  {tuner.type.toUpperCase()}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                    tuner.status === 'online'
                                      ? 'bg-emerald-500/20 text-emerald-700'
                                      : 'bg-amber-500/20 text-amber-700'
                                  }`}
                                >
                                  {tuner.status.toUpperCase()}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveTuner(tuner.id)}
                                  className="text-slate-500 hover:text-rose-600 p-1"
                                  title={t('delete_tuner')}
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>

                            <h4 className="mt-2 text-sm font-bold text-slate-900">{tuner.name}</h4>
                            <p className="text-[11px] font-mono text-slate-500 mt-0.5">{tuner.device}</p>

                            <div className="mt-4 flex flex-col gap-2 rounded-lg bg-slate-50/60 p-3 border border-slate-200">
                              <div>
                                <div className="flex justify-between text-[10px] font-bold text-slate-500">
                                  <span>{t('signal_strength')}</span>
                                  <span className="text-emerald-600">{tuner.signal_strength}%</span>
                                </div>
                                <div className="mt-1 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                                  <div
                                    className="h-full bg-emerald-500"
                                    style={{ width: `${tuner.signal_strength}%` }}
                                  />
                                </div>
                              </div>

                              <div>
                                <div className="flex justify-between text-[10px] font-bold text-slate-500">
                                  <span>{t('signal_quality')}</span>
                                  <span className="text-cyan-600">{tuner.signal_quality}%</span>
                                </div>
                                <div className="mt-1 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                                  <div
                                    className="h-full bg-cyan-500"
                                    style={{ width: `${tuner.signal_quality}%` }}
                                  />
                                </div>
                              </div>

                              <div className="flex justify-between pt-1 text-[11px]">
                                <span className="text-slate-500">{t('channels_locked')}</span>
                                <span className="font-bold text-slate-900">{tuner.channels_count} canali</span>
                              </div>
                            </div>
                          </div>

                          <div className="mt-4 pt-3 border-t border-slate-200">
                            <button
                              type="button"
                              disabled={scanningTunerId === tuner.id}
                              onClick={() => handleScanTuner(tuner.id)}
                              className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-200 disabled:opacity-50 transition"
                            >
                              <RefreshCw
                                className={`h-3.5 w-3.5 ${scanningTunerId === tuner.id ? 'animate-spin text-cyan-600' : ''}`}
                              />
                              <span>{scanningTunerId === tuner.id ? t('scanning') : t('scan_frequencies')}</span>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: PLAYLIST & M3U */}
              {activeTab === 'playlists' && (
                <div className="flex flex-col gap-6 max-w-4xl">
                  {/* Playlist Esistenti */}
                  <div className="rounded-xl border border-slate-200 bg-white/60 p-4">
                    <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                      <ListVideo className="h-4 w-4 text-purple-600" />
                      <span>{t('active_playlists')}</span>
                    </h3>

                    {!data || data.playlists.length === 0 ? (
                      <Empty>{t('playlists_empty')}</Empty>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {data.playlists.map((pl) => (
                          <div
                            key={pl.id}
                            className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3"
                          >
                            <div>
                              <h4 className="text-xs font-bold text-slate-900">{pl.name}</h4>
                              <p className="text-[10px] text-slate-500">
                                {pl.source === 'url' ? t('source_remote_url') : t('source_uploaded_file')} ·{' '}
                                {pl.count} canali
                              </p>
                            </div>

                            <div className="flex items-center gap-1.5">
                              {pl.has_url && (
                                <button
                                  type="button"
                                  onClick={() => void run(() => refreshPlaylist(pl.id))}
                                  className="p-1.5 text-slate-500 hover:text-slate-900 transition"
                                  title={t('refresh')}
                                >
                                  <RefreshCw className="h-4 w-4" />
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => void run(() => removePlaylist(pl.id))}
                                className="p-1.5 text-rose-600 hover:text-rose-700 transition"
                                title={t('delete')}
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Aggiunta nuova playlist via URL */}
                  <div className="rounded-xl border border-slate-200 bg-white/60 p-4">
                    <h3 className="text-sm font-bold text-slate-900 mb-3">{t('add_playlist_url_title')}</h3>
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (!newPlaylistName.trim() || !newPlaylistUrl.trim()) return;
                        await run(() => addPlaylist(newPlaylistName.trim(), newPlaylistUrl.trim(), ''));
                        setNewPlaylistName('');
                        setNewPlaylistUrl('');
                      }}
                      className="flex flex-col gap-3"
                    >
                      <div>
                        <label className="block text-[11px] font-bold text-slate-500 mb-1">{t('playlist_name')}</label>
                        <input
                          type="text"
                          required
                          value={newPlaylistName}
                          onChange={(e) => setNewPlaylistName(e.target.value)}
                          placeholder="es. Canali Nazionali & Sport"
                          className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-bold text-slate-500 mb-1">{t('playlist_url')}</label>
                        <input
                          type="url"
                          required
                          value={newPlaylistUrl}
                          onChange={(e) => setNewPlaylistUrl(e.target.value)}
                          placeholder="https://provider.example/live/playlist.m3u8"
                          className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={busy}
                        className="mt-2 rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 self-start"
                      >
                        {t('add_playlist')}
                      </button>
                    </form>
                  </div>
                </div>
              )}

              {/* TAB 5: IMPOSTAZIONI TV & SICUREZZA VPN */}
              {activeTab === 'settings' && (
                <div className="flex flex-col gap-4 max-w-3xl">
                  {/* Sezione VPN Obbligatoria */}
                  <div className="rounded-xl border border-slate-200 bg-white/60 p-5 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="h-5 w-5 text-cyan-600" />
                      <h3 className="text-sm font-bold text-slate-900">{t('vpn_security_title')}</h3>
                    </div>
                    <p className="text-xs text-slate-500 mb-4">{t('vpn_required_desc')}</p>

                    <div className="flex flex-col gap-4 text-xs">
                      <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                        <div>
                          <label className="font-semibold text-slate-800 block">{t('vpn_required_label')}</label>
                          <span className="text-[11px] text-slate-500">Blocca i flussi IPTV se non protetti da VPN</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={tvSettings.vpn_required}
                          onChange={(e) => handleToggleVpnRequired(e.target.checked)}
                          className="h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
                        />
                      </div>

                      {tvSettings.vpn_required && (
                        <div>
                          <label className="block font-semibold text-slate-800 mb-1">{t('vpn_profile_label')}</label>
                          <input
                            type="text"
                            value={tvSettings.vpn_profile}
                            onChange={(e) => setTvSettings({ ...tvSettings, vpn_profile: e.target.value })}
                            onBlur={(e) => handleUpdateVpnProfile(e.target.value.trim())}
                            placeholder={t('vpn_profile_placeholder')}
                            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                          />
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Sezione Guida EPG XMLTV Reale */}
                  <div className="rounded-xl border border-slate-200 bg-white/60 p-5 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <Calendar className="h-5 w-5 text-purple-600" />
                      <h3 className="text-sm font-bold text-slate-900">{t('epg_xmltv_title')}</h3>
                    </div>
                    <p className="text-xs text-slate-500 mb-4">{t('epg_xmltv_desc')}</p>

                    <div className="flex flex-col gap-3 text-xs">
                      <div>
                        <label className="block font-semibold text-slate-800 mb-1">{t('epg_xmltv_url')}</label>
                        <input
                          type="url"
                          value={tvSettings.epg_url}
                          onChange={(e) => setTvSettings({ ...tvSettings, epg_url: e.target.value })}
                          onBlur={(e) => void updateSettings({ epg_url: e.target.value.trim() })}
                          placeholder="https://epg.example/it.xml.gz"
                          className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                        />
                      </div>

                      <div className="flex items-center gap-3 mt-1">
                        <button
                          type="button"
                          disabled={epgRefreshing || !tvSettings.epg_url.trim()}
                          onClick={handleRefreshEpgNow}
                          className="flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-xs font-bold text-white hover:bg-purple-500 disabled:opacity-50 transition"
                        >
                          <RefreshCw className={`h-3.5 w-3.5 ${epgRefreshing ? 'animate-spin' : ''}`} />
                          <span>{t('refresh_epg_now')}</span>
                        </button>
                        {epgStatusMessage && (
                          <span className="text-[11px] text-purple-700">{epgStatusMessage}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Sezione Buffer e Relay */}
                  <div className="rounded-xl border border-slate-200 bg-white/60 p-5 shadow-sm">
                    <h3 className="text-sm font-bold text-slate-900 mb-3">{t('stream_settings_title')}</h3>
                    <div className="flex flex-col gap-4 text-xs">
                      <div>
                        <label className="block font-semibold text-slate-800 mb-1">{t('buffer_size_label')}</label>
                        <p className="text-[11px] text-slate-500 mb-2">{t('buffer_size_desc')}</p>
                        <select
                          value={tvSettings.buffer_size}
                          onChange={(e) => {
                            const val = e.target.value as any;
                            setTvSettings({ ...tvSettings, buffer_size: val });
                            void updateSettings({ buffer_size: val });
                          }}
                          className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-slate-900"
                        >
                          <option value="low">{t('buffer_low')}</option>
                          <option value="medium">{t('buffer_medium')}</option>
                          <option value="high">{t('buffer_high')}</option>
                        </select>
                      </div>

                      <div className="pt-3 border-t border-slate-200">
                        <label className="block font-semibold text-slate-800 mb-1">{t('relay_signature_label')}</label>
                        <p className="text-[11px] text-slate-500 mb-2">{t('relay_signature_desc')}</p>
                        <span className="inline-flex items-center rounded-md bg-emerald-500/20 px-2.5 py-1 text-[11px] font-semibold text-emerald-600">
                          {t('secure_relay_active')}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        }
        inspector={
          <OSInspector
            title={t('inspector_title')}
            subtitle={selectedChannel ? selectedChannel.name : t('no_channel_selected')}
            onClose={() => setSelectedChannel(null)}
          >
            {selectedChannel ? (
              <div className="flex flex-col gap-4 text-xs">
                {/* Logo grande canale */}
                <div className="aspect-video w-full rounded-2xl overflow-hidden bg-white/80 flex items-center justify-center border border-slate-200 p-4">
                  <ChannelLogo url={selectedChannel.logo} name={selectedChannel.name} size="hero" />
                </div>

                <div>
                  <h4 className="font-bold text-slate-900 text-sm">{selectedChannel.name}</h4>
                  <p className="text-cyan-600 text-xs">{selectedChannel.group || t('generic_category')}</p>
                </div>

                {/* Dati EPG del canale */}
                <div className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white/60 p-3">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    {t('on_air_now')}
                  </span>
                  {channelEpg?.now ? (
                    <>
                      <div className="font-semibold text-slate-900">{channelEpg.now.title}</div>
                      <p className="text-[11px] text-slate-500 leading-relaxed">{channelEpg.now.description}</p>
                      {channelEpg.now.progress !== undefined && (
                        <div className="mt-1">
                          <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                            <div
                              className="h-full bg-cyan-400"
                              style={{ width: `${channelEpg.now.progress}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-slate-500 mt-1 block">
                            {channelEpg.now.time_remaining_min} {t('minutes_remaining')}
                          </span>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-[11px] text-slate-500">{t('epg_no_schedule')}</p>
                  )}
                </div>

                {/* Prossimo Programma */}
                {channelEpg?.next && (
                  <div className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-white/40 p-3">
                    <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      {t('next_program')}
                    </span>
                    <span className="font-semibold text-slate-800">{channelEpg.next.title}</span>
                    <span className="text-[10px] text-slate-500">{channelEpg.next.genre}</span>
                  </div>
                )}

                {/* Azioni Play / Cast */}
                <div className="flex flex-col gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => handlePlayInApp(selectedChannel)}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition shadow-sm"
                  >
                    <Play className="h-3.5 w-3.5 fill-white" />
                    <span>{t('watch_in_window')}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsCastOpen(true)}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-700 hover:bg-cyan-500/20 transition"
                  >
                    <Cast className="h-3.5 w-3.5 text-cyan-600" />
                    <span>{t('cast_to_selected')}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => void handleToggleFavorite(selectedChannel)}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 transition"
                  >
                    <Star className={`h-3.5 w-3.5 ${selectedChannel.favorite ? 'fill-amber-400 text-amber-600' : ''}`} />
                    <span>{selectedChannel.favorite ? t('remove_favorite') : t('add_favorite')}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-slate-500">
                <Tv className="h-10 w-10 text-slate-700" />
                <p className="text-xs">{t('select_channel_for_details')}</p>
              </div>
            )}
          </OSInspector>
        }
        isInspectorOpen={true}
      />

      <CastModal
        isOpen={isCastOpen}
        onClose={() => setIsCastOpen(false)}
        channelName={activeStreamChannel?.name || selectedChannel?.name || ''}
        channelId={activeStreamChannel?.id || selectedChannel?.id || ''}
        channelLogo={activeStreamChannel?.logo || selectedChannel?.logo}
        t={t}
      />
    </div>
  );
};

export default View;
