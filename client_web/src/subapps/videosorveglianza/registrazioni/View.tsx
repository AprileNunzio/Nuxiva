import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Film, HardDrive, Pin, PinOff, RefreshCw, SkipBack, SkipForward, Trash2 } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { deleteSegment, fetchRecordings, fetchStorage, fetchTimeline, fetchTranscript, jump, seekTo, setPinned } from './api';
import { TranscriptPanel } from './components/TranscriptPanel';
import { SearchPanel } from './components/SearchPanel';
import { Player } from './components/Player';
import { TimelineBar } from './components/TimelineBar';
import { bytes, clock, dayLabel, KIND_GROUPS, ZOOMS } from './format';
import type { RecordingCamera, SegmentRow, StorageStats, Timeline, TranscriptTurn } from './types';

const REFRESH_MS = 30_000;

export function View() {
  const { t, lang } = useScopedI18n('subapps/videosorveglianza/registrazioni');
  const [cameras, setCameras] = useState<RecordingCamera[]>([]);
  const [camera, setCamera] = useState('');
  const [zoom, setZoom] = useState<number>(ZOOMS[0].ms);
  const [windowEnd, setWindowEnd] = useState(() => Date.now());
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [segment, setSegment] = useState<SegmentRow | null>(null);
  const [offsetMs, setOffsetMs] = useState(0);
  const [cursor, setCursor] = useState<number | null>(null);
  const [group, setGroup] = useState('all');
  const [storage, setStorage] = useState<StorageStats | null>(null);
  const [notice, setNotice] = useState('');
  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const fromMs = windowEnd - zoom;
  const kindLabel = (kind: string) => {
    const key = `kind_${kind}`;
    const text = t(key);
    return text === key ? kind : text;
  };

  const loadCameras = useCallback(async () => {
    const rows = await fetchRecordings();
    setCameras(rows);
    setCamera((current) => current || rows[0]?.camera || '');
    setStorage(await fetchStorage());
  }, []);

  useEffect(() => {
    void loadCameras();
    const timer = window.setInterval(() => void loadCameras(), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [loadCameras]);

  useEffect(() => {
    if (!camera) return;
    let alive = true;
    void fetchTimeline(camera, fromMs, windowEnd).then((data) => {
      if (alive) setTimeline(data);
    });
    void fetchTranscript(camera, Math.max(fromMs, windowEnd - 86_400_000), windowEnd).then((rows) => {
      if (alive) setTurns(rows);
    });
    return () => {
      alive = false;
    };
  }, [camera, fromMs, windowEnd]);

  const openAt = useCallback(
    async (atMs: number, target?: string) => {
      const cam = target ?? camera;
      if (!cam) return;
      const found = await seekTo(cam, atMs);
      if (!found) {
        setNotice(t('nothing_here'));
        return;
      }
      setNotice(found.gap_ms > 0 ? t('gap_skipped', { seconds: Math.round(found.gap_ms / 1000) }) : '');
      setSegment(found.segment);
      setOffsetMs(found.offset_ms);
      setCursor(found.segment.start_ms + found.offset_ms);
    },
    [camera, t],
  );

  const onJump = async (direction: 'next' | 'prev') => {
    if (!camera) return;
    const base = cursor ?? (direction === 'next' ? fromMs : windowEnd);
    const hit = await jump(camera, direction === 'next' ? base + 1000 : base - 1000, direction, KIND_GROUPS[group]);
    if (!hit || !hit.seek) {
      setNotice(t(direction === 'next' ? 'no_next_event' : 'no_prev_event'));
      return;
    }
    setNotice(`${clock(hit.marker.at_ms, lang)} · ${hit.marker.label || kindLabel(hit.marker.kind)}`);
    setSegment(hit.seek.segment);
    setOffsetMs(hit.seek.offset_ms);
    setCursor(hit.marker.at_ms);
    if (hit.marker.at_ms < fromMs || hit.marker.at_ms > windowEnd) setWindowEnd(hit.marker.at_ms + zoom / 2);
  };

  const shiftWindow = (direction: number) => setWindowEnd((end) => Math.min(Date.now(), end + direction * zoom));

  const togglePin = async () => {
    if (!segment || !camera) return;
    const updated = await setPinned(camera, segment.id, segment.tier !== 'pinned');
    if (updated) setSegment({ ...segment, tier: updated.tier });
  };

  const removeSegment = async () => {
    if (!segment || !camera || !window.confirm(t('delete_confirm'))) return;
    if (await deleteSegment(camera, segment.id)) {
      setSegment(null);
      setWindowEnd((end) => end + 1);
    }
  };

  const markers = useMemo(() => {
    const wanted = KIND_GROUPS[group];
    return (timeline?.markers ?? []).filter((m) => !wanted.length || wanted.includes(m.kind));
  }, [timeline, group]);
  const current = cameras.find((c) => c.camera === camera);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto bg-surface p-4 text-on-surface sm:p-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Film className="h-5 w-5 text-primary" aria-hidden />
            <h1 className="text-lg font-bold tracking-tight">{t('title')}</h1>
          </div>
          <p className="text-xs text-on-surface-variant">{t('subtitle')}</p>
        </div>
        {storage && (
          <div className="flex items-center gap-2 text-xs text-outline">
            <HardDrive className="h-4 w-4" aria-hidden />
            <span>
              {t('storage_used')}: <strong>{bytes(storage.vault_used_bytes, lang)} / {bytes(storage.quota_bytes, lang)}</strong>
            </span>
          </div>
        )}
      </header>

      {cameras.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center text-outline">
          <Film className="h-10 w-10 stroke-[1.5]" aria-hidden />
          <p className="text-xs">{t('empty')}</p>
        </div>
      ) : (
        <>
          <nav className="flex flex-wrap items-center gap-1.5" aria-label={t('cameras')}>
            {cameras.map((c) => (
              <button
                key={c.camera}
                type="button"
                onClick={() => {
                  setCamera(c.camera);
                  setSegment(null);
                  setCursor(null);
                }}
                aria-pressed={camera === c.camera}
                className={`rounded-full px-3 py-1 text-xs font-semibold ${camera === c.camera ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-on-surface/5'}`}
              >
                {c.name}
              </button>
            ))}
            <button type="button" onClick={() => void loadCameras()} aria-label={t('refresh')} className="rounded-full p-1.5 text-outline hover:bg-on-surface/5">
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </nav>

          <SearchPanel
            camera={camera}
            lang={lang}
            t={t}
            kindLabel={kindLabel}
            onOpen={(cam, atMs) => {
              setCamera(cam);
              setWindowEnd(Math.min(Date.now(), atMs + zoom / 2));
              void openAt(atMs, cam);
            }}
          />

          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <Player
              camera={camera}
              segment={segment}
              offsetMs={offsetMs}
              emptyText={t('pick_moment')}
              speedLabel={t('speed')}
              onTime={setCursor}
              onSegment={(next) => {
                setSegment(next);
                setOffsetMs(0);
                if (!next) setNotice(t('end_of_recording'));
              }}
            />
            <aside className="flex flex-col gap-3 text-xs">
              {current && (
                <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-on-surface-variant">
                  <dt>{t('segments')}</dt>
                  <dd className="text-right font-mono">{current.segments}</dd>
                  <dt>{t('with_audio')}</dt>
                  <dd className="text-right font-mono">{current.audio_segments}</dd>
                  <dt>{t('size')}</dt>
                  <dd className="text-right font-mono">{bytes(current.bytes, lang)}</dd>
                  <dt>{t('oldest')}</dt>
                  <dd className="text-right">{current.first_ms ? `${dayLabel(current.first_ms, lang)} ${clock(current.first_ms, lang, false)}` : '-'}</dd>
                </dl>
              )}
              {segment && (
                <div className="flex flex-col gap-2">
                  <span className="font-semibold">
                    {clock(segment.start_ms, lang)} · {t(`tier_${segment.tier}`)}
                  </span>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => void togglePin()} className="flex items-center gap-1 rounded-full px-3 py-1 text-primary hover:bg-primary/10">
                      {segment.tier === 'pinned' ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                      {t(segment.tier === 'pinned' ? 'unpin' : 'pin')}
                    </button>
                    <button type="button" onClick={() => void removeSegment()} className="flex items-center gap-1 rounded-full px-3 py-1 text-error hover:bg-error/10">
                      <Trash2 className="h-3.5 w-3.5" />
                      {t('delete')}
                    </button>
                  </div>
                </div>
              )}
              {notice && <p role="status" className="text-on-surface-variant">{notice}</p>}
              <TranscriptPanel turns={turns} cursorMs={cursor} lang={lang} t={t} onSeek={(at) => void openAt(at)} />
            </aside>
          </div>

          <section className="flex flex-col gap-2" aria-label={t('timeline')}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1">
                <button type="button" onClick={() => shiftWindow(-1)} aria-label={t('earlier')} className="rounded-full p-1.5 hover:bg-on-surface/5">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs font-semibold">{dayLabel(fromMs, lang)} {clock(fromMs, lang, false)} – {clock(windowEnd, lang, false)}</span>
                <button type="button" onClick={() => shiftWindow(1)} aria-label={t('later')} className="rounded-full p-1.5 hover:bg-on-surface/5">
                  <ChevronRight className="h-4 w-4" />
                </button>
                <button type="button" onClick={() => setWindowEnd(Date.now())} className="rounded-full px-2 py-1 text-xs text-primary hover:bg-primary/10">
                  {t('now')}
                </button>
              </div>
              <div className="flex items-center gap-1">
                {ZOOMS.map((z) => (
                  <button
                    key={z.key}
                    type="button"
                    onClick={() => setZoom(z.ms)}
                    aria-pressed={zoom === z.ms}
                    className={`rounded-full px-2 py-0.5 text-xs ${zoom === z.ms ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-on-surface/5'}`}
                  >
                    {t(z.key)}
                  </button>
                ))}
              </div>
            </div>
            <TimelineBar
              fromMs={fromMs}
              toMs={windowEnd}
              spans={timeline?.spans ?? []}
              markers={markers}
              cursorMs={cursor}
              lang={lang}
              label={t('timeline')}
              onSeek={(at) => void openAt(at)}
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-1">
                {Object.keys(KIND_GROUPS).map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGroup(g)}
                    aria-pressed={group === g}
                    className={`rounded-full px-2.5 py-0.5 text-xs ${group === g ? 'bg-secondary text-on-secondary' : 'text-on-surface-variant hover:bg-on-surface/5'}`}
                  >
                    {t(`group_${g}`)}
                  </button>
                ))}
              </div>
              <div className="flex gap-1">
                <button type="button" onClick={() => void onJump('prev')} className="flex items-center gap-1 rounded-full px-3 py-1 text-xs hover:bg-on-surface/5">
                  <SkipBack className="h-3.5 w-3.5" />
                  {t('prev_event')}
                </button>
                <button type="button" onClick={() => void onJump('next')} className="flex items-center gap-1 rounded-full px-3 py-1 text-xs hover:bg-on-surface/5">
                  {t('next_event')}
                  <SkipForward className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            <p className="text-[11px] text-outline">{t('events_in_window', { count: markers.length })}</p>
          </section>
        </>
      )}
    </div>
  );
}

export default View;
