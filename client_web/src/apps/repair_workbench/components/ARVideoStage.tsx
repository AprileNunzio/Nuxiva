import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, CheckCircle2, Cpu, Edit3, RefreshCw, VideoOff, Zap } from 'lucide-react';
import { adminPath } from '../../../shared/http/basePath';
import { reportError } from '../../../shared/errors/errorBus';
import type { ARComponentPopup, CameraSourceItem } from '../types';
import { containRect } from '../videoGeometry';

interface ARVideoStageProps {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly cameras: readonly CameraSourceItem[];
  readonly selectedCameraId: string;
  readonly cameraName: string;
  readonly sceneState: string;
  readonly popups: readonly ARComponentPopup[];
  readonly sessionActive: boolean;
  readonly busy: boolean;
  readonly onSelectCamera: (id: string, name: string) => void;
  readonly onFrameCaptured: (frameBase64: string, grid: number[]) => void;
  readonly onTeachComponent: (trackId: number, label: string, value: string) => Promise<void>;
}

const HEALTH_TONE: Record<string, string> = {
  ok: 'border-emerald-400/80 bg-emerald-950/80 text-emerald-200',
  suspect: 'border-amber-400/80 bg-amber-950/85 text-amber-200',
  fault: 'border-rose-500/90 bg-rose-950/90 text-rose-200',
  unknown: 'border-cyan-400/75 bg-slate-950/85 text-cyan-200',
};

export const ARVideoStage: React.FC<ARVideoStageProps> = ({
  t,
  cameras,
  selectedCameraId,
  cameraName,
  sceneState,
  popups,
  sessionActive,
  busy,
  onSelectCamera,
  onFrameCaptured,
  onTeachComponent,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [sourceSize, setSourceSize] = useState({ width: 0, height: 0 });
  const [stageSize, setStageSize] = useState({ width: 0, height: 0 });
  const [streamReady, setStreamReady] = useState<boolean>(false);
  const [autoAnalyze, setAutoAnalyze] = useState<boolean>(true);
  const [stamp, setStamp] = useState<number>(() => Date.now());
  const [editingTrack, setEditingTrack] = useState<number | null>(null);
  const [teachLabel, setTeachLabel] = useState<string>('');
  const [teachValue, setTeachValue] = useState<string>('');

  const isLocalUsb = selectedCameraId === 'local_usb' || selectedCameraId.startsWith('usb:');
  const videoRect = containRect(stageSize.width, stageSize.height, sourceSize.width, sourceSize.height);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setStageSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setStreamReady(false);
    if (!isLocalUsb) {
      const timer = window.setInterval(() => {
        if (!document.hidden) setStamp(Date.now());
      }, 2000);
      return () => window.clearInterval(timer);
    }
    let activeStream: MediaStream | null = null;
    let cancelled = false;
    const openUsb = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setStreamReady(false);
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1920 }, height: { ideal: 1080 },
            ...(selectedCameraId.startsWith('usb:') ? { deviceId: { exact: selectedCameraId.slice(4) } } : {}) },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((tr) => tr.stop());
          return;
        }
        activeStream = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setStreamReady(true);
        }
      } catch (cause: unknown) {
        setStreamReady(false);
        reportError('repair_workbench_webcam_access', cause);
      }
    };
    void openUsb();
    return () => {
      cancelled = true;
      if (activeStream) {
        activeStream.getTracks().forEach((tr) => tr.stop());
      }
    };
  }, [isLocalUsb, selectedCameraId]);

  const captureAndSend = useCallback(() => {
    if (!sessionActive || editingTrack !== null || document.hidden) return;
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = sourceSize.width > 0 ? Math.max(1, Math.round(640 * sourceSize.height / sourceSize.width)) : 360;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (isLocalUsb && videoRef.current && videoRef.current.readyState >= 2) {
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    } else if (!isLocalUsb && imgRef.current && imgRef.current.complete && imgRef.current.naturalWidth > 0) {
      ctx.drawImage(imgRef.current, 0, 0, canvas.width, canvas.height);
    } else {
      return;
    }

    const gridCanvas = document.createElement('canvas');
    gridCanvas.width = 8;
    gridCanvas.height = 8;
    const gctx = gridCanvas.getContext('2d');
    const grid: number[] = [];
    if (gctx) {
      gctx.drawImage(canvas, 0, 0, 8, 8);
      const pixels = gctx.getImageData(0, 0, 8, 8).data;
      for (let i = 0; i < pixels.length; i += 4) {
        const lum = Math.round((pixels[i] * 77 + pixels[i + 1] * 150 + pixels[i + 2] * 29) >> 8);
        grid.push(Math.min(255, Math.max(0, lum)));
      }
    }
    const dataUrl = canvas.toDataURL('image/jpeg', 0.82);
    onFrameCaptured(dataUrl, grid);
  }, [sessionActive, editingTrack, isLocalUsb, sourceSize, onFrameCaptured]);

  useEffect(() => {
    if (!sessionActive || !autoAnalyze || editingTrack !== null) return;
    const timer = window.setInterval(() => captureAndSend(), 3200);
    return () => window.clearInterval(timer);
  }, [sessionActive, autoAnalyze, editingTrack, captureAndSend]);

  const openTeachModal = (popup: ARComponentPopup) => {
    setEditingTrack(popup.track_id);
    setTeachLabel(popup.label);
    setTeachValue(popup.value);
  };

  const submitTeach = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingTrack === null || !teachLabel.trim()) return;
    await onTeachComponent(editingTrack, teachLabel.trim(), teachValue.trim());
    setEditingTrack(null);
  };

  const sceneLabelKey =
    sceneState === 'stable_board'
      ? 'scene_stable_board'
      : sceneState === 'operator_working'
        ? 'scene_operator_working'
        : 'scene_warmup';

  return (
    <section className="relative flex h-full w-full flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <header className="z-20 flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 bg-slate-900/90 px-3 py-2 text-xs backdrop-blur">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/15 px-2.5 py-1 font-semibold text-cyan-300">
            <Camera className="h-3.5 w-3.5" aria-hidden="true" />
            {cameraName}
          </span>
          <select
            aria-label={t('camera_select')}
            value={selectedCameraId}
            onChange={(e) => {
              const id = e.target.value;
              const found = cameras.find((c) => c.id === id);
              onSelectCamera(id, found ? found.name : t('camera_default_bench'));
            }}
            className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
          >
            <option value="local_usb">{t('camera_local_usb')}</option>
            {cameras.map((cam) => (
              <option key={cam.id} value={cam.id}>
                {cam.name}
              </option>
            ))}
          </select>
          <span className="rounded-full border border-slate-700 bg-slate-800/90 px-2.5 py-0.5 text-[11px] text-slate-300">
            {t(sceneLabelKey)}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex cursor-pointer items-center gap-1.5 text-slate-300">
            <input
              type="checkbox"
              checked={autoAnalyze}
              onChange={(e) => setAutoAnalyze(e.target.checked)}
              className="rounded border-slate-600 bg-slate-800"
            />
            {t('auto_analyze')}
          </label>
          <button
            type="button"
            disabled={!sessionActive || busy}
            onClick={captureAndSend}
            className="inline-flex items-center gap-1 rounded-lg border border-cyan-500/40 bg-cyan-500/20 px-2.5 py-1 font-medium text-cyan-200 hover:bg-cyan-500/30 disabled:opacity-40"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            {t('analyze_now')}
          </button>
        </div>
      </header>

      <div ref={stageRef} className="relative min-h-0 flex-1 overflow-hidden bg-black">
        {isLocalUsb ? (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              onLoadedMetadata={(event) => setSourceSize({ width: event.currentTarget.videoWidth, height: event.currentTarget.videoHeight })}
              className={`h-full w-full object-contain ${streamReady ? '' : 'invisible'}`}
            />
          {!streamReady && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-xs text-slate-400">
              <VideoOff className="h-8 w-8 text-slate-600" aria-hidden="true" />
              <span>{t('camera_offline')}</span>
            </div>
          )
          }
          </>
        ) : (
          <img
            ref={imgRef}
            key={stamp}
            src={adminPath(`/api/cameras/live/${encodeURIComponent(selectedCameraId)}.jpg?t=${stamp}`)}
            alt={cameraName}
            crossOrigin="anonymous"
            onLoad={(event) => {
              setStreamReady(true);
              const { naturalWidth: width, naturalHeight: height } = event.currentTarget;
              setSourceSize((previous) => previous.width === width && previous.height === height ? previous : { width, height });
            }}
            onError={() => setStreamReady(false)}
            className="h-full w-full object-contain"
          />
        )}

        <div className="pointer-events-none absolute" style={videoRect}>
          {popups.map((popup) => {
            const [x1, y1, x2, y2] = popup.bbox;
            const left = `${Math.max(0, Math.min(95, x1 * 100))}%`;
            const top = `${Math.max(0, Math.min(95, y1 * 100))}%`;
            const width = `${Math.max(4, Math.min(100, (x2 - x1) * 100))}%`;
            const height = `${Math.max(4, Math.min(100, (y2 - y1) * 100))}%`;
            const tone = HEALTH_TONE[popup.health] || HEALTH_TONE.unknown;
            const voltages = Object.entries(popup.expected_voltages);

            return (
              <div
                key={popup.track_id}
                style={{ left, top, width, height }}
                className={`pointer-events-auto absolute rounded-lg border-2 transition-all duration-150 ${tone}`}
              >
                <div className="absolute -top-7 left-0 z-10 flex items-center gap-1 whitespace-nowrap rounded-md border border-slate-700 bg-slate-950/95 px-2 py-0.5 text-[11px] shadow-lg">
                  <Cpu className="h-3 w-3 text-cyan-400" aria-hidden="true" />
                  <strong className="font-semibold text-white">{popup.key}</strong>
                  {popup.value && <span className="text-cyan-300">{popup.value}</span>}
                  {popup.taught && (
                    <span className="inline-flex items-center gap-0.5 text-emerald-400">
                      <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                      {t('popup_taught_badge')}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => openTeachModal(popup)}
                    title={t('popup_teach')}
                    className="ml-1 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-200 hover:bg-cyan-600 hover:text-white"
                  >
                    <Edit3 className="h-2.5 w-2.5" aria-hidden="true" />
                  </button>
                </div>

                {(popup.notes || voltages.length > 0) && (
                  <div className="absolute left-0 top-full z-10 mt-1 max-w-xs rounded-md border border-slate-700 bg-slate-950/95 p-1.5 text-[10px] text-slate-200 shadow-xl">
                    {popup.notes && <p className="mb-1 text-slate-300">{popup.notes}</p>}
                    {voltages.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1">
                        <Zap className="h-3 w-3 text-amber-400" aria-hidden="true" />
                        <span className="text-slate-400">{t('popup_voltages')}:</span>
                        {voltages.map(([pin, v]) => (
                          <span
                            key={pin}
                            className="rounded bg-slate-800 px-1 py-0.5 font-mono text-amber-300"
                          >
                            P{pin}: {v}V
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {editingTrack !== null && (
          <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
            <form
              onSubmit={submitTeach}
              className="flex w-full max-w-sm flex-col gap-3 rounded-xl border border-slate-700 bg-slate-900 p-4 text-xs text-slate-100 shadow-2xl"
            >
              <h3 className="text-sm font-semibold text-cyan-300">{t('popup_teach_title')}</h3>
              <input
                type="text"
                value={teachLabel}
                maxLength={80}
                onChange={(e) => setTeachLabel(e.target.value)}
                placeholder={t('popup_label_placeholder')}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
                required
              />
              <input
                type="text"
                value={teachValue}
                maxLength={80}
                onChange={(e) => setTeachValue(e.target.value)}
                placeholder={t('popup_value_placeholder')}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingTrack(null)}
                  className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800"
                >
                  {t('popup_cancel')}
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-lg bg-cyan-600 px-3 py-1.5 font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
                >
                  {t('popup_save')}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </section>
  );
};
