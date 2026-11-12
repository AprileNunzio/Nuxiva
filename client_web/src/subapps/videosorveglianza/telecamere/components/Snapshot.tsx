import React, { useEffect, useState, useCallback } from 'react';
import { VideoOff, Radio, RefreshCw } from 'lucide-react';
import { adminPath } from '../../../../shared/http/basePath';

interface SnapshotProps {
  readonly sourceId: string;
  readonly name: string;
  readonly offlineLabel: string;
  readonly liveLabel: string;
  readonly streamLabel?: string;
  readonly isRecording?: boolean;
}

export const Snapshot: React.FC<SnapshotProps> = ({
  sourceId,
  name,
  offlineLabel,
  liveLabel,
  streamLabel = 'Stream',
  isRecording = false,
}) => {
  const [stamp, setStamp] = useState(() => Date.now());
  const [failed, setFailed] = useState(false);
  const [useMjpeg, setUseMjpeg] = useState(false);

  const refreshSnapshot = useCallback(() => {
    if (!document.hidden && !useMjpeg) {
      setStamp(Date.now());
    }
  }, [useMjpeg]);

  useEffect(() => {
    if (useMjpeg) {
      return;
    }
    const timer = window.setInterval(refreshSnapshot, 3000);
    return () => window.clearInterval(timer);
  }, [refreshSnapshot, useMjpeg]);

  const handleRetry = () => {
    setFailed(false);
    setStamp(Date.now());
  };

  const imageSrc = useMjpeg
    ? adminPath(`/api/cameras/live/${encodeURIComponent(sourceId)}.mjpg`)
    : adminPath(`/api/cameras/live/${encodeURIComponent(sourceId)}.jpg?t=${stamp}`);

  return (
    <figure className="relative aspect-video w-full overflow-hidden rounded-2xl border border-outline-variant/60 bg-black shadow-sm transition-all hover:border-primary/50">
      {failed ? (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center text-outline">
          <VideoOff className="h-8 w-8 stroke-[1.5] text-error/80" />
          <span className="text-xs font-semibold text-on-surface-variant">{offlineLabel}</span>
          <button
            type="button"
            onClick={handleRetry}
            className="mt-1 flex items-center gap-1 rounded-lg bg-surface-container-high px-2.5 py-1 text-[11px] font-medium text-on-surface hover:bg-surface-container-highest"
          >
            <RefreshCw className="h-3 w-3" />
            <span>{name}</span>
          </button>
        </div>
      ) : (
        <img
          key={useMjpeg ? 'mjpeg' : stamp}
          src={imageSrc}
          alt={name}
          onError={() => setFailed(true)}
          onLoad={() => setFailed(false)}
          className="h-full w-full object-cover"
        />
      )}

      <div className="absolute top-2 left-2 flex items-center gap-1.5 pointer-events-none">
        <span className="flex items-center gap-1 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase text-emerald-400 backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          {liveLabel}
        </span>
        {isRecording && (
          <span className="flex items-center gap-1 rounded-full bg-error/80 px-2 py-0.5 text-[10px] font-bold uppercase text-white backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
            REC
          </span>
        )}
      </div>

      <div className="absolute top-2 right-2">
        <button
          type="button"
          onClick={() => {
            setFailed(false);
            setUseMjpeg((prev) => !prev);
          }}
          className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold backdrop-blur-sm transition-colors ${
            useMjpeg
              ? 'bg-primary text-on-primary shadow-sm'
              : 'bg-black/60 text-white hover:bg-black/80'
          }`}
          title={streamLabel}
        >
          <Radio className="h-3 w-3" />
          <span>{useMjpeg ? 'MJPEG' : '3s'}</span>
        </button>
      </div>

      <figcaption className="absolute bottom-0 inset-x-0 flex items-center justify-between bg-gradient-to-t from-black/80 via-black/40 to-transparent px-3 py-2 text-white">
        <span className="truncate text-xs font-semibold drop-shadow">{name}</span>
        <span className="text-[10px] font-mono text-white/70 drop-shadow">{sourceId}</span>
      </figcaption>
    </figure>
  );
};

export default Snapshot;
