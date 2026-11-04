import React, { useEffect, useMemo, useRef } from 'react';
import type { Catalog, Clip, Project, Track } from '../types';
import type { Mutator } from '../useStudio';
import type { Player } from '../engine/player';

interface Props {
  readonly project: Project;
  readonly catalog: Catalog;
  readonly track: Track | undefined;
  readonly clip: Clip | undefined;
  readonly beat: number;
  readonly edit: (m: Mutator) => void;
  readonly player: Player | null;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const KEY_W = 56;
const BEAT_W = 48;
const ROW_H = 14;
const BLACK = new Set([1, 3, 6, 8, 10]);

export const PianoRoll: React.FC<Props> = ({ project, catalog, track, clip, beat, edit, player, t }) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const drums = track?.role === 'drums';
  const rows = useMemo(() => {
    if (drums) return Object.entries(catalog.lanes).sort((a, b) => b[1] - a[1]).map(([name, midi]) => ({ midi, label: name.replace('_', ' ') }));
    const base = track?.role === 'bass' ? 28 : track?.role === 'lead' || track?.role === 'arp' ? 55 : 40;
    return Array.from({ length: 37 }, (_, i) => base + 36 - i).map((midi) => ({ midi, label: `${catalog.notes[midi % 12]}${Math.floor(midi / 12) - 1}` }));
  }, [drums, track?.role, catalog]);
  const width = clip ? Math.max(1, clip.length) * BEAT_W : 0;
  const height = rows.length * ROW_H;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !clip) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = (KEY_W + width) * ratio;
    canvas.height = height * ratio;
    const g = canvas.getContext('2d');
    if (!g) return;
    g.scale(ratio, ratio);
    g.clearRect(0, 0, KEY_W + width, height);
    rows.forEach((row, i) => {
      const black = !drums && BLACK.has(row.midi % 12);
      g.fillStyle = black ? '#f1f5f9' : '#ffffff';
      g.fillRect(KEY_W, i * ROW_H, width, ROW_H);
      g.fillStyle = black ? '#1e293b' : '#f8fafc';
      g.fillRect(0, i * ROW_H, KEY_W, ROW_H);
      g.fillStyle = black ? '#e2e8f0' : '#475569';
      g.font = '9px system-ui';
      g.fillText(row.label, 4, i * ROW_H + 10);
      g.strokeStyle = '#eef2f7';
      g.beginPath();
      g.moveTo(KEY_W, (i + 1) * ROW_H);
      g.lineTo(KEY_W + width, (i + 1) * ROW_H);
      g.stroke();
    });
    for (let b = 0; b <= clip.length * 4; b += 1) {
      g.strokeStyle = b % (project.beats * 4) === 0 ? '#cbd5e1' : b % 4 === 0 ? '#e2e8f0' : '#f1f5f9';
      g.beginPath();
      g.moveTo(KEY_W + (b / 4) * BEAT_W, 0);
      g.lineTo(KEY_W + (b / 4) * BEAT_W, height);
      g.stroke();
    }
    g.fillStyle = track?.color ?? '#7c3aed';
    for (const n of clip.notes) {
      const i = rows.findIndex((r) => r.midi === n.p);
      if (i < 0) continue;
      g.globalAlpha = 0.4 + n.v * 0.6;
      g.fillRect(KEY_W + n.t * BEAT_W + 1, i * ROW_H + 1, Math.max(4, n.d * BEAT_W - 2), ROW_H - 2);
    }
    g.globalAlpha = 1;
    const local = beat - clip.start;
    if (local >= 0 && local <= clip.length) {
      g.fillStyle = '#f43f5e';
      g.fillRect(KEY_W + local * BEAT_W, 0, 1.5, height);
    }
  }, [clip, rows, width, height, beat, track?.color, project.beats, drums]);

  if (!track || !clip) return <div className="flex flex-1 items-center justify-center text-sm text-slate-400">{t('pick_clip')}</div>;
  if (clip.vocal) return <div className="flex flex-1 items-center justify-center text-sm text-slate-500">{t('vocal_clip_hint')}</div>;

  const onClick = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left - KEY_W;
    const row = rows[Math.floor((e.clientY - rect.top) / ROW_H)];
    if (x < 0) {
      if (row) void player?.preview(track.id, row.midi);
      return;
    }
    if (!row) return;
    const time = Math.floor((x / BEAT_W) * 4) / 4;
    const hit = clip.notes.findIndex((n) => n.p === row.midi && time >= n.t - 0.001 && time < n.t + Math.max(0.25, n.d));
    edit((p) => ({
      ...p,
      tracks: p.tracks.map((tr) =>
        tr.id !== track.id
          ? tr
          : {
              ...tr,
              clips: tr.clips.map((c) =>
                c.id !== clip.id
                  ? c
                  : { ...c, notes: hit >= 0 ? c.notes.filter((_, i) => i !== hit) : [...c.notes, { t: time, d: drums ? 0.25 : 0.5, p: row.midi, v: 0.8 }].slice(0, 640) },
              ),
            },
      ),
    }));
    if (hit < 0) void player?.preview(track.id, row.midi);
  };

  return (
    <div className="flex-1 overflow-auto bg-white">
      <canvas ref={ref} onPointerDown={onClick} style={{ width: KEY_W + width, height }} className="cursor-crosshair" aria-label={t('piano_roll')} />
    </div>
  );
};
