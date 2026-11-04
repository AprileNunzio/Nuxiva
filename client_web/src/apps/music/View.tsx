import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useOSApp, useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
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
  fetchLibraryOverview,
  fetchHome,
  fetchTracks,
  searchMusic,
  fetchPlaylists,
  createPlaylist,
  fetchPlaylistDetails,
  fetchLyrics,
  toggleLike,
  reportPlayed,
  uploadMediaFile,
  triggerLibraryScan,
  getStreamUrl,
  getCoverUrl,
  askMusicMCP,
  fetchMusicSettings,
  saveMusicSettings,
} from './api';
import { Track, Playlist, LyricsResponse, LibraryOverview, HomeMixes, MusicSettings } from './types';
import {
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Shuffle,
  Repeat,
  Volume2,
  VolumeX,
  Heart,
  ListMusic,
  Music,
  Film,
  Mic2,
  UploadCloud,
  Sparkles,
  Plus,
  Check,
  Copy,
  RefreshCw,
  Clock,
  Disc,
  Compass,
  Sliders,
  Save,
  Cast,
} from 'lucide-react';
import { CastModal } from './CastModal';
import './style.css';

function formatDuration(seconds: number): string {
  if (!seconds || isNaN(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/music');
  const os = useOSApp();

  const [activeTab, setActiveTab] = useState<'home' | 'tracks' | 'playlists' | 'karaoke' | 'upload' | 'settings'>('home');
  const [library, setLibrary] = useState<LibraryOverview | null>(null);
  const [homeData, setHomeData] = useState<HomeMixes | null>(null);
  const [tracks, setTracks] = useState<readonly Track[]>([]);
  const [playlists, setPlaylists] = useState<readonly Playlist[]>([]);
  const [selectedPlaylist, setSelectedPlaylist] = useState<Playlist | null>(null);
  const [loading, setLoading] = useState(true);

  // Settings state
  const [musicSettings, setMusicSettings] = useState<MusicSettings>({
    NUXIVA_MUSIC_SCANNER_ENABLED: '1',
    NUXIVA_MUSIC_SCAN_MIN: '15',
    NUXIVA_MUSIC_RECOGNITION: '1',
    NUXIVA_MUSIC_IDENTIFY: '1',
    NUXIVA_MUSIC_COVERS: '1',
    NUXIVA_MUSIC_LYRICS: '1',
    NUXIVA_MUSIC_ORGANIZE: '1',
    NUXIVA_MUSIC_TRANSCODE: 'auto',
    NUXIVA_MUSIC_TRANSCODE_KBPS: '192',
    NUXIVA_MUSIC_CROSSFADE: '0',
    NUXIVA_MUSIC_RADIO: '1',
    NUXIVA_MUSIC_CAST: '1',
    NUXIVA_MUSIC_VOICE: '1',
    NUXIVA_MUSIC_TAGS: '1',
    NUXIVA_MUSIC_RENAME: '1',
  });
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsFeedback, setSettingsFeedback] = useState<string | null>(null);
  const [scanTriggered, setScanTriggered] = useState(false);

  // Playback state
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [isShuffle, setIsShuffle] = useState(false);
  const [isRepeat, setIsRepeat] = useState(false);
  const [castModalOpen, setCastModalOpen] = useState(false);

  // Selection & Details
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const [lyricsData, setLyricsData] = useState<LyricsResponse>({});
  const [copiedUnc, setCopiedUnc] = useState(false);

  // Playlist creation
  const [newPlaylistOpen, setNewPlaylistOpen] = useState(false);
  const [playlistName, setPlaylistName] = useState('');
  const [playlistDesc, setPlaylistDesc] = useState('');

  // Upload status
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  // MCP AI Assistant
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  // Media element refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const lyricsContainerRef = useRef<HTMLDivElement | null>(null);

  // Load initial library overview, home mixes, and tracks
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [libData, home, trackList, playlistList] = await Promise.all([
        fetchLibraryOverview().catch(() => null),
        fetchHome().catch(() => null),
        fetchTracks({ limit: 120 }).catch(() => ({ tracks: [], total: 0 })),
        fetchPlaylists().catch(() => []),
      ]);
      if (libData) setLibrary(libData);
      if (home) setHomeData(home);
      setTracks(trackList.tracks || []);
      setPlaylists(playlistList);
    } catch {
      // noop
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    setSettingsLoading(true);
    try {
      const data = await fetchMusicSettings();
      if (data && Object.keys(data).length > 0) {
        setMusicSettings((prev) => ({ ...prev, ...data }));
      }
    } finally {
      setSettingsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
    void loadSettings();
  }, [loadData, loadSettings]);

  // Synchronize OS Breadcrumbs
  useEffect(() => {
    const tabLabels: Record<string, string> = {
      home: t('tab_home'),
      tracks: t('tab_tracks'),
      playlists: selectedPlaylist ? selectedPlaylist.name : t('tab_playlists'),
      karaoke: t('tab_karaoke'),
      upload: t('tab_upload'),
      settings: t('tab_settings'),
    };

    const crumbs = [
      {
        id: 'root',
        label: 'Nexus Media Player',
        onClick: () => {
          setActiveTab('home');
          setSelectedPlaylist(null);
        },
      },
      {
        id: activeTab,
        label: tabLabels[activeTab] || activeTab,
        onClick: selectedPlaylist
          ? () => setSelectedPlaylist(null)
          : undefined,
      },
    ];

    if (currentTrack) {
      crumbs.push({
        id: `track-${currentTrack.id}`,
        label: currentTrack.title,
        onClick: undefined,
      });
    }

    os.setBreadcrumbs?.(crumbs);
  }, [activeTab, selectedPlaylist, currentTrack, os, t]);

  // Synchronize OS Status Bar
  useEffect(() => {
    os.setStatus({
      connected: true,
      itemCount: tracks.length,
      details: currentTrack
        ? `${isPlaying ? '▶' : '⏸'} ${currentTrack.title} — ${currentTrack.artist}`
        : t('status_available', { count: tracks.length }),
    });
  }, [tracks.length, currentTrack, isPlaying, os, t]);

  // Toolbar Actions handler
  useWindowToolbar(
    useCallback(
      (id: string, value?: string) => {
        if (id === 'search') {
          os.setSearchQuery(value || '');
          if (value && activeTab !== 'tracks') {
            setActiveTab('tracks');
          }
        }
        if (id === 'refresh') {
          void loadData();
          void triggerLibraryScan();
        }
      },
      [loadData, activeTab, os]
    )
  );

  // Settings actions
  const handleSaveSettings = useCallback(async () => {
    setSettingsSaving(true);
    setSettingsFeedback(null);
    try {
      await saveMusicSettings(musicSettings as Record<string, string>);
      setSettingsFeedback(t('settings_saved'));
      setTimeout(() => setSettingsFeedback(null), 4000);
    } catch {
      setSettingsFeedback('Errore durante il salvataggio');
      setTimeout(() => setSettingsFeedback(null), 4000);
    } finally {
      setSettingsSaving(false);
    }
  }, [musicSettings, t]);

  const handleTriggerScan = useCallback(async () => {
    setScanTriggered(true);
    try {
      await triggerLibraryScan();
      await loadData();
      setSettingsFeedback(t('settings_scan_started'));
      setTimeout(() => setSettingsFeedback(null), 4000);
    } catch {
      setSettingsFeedback('Errore avvio scansione');
      setTimeout(() => setSettingsFeedback(null), 4000);
    } finally {
      setTimeout(() => setScanTriggered(false), 2000);
    }
  }, [loadData, t]);

  // Play track
  const handlePlayTrack = useCallback((track: Track) => {
    setCurrentTrack(track);
    setSelectedTrack(track);
    setIsPlaying(true);
    setCurrentTime(0);

    // Fetch lyrics for karaoke
    void fetchLyrics(track.id).then(setLyricsData);

    const mediaEl = (track.is_video || track.path?.match(/\.(mp4|webm|mkv)$/i))
      ? videoRef.current
      : audioRef.current;

    if (mediaEl) {
      mediaEl.src = getStreamUrl(track.id);
      mediaEl.currentTime = 0;
      void mediaEl.play();
    }
  }, []);

  const togglePlayPause = () => {
    if (!currentTrack) {
      if (tracks.length > 0) handlePlayTrack(tracks[0]);
      return;
    }
    const mediaEl = currentTrack.is_video ? videoRef.current : audioRef.current;
    if (mediaEl) {
      if (isPlaying) {
        mediaEl.pause();
        setIsPlaying(false);
      } else {
        void mediaEl.play();
        setIsPlaying(true);
      }
    }
  };

  const handleNext = useCallback(() => {
    if (tracks.length === 0) return;
    if (isShuffle) {
      const randIdx = Math.floor(Math.random() * tracks.length);
      handlePlayTrack(tracks[randIdx]);
      return;
    }
    if (!currentTrack) {
      handlePlayTrack(tracks[0]);
      return;
    }
    const curIdx = tracks.findIndex((t) => t.id === currentTrack.id);
    const nextIdx = (curIdx + 1) % tracks.length;
    handlePlayTrack(tracks[nextIdx]);
  }, [tracks, currentTrack, isShuffle, handlePlayTrack]);

  const handlePrev = useCallback(() => {
    if (tracks.length === 0) return;
    if (!currentTrack) {
      handlePlayTrack(tracks[0]);
      return;
    }
    const curIdx = tracks.findIndex((t) => t.id === currentTrack.id);
    const prevIdx = (curIdx - 1 + tracks.length) % tracks.length;
    handlePlayTrack(tracks[prevIdx]);
  }, [tracks, currentTrack, handlePlayTrack]);

  // Audio/Video Time & End handlers
  const onTimeUpdate = (e: React.SyntheticEvent<HTMLMediaElement>) => {
    const el = e.currentTarget;
    setCurrentTime(el.currentTime);
  };

  const onLoadedMetadata = (e: React.SyntheticEvent<HTMLMediaElement>) => {
    const el = e.currentTarget;
    setDuration(el.duration);
  };

  const onEnded = () => {
    if (currentTrack) {
      void reportPlayed(currentTrack.id, currentTime, true);
    }
    if (isRepeat) {
      const mediaEl = currentTrack?.is_video ? videoRef.current : audioRef.current;
      if (mediaEl) {
        mediaEl.currentTime = 0;
        void mediaEl.play();
      }
    } else {
      handleNext();
    }
  };

  // Like track toggle
  const handleToggleLike = async (track: Track) => {
    const newLiked = !track.liked;
    try {
      await toggleLike(track.id, newLiked);
      setTracks((prev) =>
        prev.map((t) => (t.id === track.id ? { ...t, liked: newLiked } : t))
      );
      if (currentTrack?.id === track.id) {
        setCurrentTrack((prev) => (prev ? { ...prev, liked: newLiked } : null));
      }
      if (selectedTrack?.id === track.id) {
        setSelectedTrack((prev) => (prev ? { ...prev, liked: newLiked } : null));
      }
    } catch {
      // noop
    }
  };

  // Universal File Upload Handler
  const processFilesUpload = useCallback(async (files: File[]) => {
    if (!files || files.length === 0) return;
    setUploadStatus(t('uploading_files', { count: files.length }));
    setUploadProgress(10);
    try {
      for (let i = 0; i < files.length; i++) {
        await uploadMediaFile(files[i]);
        setUploadProgress(Math.round(((i + 1) / files.length) * 100));
      }
      setUploadStatus(t('upload_success'));
      await triggerLibraryScan().catch(() => {});
      await loadData();
      setTimeout(() => {
        setUploadStatus(null);
        setUploadProgress(null);
      }, 2000);
    } catch (err) {
      setUploadStatus(t('upload_error', { error: err instanceof Error ? err.message : '' }));
    }
  }, [loadData, t]);

  const { openPicker: openUploadPicker, fileInput: uploadFileInput } = useOSFileUpload(
    processFilesUpload,
    {
      accept: 'audio/*,video/*,.mp3,.flac,.wav,.ogg,.m4a,.aac,.opus,.mp4,.webm,.mkv,.mov',
      multiple: true,
    }
  );

  // Create playlist
  const handleCreatePlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!playlistName.trim()) return;
    try {
      const res = await createPlaylist(playlistName.trim(), playlistDesc.trim());
      setNewPlaylistOpen(false);
      setPlaylistName('');
      setPlaylistDesc('');
      const updatedPlaylists = await fetchPlaylists();
      setPlaylists(updatedPlaylists);
      const created = updatedPlaylists.find((p) => p.id === res.id);
      if (created) setSelectedPlaylist(created);
    } catch (err) {
      alert(t('playlist_create_error') + (err instanceof Error ? `: ${err.message}` : ''));
    }
  };

  // MCP AI music query
  const handleAskAI = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    setAiResponse(null);
    try {
      const reply = await askMusicMCP(aiQuery.trim());
      setAiResponse(reply);
      // Also trigger a search matching keywords in local library
      const matched = await searchMusic(aiQuery.trim());
      if (matched.tracks && matched.tracks.length > 0) {
        handlePlayTrack(matched.tracks[0]);
      }
    } catch (err) {
      setAiResponse(t('ai_error', { error: err instanceof Error ? err.message : '' }));
    } finally {
      setAiLoading(false);
    }
  };

  // Filtered tracks
  const searchQuery = (os.searchQuery || '').trim().toLowerCase();
  const displayedTracks = useMemo(() => {
    let list = selectedPlaylist?.tracks || tracks;
    if (searchQuery) {
      list = list.filter(
        (t) =>
          t.title.toLowerCase().includes(searchQuery) ||
          t.artist.toLowerCase().includes(searchQuery) ||
          t.album.toLowerCase().includes(searchQuery)
      );
    }
    return list;
  }, [selectedPlaylist, tracks, searchQuery]);

  // Karaoke current lyric line index
  const activeLyricIndex = useMemo(() => {
    if (!lyricsData.synced || lyricsData.synced.length === 0) return -1;
    let idx = -1;
    for (let i = 0; i < lyricsData.synced.length; i++) {
      if (currentTime >= lyricsData.synced[i].time) {
        idx = i;
      } else {
        break;
      }
    }
    return idx;
  }, [lyricsData.synced, currentTime]);

  // Auto-scroll active lyric
  useEffect(() => {
    if (activeLyricIndex >= 0 && lyricsContainerRef.current) {
      const activeEl = lyricsContainerRef.current.children[activeLyricIndex] as HTMLElement | undefined;
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeLyricIndex]);

  // Sidebar items
  const sidebarNavItems = [
    {
      id: 'home',
      label: t('tab_home'),
      icon: <Compass className="h-4 w-4 text-sky-600" />,
    },
    {
      id: 'tracks',
      label: t('tab_tracks'),
      icon: <Music className="h-4 w-4 text-emerald-600" />,
      count: tracks.length,
    },
    {
      id: 'playlists',
      label: t('tab_playlists'),
      icon: <ListMusic className="h-4 w-4 text-purple-600" />,
      count: playlists.length,
    },
    {
      id: 'karaoke',
      label: t('tab_karaoke'),
      icon: <Mic2 className="h-4 w-4 text-amber-600" />,
    },
    {
      id: 'upload',
      label: t('tab_upload'),
      icon: <UploadCloud className="h-4 w-4 text-blue-600" />,
    },
    {
      id: 'settings',
      label: t('tab_settings'),
      icon: <Sliders className="h-4 w-4 text-cyan-600" />,
    },
  ];

  const sidebarFooter = library ? (
    <div className="flex flex-col gap-1.5 rounded-lg border border-slate-300/60 bg-white/80 p-2.5 text-[11px] text-slate-600">
      <div className="flex items-center justify-between font-semibold">
        <span className="flex items-center gap-1.5 text-sky-600">
          <Disc className="h-3.5 w-3.5" />
          <span>{t('library_smb')}</span>
        </span>
        <span className="font-mono text-slate-500">{t('tracks_count', { count: library.tracks })}</span>
      </div>
      <div className="text-[10px] text-slate-500 font-mono truncate" title={library.root}>
        {library.root}
      </div>
    </div>
  ) : null;

  return (
    <div className="nexus-player-app h-full w-full">
      {/* Hidden audio element for pure sound tracks */}
      <audio
        ref={audioRef}
        onTimeUpdate={onTimeUpdate}
        onLoadedMetadata={onLoadedMetadata}
        onEnded={onEnded}
      />

      {uploadFileInput}

      <OSAppLayout
        onFilesDrop={processFilesUpload}
        dropLabel={t('drop_action')}
        dropHint={t('drop_hint')}
        isUploading={Boolean(uploadProgress !== null || uploadStatus)}
        uploadStatus={uploadStatus}
        uploadProgress={uploadProgress}
        sidebar={
          <OSSidebar
            title="Nexus Media Player"
            items={sidebarNavItems}
            activeId={activeTab}
            onSelect={(id) => {
              setActiveTab(id as typeof activeTab);
              if (id !== 'playlists') setSelectedPlaylist(null);
            }}
            footer={sidebarFooter}
          />
        }
        content={
          <div className="flex h-full flex-col overflow-hidden bg-slate-50 text-slate-900">
            {/* Top Workspace Header Bar */}
            <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 bg-white/60 px-5 py-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-slate-900 capitalize">
                  {selectedPlaylist ? selectedPlaylist.name : t(`tab_${activeTab}`)}
                </span>
                {currentTrack && isPlaying && (
                  <div className="flex items-center gap-1">
                    <span className="nexus-eq-bar" />
                    <span className="nexus-eq-bar" />
                    <span className="nexus-eq-bar" />
                    <span className="nexus-eq-bar" />
                  </div>
                )}
              </div>

              {/* Quick AI & Actions */}
              <div className="flex items-center gap-2">
                <form onSubmit={handleAskAI} className="relative flex items-center">
                  <Sparkles className="absolute left-2.5 h-3.5 w-3.5 text-amber-600" />
                  <input
                    type="text"
                    placeholder={t('ask_ai_placeholder')}
                    value={aiQuery}
                    onChange={(e) => setAiQuery(e.target.value)}
                    className="w-56 rounded-full border border-slate-300 bg-white py-1 pl-8 pr-3 text-xs text-slate-900 placeholder-slate-500 focus:border-sky-400 focus:outline-none"
                  />
                  {aiLoading && (
                    <span className="absolute right-2.5 text-[10px] text-amber-600 animate-pulse">…</span>
                  )}
                </form>

                <button
                  type="button"
                  onClick={() => {
                    void loadData();
                    void triggerLibraryScan();
                  }}
                  title={t('refresh_library')}
                  className="rounded-lg border border-slate-300 bg-slate-100 p-1.5 text-slate-600 hover:bg-slate-200 transition"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
              </div>
            </header>

            {/* AI Response Banner if present */}
            {aiResponse && (
              <div className="flex items-center justify-between border-b border-amber-500/30 bg-amber-500/10 px-5 py-2 text-xs text-amber-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber-600 shrink-0" />
                  <span>{aiResponse}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setAiResponse(null)}
                  className="p-1 hover:text-slate-900"
                >
                  ×
                </button>
              </div>
            )}

            {/* Workspace View Switcher */}
            <div className="flex-1 overflow-auto p-5">
              {loading && <Loading label={t('loading')} />}

              {/* TAB 1: HOME */}
              {!loading && activeTab === 'home' && (
                <div className="flex flex-col gap-6">
                  {/* Hero card */}
                  <div className="relative overflow-hidden rounded-2xl border border-white/20 bg-gradient-to-r from-sky-600 via-indigo-600 to-purple-700 p-6 shadow-xl shadow-indigo-900/15">
                    {/* Decorative glowing ambient orb */}
                    <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
                    <div className="pointer-events-none absolute -left-16 -bottom-16 h-64 w-64 rounded-full bg-sky-400/20 blur-3xl" />

                    <div className="relative z-10 flex flex-col sm:flex-row items-center gap-6">
                      <div className="h-28 w-28 shrink-0 overflow-hidden rounded-2xl border-2 border-white/30 bg-white/15 shadow-2xl backdrop-blur-md flex items-center justify-center">
                        {currentTrack?.cover ? (
                          <img
                            src={getCoverUrl(currentTrack.album_key)}
                            alt=""
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <Music className="h-12 w-12 text-slate-900 drop-shadow-md" />
                        )}
                      </div>
                      <div className="flex-1 text-center sm:text-left">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-0.5 text-[11px] font-bold tracking-wider text-slate-900 uppercase backdrop-blur-md border border-white/25">
                          <Sparkles className="h-3 w-3 text-amber-700" />
                          <span>{currentTrack ? t('hero_now_playing') : 'Nexus Media Player'}</span>
                        </span>
                        <h2 className="text-2xl font-black text-slate-900 tracking-tight drop-shadow-sm mt-2">
                          {currentTrack ? currentTrack.title : t('hero_explore_title')}
                        </h2>
                        <p className="text-sm font-medium text-sky-100 mt-1 leading-relaxed">
                          {currentTrack
                            ? `${currentTrack.artist} · ${currentTrack.album}`
                            : t('hero_explore_subtitle', { count: tracks.length })}
                        </p>
                        <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 mt-4">
                          <button
                            type="button"
                            onClick={() => {
                              if (currentTrack) togglePlayPause();
                              else if (tracks.length > 0) handlePlayTrack(tracks[0]);
                            }}
                            className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-xs font-bold text-slate-900 hover:bg-sky-50 shadow-lg shadow-black/10 hover:scale-105 transition transform"
                          >
                            {isPlaying ? <Pause className="h-4 w-4 text-sky-600" /> : <Play className="h-4 w-4 text-sky-600" />}
                            <span>{isPlaying ? t('btn_pause') : t('btn_play_now')}</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setActiveTab('karaoke')}
                            className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/15 px-4 py-2.5 text-xs font-semibold text-slate-900 hover:bg-white/25 backdrop-blur-md shadow-md transition transform hover:scale-105"
                          >
                            <Mic2 className="h-3.5 w-3.5 text-amber-700" />
                            <span>{t('btn_karaoke_mode')}</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recently Played / Mixes */}
                  {homeData?.recent && homeData.recent.length > 0 && (
                    <section>
                      <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                        <Clock className="h-4 w-4 text-sky-600" />
                        <span>{t('recent_tracks')}</span>
                      </h3>
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                        {homeData.recent.slice(0, 6).map((track) => (
                          <div
                            key={track.id}
                            onClick={() => handlePlayTrack(track)}
                            className="group flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/60 p-3 hover:border-sky-500/50 hover:bg-slate-100 cursor-pointer transition"
                          >
                            <div className="relative aspect-square w-full rounded-lg overflow-hidden bg-slate-100 flex items-center justify-center">
                              {track.cover ? (
                                <img src={getCoverUrl(track.album_key)} alt="" className="h-full w-full object-cover" />
                              ) : (
                                <Music className="h-8 w-8 text-slate-500" />
                              )}
                              <button
                                type="button"
                                className="absolute bottom-2 right-2 rounded-full bg-sky-500 p-2 text-slate-950 opacity-0 group-hover:opacity-100 shadow-lg transition transform translate-y-1 group-hover:translate-y-0"
                              >
                                <Play className="h-4 w-4" />
                              </button>
                            </div>
                            <span className="truncate text-xs font-bold text-slate-900" title={track.title}>
                              {track.title}
                            </span>
                            <span className="truncate text-[11px] text-slate-500" title={track.artist}>
                              {track.artist}
                            </span>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {/* Real tracks in library */}
                  {tracks.length > 0 && (
                    <section>
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                          <Music className="h-4 w-4 text-emerald-600" />
                          <span>{t('latest_additions')}</span>
                        </h3>
                        <button
                          type="button"
                          onClick={() => setActiveTab('tracks')}
                          className="text-xs text-sky-600 hover:text-sky-700 font-medium"
                        >
                          {t('all_tracks')} ({tracks.length}) →
                        </button>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                        {tracks.slice(0, 6).map((track) => (
                          <div
                            key={track.id}
                            onClick={() => handlePlayTrack(track)}
                            className="group flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/60 p-3 hover:border-emerald-500/50 hover:bg-slate-100 cursor-pointer transition shadow-sm"
                          >
                            <div className="relative aspect-square w-full rounded-lg overflow-hidden bg-slate-100 flex items-center justify-center">
                              {track.cover ? (
                                <img src={getCoverUrl(track.album_key)} alt="" className="h-full w-full object-cover" />
                              ) : track.is_video ? (
                                <Film className="h-8 w-8 text-purple-600" />
                              ) : (
                                <Music className="h-8 w-8 text-slate-500" />
                              )}
                              <button
                                type="button"
                                className="absolute bottom-2 right-2 rounded-full bg-emerald-500 p-2 text-slate-950 opacity-0 group-hover:opacity-100 shadow-lg transition transform translate-y-1 group-hover:translate-y-0"
                              >
                                <Play className="h-4 w-4 fill-slate-950" />
                              </button>
                            </div>
                            <span className="truncate text-xs font-bold text-slate-900" title={track.title}>
                              {track.title}
                            </span>
                            <span className="truncate text-[11px] text-slate-500" title={track.artist}>
                              {track.artist}
                            </span>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {/* Playlists grid */}
                  <section>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        <ListMusic className="h-4 w-4 text-purple-600" />
                        <span>{t('tab_playlists')}</span>
                      </h3>
                      <button
                        type="button"
                        onClick={() => setNewPlaylistOpen(true)}
                        className="inline-flex items-center gap-1 text-xs text-sky-600 hover:text-sky-700"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        <span>{t('new_playlist')}</span>
                      </button>
                    </div>
                    {playlists.length === 0 ? (
                      <Empty>{t('empty_playlists')}</Empty>
                    ) : (
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                        {playlists.map((pl) => (
                          <div
                            key={pl.id}
                            onClick={() => {
                              setSelectedPlaylist(pl);
                              setActiveTab('playlists');
                              void fetchPlaylistDetails(pl.id).then(setSelectedPlaylist);
                            }}
                            className="group flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/60 p-3 hover:border-purple-500/50 cursor-pointer transition"
                          >
                            <div className="aspect-square w-full rounded-lg bg-gradient-to-br from-purple-900/50 to-slate-100 flex items-center justify-center">
                              <ListMusic className="h-10 w-10 text-purple-600 group-hover:scale-110 transition" />
                            </div>
                            <span className="truncate text-xs font-bold text-slate-900">{pl.name}</span>
                            <span className="text-[11px] text-slate-500">{t('tracks_count', { count: pl.count })}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                </div>
              )}

              {/* TAB 2: TRACKS / BRANI */}
              {!loading && (activeTab === 'tracks' || (activeTab === 'playlists' && selectedPlaylist)) && (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-base font-bold text-slate-900">
                        {selectedPlaylist ? selectedPlaylist.name : t('all_tracks')}
                      </h2>
                      <span className="text-xs text-slate-500">
                        {t('tracks_found', { count: displayedTracks.length })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          if (displayedTracks.length > 0) handlePlayTrack(displayedTracks[0]);
                        }}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500 px-3 py-1.5 text-xs font-bold text-slate-950 hover:bg-sky-400 transition"
                      >
                        <Play className="h-3.5 w-3.5" />
                        <span>{t('btn_play_all')}</span>
                      </button>
                    </div>
                  </div>

                  {displayedTracks.length === 0 ? (
                    <Empty>{t('empty_library')}</Empty>
                  ) : (
                    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white/50 shadow-sm">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-200 bg-white/80 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                            <th className="px-3 py-2 w-10 text-center">{t('th_index')}</th>
                            <th className="px-3 py-2">{t('th_title')}</th>
                            <th className="px-3 py-2 hidden md:table-cell">{t('th_album')}</th>
                            <th className="px-3 py-2 w-20 text-right">{t('th_duration')}</th>
                            <th className="px-3 py-2 w-16 text-center">{t('th_actions')}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200/60">
                          {displayedTracks.map((track, idx) => {
                            const isCurrent = currentTrack?.id === track.id;
                            const isSelected = selectedTrack?.id === track.id;
                            return (
                              <tr
                                key={track.id}
                                onClick={() => setSelectedTrack(track)}
                                onDoubleClick={() => handlePlayTrack(track)}
                                className={`group cursor-pointer transition ${
                                  isCurrent
                                    ? 'bg-sky-500/10 text-sky-700 font-semibold'
                                    : isSelected
                                    ? 'bg-slate-100/60'
                                    : 'hover:bg-slate-100'
                                }`}
                              >
                                <td className="px-3 py-2 text-center text-slate-500">
                                  {isCurrent && isPlaying ? (
                                    <div className="flex items-center justify-center gap-0.5">
                                      <span className="nexus-eq-bar !h-3" />
                                      <span className="nexus-eq-bar !h-4" />
                                      <span className="nexus-eq-bar !h-2" />
                                    </div>
                                  ) : (
                                    <span className="group-hover:hidden">{idx + 1}</span>
                                  )}
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handlePlayTrack(track);
                                    }}
                                    className="hidden group-hover:inline-flex text-sky-600"
                                  >
                                    <Play className="h-3.5 w-3.5" />
                                  </button>
                                </td>
                                <td className="px-3 py-2">
                                  <div className="flex items-center gap-2.5 truncate">
                                    <div className="h-8 w-8 shrink-0 overflow-hidden rounded bg-slate-100 flex items-center justify-center">
                                      {track.cover ? (
                                        <img src={getCoverUrl(track.album_key)} alt="" className="h-full w-full object-cover" />
                                      ) : track.is_video ? (
                                        <Film className="h-4 w-4 text-purple-600" />
                                      ) : (
                                        <Music className="h-4 w-4 text-slate-500" />
                                      )}
                                    </div>
                                    <div className="truncate">
                                      <span className="block truncate font-medium text-slate-900">{track.title}</span>
                                      <span className="block truncate text-[11px] text-slate-500">{track.artist}</span>
                                    </div>
                                  </div>
                                </td>
                                <td className="px-3 py-2 text-slate-500 hidden md:table-cell truncate">
                                  {track.album || '—'}
                                </td>
                                <td className="px-3 py-2 text-right font-mono text-slate-500">
                                  {formatDuration(track.duration)}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      void handleToggleLike(track);
                                    }}
                                    className={`p-1 transition ${
                                      track.liked ? 'text-rose-500' : 'text-slate-500 hover:text-slate-600'
                                    }`}
                                  >
                                    <Heart className="h-3.5 w-3.5 fill-current" />
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: PLAYLISTS GRID */}
              {!loading && activeTab === 'playlists' && !selectedPlaylist && (
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-bold text-slate-900">{t('tab_playlists')}</h2>
                    <button
                      type="button"
                      onClick={() => setNewPlaylistOpen(true)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500 px-3 py-1.5 text-xs font-bold text-slate-950 hover:bg-sky-400 transition"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>{t('new_playlist')}</span>
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                    {playlists.map((pl) => (
                      <div
                        key={pl.id}
                        onClick={() => {
                          setSelectedPlaylist(pl);
                          void fetchPlaylistDetails(pl.id).then(setSelectedPlaylist);
                        }}
                        className="group flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/60 p-4 hover:border-purple-500 cursor-pointer transition"
                      >
                        <div className="aspect-square w-full rounded-lg bg-gradient-to-br from-purple-900/50 to-slate-100 flex items-center justify-center">
                          <ListMusic className="h-12 w-12 text-purple-600 group-hover:scale-110 transition" />
                        </div>
                        <span className="truncate text-sm font-bold text-slate-900">{pl.name}</span>
                        <span className="text-xs text-slate-500">{t('tracks_count', { count: pl.count })}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 4: KARAOKE & VIDEO */}
              {!loading && activeTab === 'karaoke' && (
                <div className="flex h-full flex-col lg:flex-row gap-6">
                  {/* Left: Video / Visualizer Player */}
                  <div className="flex-1 flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white/80 p-6 overflow-hidden">
                    {currentTrack?.is_video || currentTrack?.path?.match(/\.(mp4|webm|mkv)$/i) ? (
                      <div className="w-full aspect-video rounded-xl overflow-hidden bg-black flex items-center justify-center shadow-2xl">
                        <video
                          ref={videoRef}
                          controls
                          onTimeUpdate={onTimeUpdate}
                          onLoadedMetadata={onLoadedMetadata}
                          onEnded={onEnded}
                          className="h-full w-full object-contain"
                        />
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center gap-4 text-center my-auto">
                        <div className="relative h-44 w-44 rounded-2xl overflow-hidden border border-sky-500/30 bg-slate-100 shadow-2xl flex items-center justify-center">
                          {currentTrack?.cover ? (
                            <img
                              src={getCoverUrl(currentTrack.album_key)}
                              alt=""
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <Disc className="h-20 w-20 text-sky-600 animate-spin" style={{ animationDuration: '8s' }} />
                          )}
                        </div>
                        <div>
                          <h3 className="text-lg font-black text-slate-900">{currentTrack?.title || t('select_track_prompt')}</h3>
                          <p className="text-sm text-slate-500">{currentTrack?.artist || 'Nexus Media Player'}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right: Synchronized Karaoke Lyrics */}
                  <div className="w-full lg:w-96 flex flex-col rounded-2xl border border-slate-200 bg-white/60 p-4">
                    <header className="border-b border-slate-200 pb-3 mb-3">
                      <div className="flex items-center gap-2">
                        <Mic2 className="h-4 w-4 text-amber-600" />
                        <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{t('karaoke_title')}</h4>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">{t('karaoke_hint')}</p>
                    </header>

                    <div
                      ref={lyricsContainerRef}
                      className="flex-1 overflow-y-auto flex flex-col gap-2 p-2 text-center text-sm"
                    >
                      {lyricsData.synced && lyricsData.synced.length > 0 ? (
                        lyricsData.synced.map((line, idx) => (
                          <div
                            key={`${line.time}-${idx}`}
                            className={`nexus-karaoke-line ${
                              idx === activeLyricIndex ? 'nexus-karaoke-active' : ''
                            }`}
                          >
                            {line.text}
                          </div>
                        ))
                      ) : lyricsData.plain ? (
                        <pre className="whitespace-pre-wrap font-sans text-xs text-slate-600 leading-relaxed">
                          {lyricsData.plain}
                        </pre>
                      ) : (
                        <div className="my-auto text-xs text-slate-500">
                          {currentTrack ? t('lyrics_empty') : t('karaoke_start_prompt')}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 5: UPLOAD / DRAG & DROP */}
              {!loading && activeTab === 'upload' && (
                <div className="flex flex-col items-center justify-center gap-6 rounded-2xl border border-slate-200 bg-white/50 p-8 text-center max-w-xl mx-auto my-auto">
                  <div className="rounded-2xl bg-sky-500/10 p-5 text-sky-600">
                    <UploadCloud className="h-12 w-12" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">{t('upload_title')}</h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-md">{t('drop_hint')}</p>
                  </div>

                  <button
                    type="button"
                    onClick={openUploadPicker}
                    className="rounded-lg bg-sky-500 px-5 py-2.5 text-xs font-bold text-slate-950 hover:bg-sky-400 transition"
                  >
                    {t('browse_files')}
                  </button>

                  {uploadStatus && (
                    <div className="w-full rounded-xl border border-sky-500/30 bg-sky-500/10 p-3 text-xs text-sky-800">
                      <span>{uploadStatus}</span>
                      {uploadProgress !== null && (
                        <div className="mt-2 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className="h-full bg-sky-400 transition-all duration-300"
                            style={{ width: `${uploadProgress}%` }}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 6: SETTINGS */}
              {!loading && activeTab === 'settings' && (
                <div className="flex flex-col gap-6 max-w-3xl pb-10">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                    <div>
                      <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                        <Sliders className="h-5 w-5 text-cyan-600" />
                        <span>{t('settings_title')}</span>
                      </h2>
                    </div>
                    <div className="flex items-center gap-3">
                      {settingsFeedback && (
                        <span className="text-xs font-semibold text-emerald-600 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 rounded-lg">
                          {settingsFeedback}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => void handleSaveSettings()}
                        disabled={settingsSaving}
                        className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition shadow"
                      >
                        <Save className="h-4 w-4" />
                        <span>{settingsSaving ? t('settings_saving') : t('settings_save_btn')}</span>
                      </button>
                    </div>
                  </div>

                  {settingsLoading ? (
                    <Loading label={t('loading')} />
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      {/* Section 1: Scanner della Libreria */}
                      <div className="rounded-xl border border-slate-200 bg-white/60 p-4 flex flex-col gap-4">
                        <div className="flex items-center gap-2 text-cyan-600 font-bold text-xs uppercase tracking-wider border-b border-slate-200/80 pb-2">
                          <Disc className="h-4 w-4" />
                          <span>{t('settings_scanner_title')}</span>
                        </div>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_SCANNER_ENABLED !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_SCANNER_ENABLED: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-cyan-500 focus:ring-cyan-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_scanner_enable')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_scanner_enable_desc')}
                            </span>
                          </div>
                        </label>

                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                            {t('settings_scan_interval')}
                          </label>
                          <select
                            value={musicSettings.NUXIVA_MUSIC_SCAN_MIN || '15'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_SCAN_MIN: e.target.value,
                              }))
                            }
                            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                          >
                            <option value="5">{t('settings_scan_5min')}</option>
                            <option value="15">{t('settings_scan_15min')}</option>
                            <option value="60">{t('settings_scan_1hour')}</option>
                            <option value="360">{t('settings_scan_6hours')}</option>
                          </select>
                        </div>

                        <div className="pt-2 border-t border-slate-200/60">
                          <button
                            type="button"
                            onClick={() => void handleTriggerScan()}
                            disabled={scanTriggered}
                            className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-200 transition"
                          >
                            <RefreshCw className={`h-3.5 w-3.5 ${scanTriggered ? 'animate-spin text-cyan-600' : ''}`} />
                            <span>{t('settings_scan_now')}</span>
                          </button>
                        </div>
                      </div>

                      {/* Section 2: Riconoscimento Musicale & Acustico */}
                      <div className="rounded-xl border border-slate-200 bg-white/60 p-4 flex flex-col gap-4">
                        <div className="flex items-center gap-2 text-amber-600 font-bold text-xs uppercase tracking-wider border-b border-slate-200/80 pb-2">
                          <Mic2 className="h-4 w-4" />
                          <span>{t('settings_recognition_title')}</span>
                        </div>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_RECOGNITION !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_RECOGNITION: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-amber-500 focus:ring-amber-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_recognition_enable')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_recognition_desc')}
                            </span>
                          </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_IDENTIFY !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_IDENTIFY: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-amber-500 focus:ring-amber-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_ambient_identify')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_ambient_identify_desc')}
                            </span>
                          </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_VOICE !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_VOICE: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-amber-500 focus:ring-amber-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_voice_commands')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_voice_commands_desc')}
                            </span>
                          </div>
                        </label>
                      </div>

                      {/* Section 3: Metadati e Testi Online */}
                      <div className="rounded-xl border border-slate-200 bg-white/60 p-4 flex flex-col gap-4">
                        <div className="flex items-center gap-2 text-purple-600 font-bold text-xs uppercase tracking-wider border-b border-slate-200/80 pb-2">
                          <Sparkles className="h-4 w-4" />
                          <span>{t('settings_metadata_title')}</span>
                        </div>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_COVERS !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_COVERS: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-purple-500 focus:ring-purple-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_covers_online')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_covers_online_desc')}
                            </span>
                          </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_LYRICS !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_LYRICS: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-purple-500 focus:ring-purple-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_lyrics_online')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_lyrics_online_desc')}
                            </span>
                          </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_ORGANIZE !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_ORGANIZE: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-purple-500 focus:ring-purple-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_auto_organize')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_auto_organize_desc')}
                            </span>
                          </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_TAGS !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_TAGS: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-purple-500 focus:ring-purple-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_write_tags')}
                            </span>
                            <span className="block text-[11px] text-slate-500 leading-relaxed">
                              {t('settings_write_tags_desc')}
                            </span>
                          </div>
                        </label>
                      </div>

                      {/* Section 4: Riproduzione & Streaming */}
                      <div className="rounded-xl border border-slate-200 bg-white/60 p-4 flex flex-col gap-4">
                        <div className="flex items-center gap-2 text-emerald-600 font-bold text-xs uppercase tracking-wider border-b border-slate-200/80 pb-2">
                          <Volume2 className="h-4 w-4" />
                          <span>{t('settings_playback_title')}</span>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                            {t('settings_transcode')}
                          </label>
                          <select
                            value={musicSettings.NUXIVA_MUSIC_TRANSCODE || 'auto'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_TRANSCODE: e.target.value,
                              }))
                            }
                            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                          >
                            <option value="auto">{t('settings_transcode_auto')}</option>
                            <option value="never">{t('settings_transcode_never')}</option>
                            <option value="always">{t('settings_transcode_always')}</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                            {t('settings_bitrate')}
                          </label>
                          <select
                            value={musicSettings.NUXIVA_MUSIC_TRANSCODE_KBPS || '192'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_TRANSCODE_KBPS: e.target.value,
                              }))
                            }
                            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                          >
                            <option value="128">128 kbps</option>
                            <option value="192">192 kbps</option>
                            <option value="256">256 kbps</option>
                            <option value="320">320 kbps</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                            {t('settings_crossfade')}
                          </label>
                          <select
                            value={musicSettings.NUXIVA_MUSIC_CROSSFADE || '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_CROSSFADE: e.target.value,
                              }))
                            }
                            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none"
                          >
                            <option value="0">{t('settings_crossfade_none')}</option>
                            <option value="3">{t('settings_crossfade_3s')}</option>
                            <option value="6">{t('settings_crossfade_6s')}</option>
                            <option value="10">{t('settings_crossfade_10s')}</option>
                          </select>
                        </div>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_RADIO !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_RADIO: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-emerald-500 focus:ring-emerald-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_radio')}
                            </span>
                          </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={musicSettings.NUXIVA_MUSIC_CAST !== '0'}
                            onChange={(e) =>
                              setMusicSettings((prev) => ({
                                ...prev,
                                NUXIVA_MUSIC_CAST: e.target.checked ? '1' : '0',
                              }))
                            }
                            className="mt-0.5 rounded border-slate-300 bg-slate-50 text-emerald-500 focus:ring-emerald-500"
                          />
                          <div>
                            <span className="block text-xs font-bold text-slate-900">
                              {t('settings_cast')}
                            </span>
                          </div>
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Persistent Player Bottom Bar */}
            <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white px-4 py-2.5">
              {/* Left: Track Info */}
              <div className="flex items-center gap-3 min-w-0 w-60">
                <div className="h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-slate-100 flex items-center justify-center">
                  {currentTrack?.cover ? (
                    <img src={getCoverUrl(currentTrack.album_key)} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <Music className="h-5 w-5 text-slate-500" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-bold text-slate-900">
                    {currentTrack ? currentTrack.title : t('no_track_selected')}
                  </span>
                  <span className="block truncate text-[11px] text-slate-500">
                    {currentTrack ? currentTrack.artist : t('select_from_library')}
                  </span>
                </div>
                {currentTrack && (
                  <button
                    type="button"
                    onClick={() => void handleToggleLike(currentTrack)}
                    className={`p-1 transition ${
                      currentTrack.liked ? 'text-rose-500' : 'text-slate-500 hover:text-slate-600'
                    }`}
                  >
                    <Heart className="h-4 w-4 fill-current" />
                  </button>
                )}
              </div>

              {/* Center: Controls & Time Slider */}
              <div className="flex flex-col items-center gap-1 flex-1 max-w-md">
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={() => setIsShuffle((v) => !v)}
                    title={t('shuffle')}
                    className={`p-1 transition ${isShuffle ? 'text-sky-600' : 'text-slate-500 hover:text-slate-900'}`}
                  >
                    <Shuffle className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={handlePrev}
                    title={t('prev')}
                    className="p-1 text-slate-600 hover:text-slate-900 transition"
                  >
                    <SkipBack className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={togglePlayPause}
                    title={isPlaying ? t('pause') : t('play')}
                    className="rounded-full bg-white p-2 text-slate-950 hover:scale-105 transition"
                  >
                    {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={handleNext}
                    title={t('next')}
                    className="p-1 text-slate-600 hover:text-slate-900 transition"
                  >
                    <SkipForward className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsRepeat((v) => !v)}
                    title={t('repeat')}
                    className={`p-1 transition ${isRepeat ? 'text-sky-600' : 'text-slate-500 hover:text-slate-900'}`}
                  >
                    <Repeat className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Progress bar */}
                <div className="flex items-center gap-2 w-full text-[10px] font-mono text-slate-500">
                  <span>{formatDuration(currentTime)}</span>
                  <input
                    type="range"
                    min={0}
                    max={duration || 100}
                    value={currentTime}
                    onChange={(e) => {
                      const newTime = Number(e.target.value);
                      setCurrentTime(newTime);
                      const el = currentTrack?.is_video ? videoRef.current : audioRef.current;
                      if (el) el.currentTime = newTime;
                    }}
                    className="h-1 flex-1 cursor-pointer accent-sky-400 rounded-lg bg-slate-100"
                  />
                  <span>{formatDuration(duration)}</span>
                </div>
              </div>

              {/* Right: Volume & Quick Modes */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setActiveTab('karaoke')}
                  title={t('open_karaoke')}
                  className={`rounded-lg p-1.5 transition ${
                    activeTab === 'karaoke' ? 'bg-amber-500/20 text-amber-600' : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Mic2 className="h-4 w-4" />
                </button>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      const nextMute = !isMuted;
                      setIsMuted(nextMute);
                      const el = currentTrack?.is_video ? videoRef.current : audioRef.current;
                      if (el) el.muted = nextMute;
                    }}
                    className="text-slate-500 hover:text-slate-900"
                  >
                    {isMuted || volume === 0 ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                  </button>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={isMuted ? 0 : volume}
                    onChange={(e) => {
                      const newVol = Number(e.target.value);
                      setVolume(newVol);
                      setIsMuted(false);
                      const el = currentTrack?.is_video ? videoRef.current : audioRef.current;
                      if (el) {
                        el.volume = newVol;
                        el.muted = false;
                      }
                    }}
                    className="h-1 w-18 cursor-pointer accent-sky-400 rounded-lg bg-slate-100"
                  />

                  <button
                    type="button"
                    onClick={() => setCastModalOpen(true)}
                    className="ml-1 rounded-lg p-1.5 text-slate-500 hover:text-sky-700 hover:bg-slate-100 transition"
                    title="Trasmetti Musica (Google Home, Nest Hub, Sonos, Bose, Smart TV)"
                  >
                    <Cast className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </footer>

            {/* Modal: Create Playlist */}
            {newPlaylistOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-2xs">
                <form
                  onSubmit={handleCreatePlaylist}
                  className="flex flex-col gap-4 rounded-2xl border border-slate-300 bg-white p-6 max-w-sm w-full shadow-2xl"
                >
                  <h3 className="text-sm font-bold text-slate-900">{t('new_playlist')}</h3>
                  <input
                    type="text"
                    autoFocus
                    placeholder={t('playlist_name')}
                    value={playlistName}
                    onChange={(e) => setPlaylistName(e.target.value)}
                    className="rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-xs text-slate-900 placeholder-slate-500 focus:border-sky-400 focus:outline-none"
                  />
                  <input
                    type="text"
                    placeholder={t('playlist_desc')}
                    value={playlistDesc}
                    onChange={(e) => setPlaylistDesc(e.target.value)}
                    className="rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-xs text-slate-900 placeholder-slate-500 focus:border-sky-400 focus:outline-none"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setNewPlaylistOpen(false)}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-500 hover:text-slate-900"
                    >
                      {t('cancel')}
                    </button>
                    <button
                      type="submit"
                      disabled={!playlistName.trim()}
                      className="rounded-lg bg-sky-500 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-sky-400 disabled:opacity-50"
                    >
                      {t('create')}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        }
        inspector={
          <OSInspector
            title={t('details')}
            subtitle={selectedTrack ? selectedTrack.title : t('no_track_selected')}
            onClose={() => setSelectedTrack(null)}
          >
            {selectedTrack ? (
              <div className="flex flex-col gap-4 text-xs">
                <div className="aspect-square w-full rounded-xl overflow-hidden bg-slate-100 flex items-center justify-center border border-slate-300 shadow-sm">
                  {selectedTrack.cover ? (
                    <img src={getCoverUrl(selectedTrack.album_key)} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <Music className="h-16 w-16 text-slate-500" />
                  )}
                </div>

                <div>
                  <h4 className="font-bold text-slate-900 text-sm">{selectedTrack.title}</h4>
                  <p className="text-slate-500">{selectedTrack.artist}</p>
                </div>

                <div className="flex flex-col gap-2 rounded-lg border border-slate-200/80 bg-slate-50 p-3">
                  <div>
                    <span className="block text-[10px] font-bold uppercase text-slate-500">{t('th_album')}</span>
                    <span className="text-slate-700 font-medium">{selectedTrack.album || '—'}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold uppercase text-slate-500">{t('genre_and_year')}</span>
                    <span className="text-slate-700">{selectedTrack.genre || t('generic_genre')} · {selectedTrack.year || '—'}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold uppercase text-slate-500">{t('duration_and_bitrate')}</span>
                    <span className="font-mono text-slate-700">{formatDuration(selectedTrack.duration)} · {selectedTrack.bitrate ? `${selectedTrack.bitrate} kbps` : 'Audio'}</span>
                  </div>
                  {selectedTrack.path && (
                    <div>
                      <span className="block text-[10px] font-bold uppercase text-slate-500">{t('smb_path')}</span>
                      <div className="flex items-center justify-between gap-1 mt-0.5">
                        <span className="font-mono text-[10px] text-slate-600 truncate">{selectedTrack.path}</span>
                        <button
                          type="button"
                          onClick={async () => {
                            await navigator.clipboard.writeText(selectedTrack.path || '');
                            setCopiedUnc(true);
                            setTimeout(() => setCopiedUnc(false), 2000);
                          }}
                          className="p-1 text-slate-500 hover:text-slate-700"
                          title={t('copy_path')}
                        >
                          {copiedUnc ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-2">
                  <button
                    type="button"
                    onClick={() => handlePlayTrack(selectedTrack)}
                    className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-sky-500 px-3 py-2 text-xs font-bold text-slate-950 hover:bg-sky-400 transition"
                  >
                    <Play className="h-3.5 w-3.5" />
                    <span>{t('play_immediately')}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      handlePlayTrack(selectedTrack);
                      setActiveTab('karaoke');
                    }}
                    className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    <Mic2 className="h-3.5 w-3.5 text-amber-500" />
                    <span>{t('open_karaoke_sing_along')}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-slate-500">
                <Disc className="h-10 w-10 text-slate-600" />
                <p className="text-xs">{t('inspector_empty_desc')}</p>
              </div>
            )}
          </OSInspector>
        }
        isInspectorOpen={true}
      />

      <CastModal
        isOpen={castModalOpen}
        onClose={() => setCastModalOpen(false)}
        trackId={currentTrack?.id}
        trackTitle={currentTrack?.title}
        trackArtist={currentTrack?.artist}
        t={t}
      />
    </div>
  );
};

export default View;
