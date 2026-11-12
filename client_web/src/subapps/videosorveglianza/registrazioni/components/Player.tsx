import React, { useEffect, useRef, useState } from 'react';
import { Gauge } from 'lucide-react';
import { nextSegment, playUrl } from '../api';
import type { SegmentRow } from '../types';

interface Props {
  camera: string;
  segment: SegmentRow | null;
  offsetMs: number;
  emptyText: string;
  speedLabel: string;
  onTime: (absoluteMs: number) => void;
  onSegment: (segment: SegmentRow | null) => void;
}

const SPEEDS = [0.5, 1, 2, 4, 8];

export function Player({ camera, segment, offsetMs, emptyText, speedLabel, onTime, onSegment }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const [speed, setSpeed] = useState(1);
  const pendingOffset = useRef(offsetMs);

  useEffect(() => {
    pendingOffset.current = offsetMs;
    const el = video.current;
    if (el && el.readyState >= 1 && segment) {
      el.currentTime = offsetMs / 1000;
    }
  }, [offsetMs, segment]);

  useEffect(() => {
    if (video.current) video.current.playbackRate = speed;
  }, [speed, segment]);

  if (!segment) {
    return (
      <div className="flex aspect-video w-full items-center justify-center rounded-2xl bg-on-surface/5 text-xs text-outline">
        {emptyText}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <video
        ref={video}
        key={`${camera}/${segment.id}`}
        src={playUrl(camera, segment.id)}
        controls
        autoPlay
        playsInline
        preload="metadata"
        controlsList="nodownload"
        className="aspect-video w-full rounded-2xl bg-black object-contain"
        onLoadedMetadata={(e) => {
          e.currentTarget.currentTime = pendingOffset.current / 1000;
          e.currentTarget.playbackRate = speed;
        }}
        onTimeUpdate={(e) => onTime(segment.start_ms + Math.round(e.currentTarget.currentTime * 1000))}
        onEnded={async () => {
          pendingOffset.current = 0;
          onSegment(await nextSegment(camera, segment.id));
        }}
      />
      <div className="flex items-center gap-1.5 text-xs">
        <Gauge className="h-3.5 w-3.5 text-outline" aria-hidden />
        <span className="text-outline">{speedLabel}</span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSpeed(s)}
            aria-pressed={speed === s}
            className={`rounded-full px-2 py-0.5 font-mono ${speed === s ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-on-surface/5'}`}
          >
            {s}×
          </button>
        ))}
      </div>
    </div>
  );
}

export default Player;
