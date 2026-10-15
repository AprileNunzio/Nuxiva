import React, { useState, useEffect } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Camera,
  Shield,
  ShieldOff,
  Video,
  Scan,
  Hand,
  Users,
  CameraOff,
  Save,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

interface CameraDevice {
  id: string;
  name: string;
  resolution: string;
  fps: number;
  status: string;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/camera');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [cameras, setCameras] = useState<CameraDevice[]>([
    { id: '/dev/video0', name: 'Sony IMX708 Wide 4K Ultra-HD', resolution: '3840x2160', fps: 30, status: 'active' },
    { id: '/dev/video2', name: 'Logitech C920 HD Pro (USB)', resolution: '1920x1080', fps: 60, status: 'standby' },
    { id: 'rtsp://camera', name: 'ESP32-CAM Satellite RTSP Stream', resolution: '1280x720', fps: 25, status: 'streaming' },
  ]);
  const [selectedCam, setSelectedCam] = useState('/dev/video0');

  // Privacy Shutter
  const [privacyShutter, setPrivacyShutter] = useState(false);

  // Resolution & Profile
  const [resolution, setResolution] = useState('1920x1080');
  const [fps, setFps] = useState(30);

  // Vision AI
  const [faceId, setFaceId] = useState(true);
  const [handGestures, setHandGestures] = useState(true);
  const [presenceDetection, setPresenceDetection] = useState(true);

  // Snapshot
  const [snapshotTaken, setSnapshotTaken] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchHardware = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/v5/nodes/${nodeId}/hardware`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted && Array.isArray(data.cameras) && data.cameras.length > 0) {
            setCameras(data.cameras);
            setSelectedCam(data.cameras[0].id);
          }
        }
      } catch (err) {
        console.warn('Hardware fetch failed', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchHardware();
    return () => {
      isMounted = false;
    };
  }, [nodeId]);

  const handleTakeSnapshot = () => {
    setSnapshotTaken(true);
    setTimeout(() => setSnapshotTaken(false), 2500);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`/api/v5/nodes/${nodeId}/apps/camera/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: !privacyShutter,
          settings: {
            selectedCam,
            privacyShutter,
            resolution,
            fps,
            faceId,
            handGestures,
            presenceDetection,
          },
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center text-slate-400 font-mono gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span className="text-xs">Rilevamento sensori video telecamera...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-wide">{t('title')}</h2>
            <p className="text-xs text-slate-400 mt-0.5">{t('description')}</p>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-cyan-500/20 transition cursor-pointer"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? t('saving') : t('save')}
        </button>
      </div>

      {saved && (
        <div className="bg-emerald-950/60 border border-emerald-500/40 p-3.5 rounded-xl flex items-center gap-3 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{t('saved')}</span>
        </div>
      )}

      {/* Privacy Shutter Banner */}
      <div
        className={`p-4 rounded-2xl border transition flex items-center justify-between ${
          privacyShutter
            ? 'bg-rose-950/30 border-rose-500/50 shadow-[0_0_20px_rgba(244,63,94,0.15)]'
            : 'bg-slate-900/60 border-slate-800'
        }`}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${privacyShutter ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800 text-slate-400'}`}>
            {privacyShutter ? <ShieldOff className="w-5 h-5" /> : <Shield className="w-5 h-5 text-emerald-400" />}
          </div>
          <div>
            <div className="text-xs font-bold text-white flex items-center gap-2">
              {t('privacy_shutter')}
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                privacyShutter
                  ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                  : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
              }`}>
                {privacyShutter ? t('privacy_active') : t('privacy_inactive')}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">{t('privacy_shutter_desc')}</p>
          </div>
        </div>

        <button
          onClick={() => setPrivacyShutter(!privacyShutter)}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${
            privacyShutter
              ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/30'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
          }`}
        >
          {privacyShutter ? 'DISATTIVA OTTURATORE' : 'ATTIVA PRIVACY'}
        </button>
      </div>

      {/* Camera Selection & Resolution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Video className="w-4 h-4 text-cyan-400" />
            {t('select_camera')}
          </div>

          <div className="space-y-2">
            {cameras.map((cam) => (
              <div
                key={cam.id}
                onClick={() => setSelectedCam(cam.id)}
                className={`p-3.5 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                  selectedCam === cam.id
                    ? 'bg-cyan-950/30 border-cyan-500/60 ring-1 ring-cyan-500/40'
                    : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="text-xs font-bold text-white">{cam.name}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    ID: {cam.id} · Max: {cam.resolution} @ {cam.fps}fps
                  </div>
                </div>
                {selectedCam === cam.id && <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#06b6d4]" />}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Scan className="w-4 h-4 text-cyan-400" />
            {t('stream_profile')}
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Risoluzione Sensore</label>
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="3840x2160">4K Ultra-HD (3840 x 2160)</option>
                <option value="1920x1080">Full-HD 1080p (1920 x 1080)</option>
                <option value="1280x720">HD 720p (1280 x 720)</option>
                <option value="640x480">Standard SD 480p (Satellite Low-Bandwidth)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Framerate Flusso (FPS)</label>
              <select
                value={fps}
                onChange={(e) => setFps(parseInt(e.target.value, 10))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="60">60 FPS (Ultra Fluido / Gaming)</option>
                <option value="30">30 FPS (Standard Broadcast)</option>
                <option value="15">15 FPS (Basso Consumo Energetico)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Edge Vision AI Pipelines */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Scan className="w-4 h-4 text-purple-400" />
          {t('vision_ai_title')}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            onClick={() => setFaceId(!faceId)}
            className={`p-4 rounded-xl border cursor-pointer transition ${
              faceId ? 'bg-purple-950/20 border-purple-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-purple-400" />
                {t('ai_face_id')}
              </span>
              <span className={`text-[10px] font-bold ${faceId ? 'text-purple-400' : 'text-slate-500'}`}>
                {faceId ? 'ATTIVO' : 'OFF'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">{t('ai_face_id_desc')}</p>
          </div>

          <div
            onClick={() => setHandGestures(!handGestures)}
            className={`p-4 rounded-xl border cursor-pointer transition ${
              handGestures ? 'bg-cyan-950/20 border-cyan-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Hand className="w-3.5 h-3.5 text-cyan-400" />
                {t('ai_hands')}
              </span>
              <span className={`text-[10px] font-bold ${handGestures ? 'text-cyan-400' : 'text-slate-500'}`}>
                {handGestures ? 'ATTIVO' : 'OFF'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">{t('ai_hands_desc')}</p>
          </div>

          <div
            onClick={() => setPresenceDetection(!presenceDetection)}
            className={`p-4 rounded-xl border cursor-pointer transition ${
              presenceDetection ? 'bg-emerald-950/20 border-emerald-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-emerald-400" />
                {t('ai_presence')}
              </span>
              <span className={`text-[10px] font-bold ${presenceDetection ? 'text-emerald-400' : 'text-slate-500'}`}>
                {presenceDetection ? 'ATTIVO' : 'OFF'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">{t('ai_presence_desc')}</p>
          </div>
        </div>
      </div>

      {/* Live Viewfinder Cockpit */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="bg-slate-900/90 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Camera className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-200">{t('viewfinder_title')}</span>
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-slate-400">{t('status_res')}: <strong className="text-white">{resolution}</strong></span>
            <span className="text-slate-400">{t('status_fps')}: <strong className="text-emerald-400">{fps} FPS</strong></span>
            <button
              onClick={handleTakeSnapshot}
              disabled={privacyShutter}
              className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-40"
            >
              {snapshotTaken ? t('snapshot_taken') : t('snapshot_btn')}
            </button>
          </div>
        </div>

        <div className="relative aspect-video max-h-[380px] w-full bg-[#030712] flex items-center justify-center overflow-hidden">
          {privacyShutter ? (
            <div className="flex flex-col items-center gap-2 text-rose-400">
              <CameraOff className="w-12 h-12" />
              <span className="text-xs font-bold tracking-widest uppercase">Flusso Video Oscurato — Modalità Privacy Attiva</span>
            </div>
          ) : (
            <div className="relative w-full h-full flex items-center justify-center">
              {/* Animated HUD Grid */}
              <div className="absolute inset-0 bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:24px_24px] opacity-20" />
              
              {/* Corner brackets */}
              <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-cyan-400/80" />
              <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-cyan-400/80" />
              <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-cyan-400/80" />
              <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-cyan-400/80" />

              {/* Crosshair */}
              <div className="absolute w-12 h-12 border border-cyan-500/40 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              </div>

              {/* Simulated Face Detection Box if faceId is ON */}
              {faceId && (
                <div className="absolute top-1/4 left-1/3 w-32 h-40 border-2 border-purple-400/80 rounded-lg shadow-[0_0_15px_rgba(168,85,247,0.3)] flex flex-col justify-between p-1.5">
                  <span className="text-[9px] font-bold bg-purple-950/80 text-purple-300 px-1 rounded w-fit">
                    FaceID: Persona Riconosciuta
                  </span>
                  <span className="text-[9px] text-purple-300 text-right">98.4%</span>
                </div>
              )}

              {/* Live Status Overlay */}
              <div className="absolute bottom-3 left-4 text-[10px] text-slate-400 flex items-center gap-3 bg-slate-900/80 px-2.5 py-1 rounded-md border border-slate-800">
                <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> REC LIVE
                </span>
                <span>Node: {nodeId}</span>
                <span>Bitrate: 4.2 Mbps</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default View;
