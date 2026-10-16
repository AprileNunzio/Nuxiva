import React, { useEffect, useState } from 'react';
import { VideoOff } from 'lucide-react';

interface SnapshotProps {
  readonly sourceId: string;
  readonly name: string;
  readonly offline: string;
}

export const Snapshot: React.FC<SnapshotProps> = ({ sourceId, name, offline }) => {
  const [stamp, setStamp] = useState(() => Date.now());
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const timer = window.setInterval(() => !document.hidden && setStamp(Date.now()), 3000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <figure className="relative aspect-video overflow-hidden rounded-xl border border-slate-800 bg-black">
      {failed ? (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-xs text-slate-500">
          <VideoOff className="h-6 w-6" aria-hidden="true" />
          {offline}
        </div>
      ) : (
        <img
          key={stamp}
          src={`/api/cameras/live/${encodeURIComponent(sourceId)}.jpg?t=${stamp}`}
          alt={name}
          onError={() => setFailed(true)}
          onLoad={() => setFailed(false)}
          className="h-full w-full object-cover"
        />
      )}
      <figcaption className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1 text-[11px] text-slate-200">{name}</figcaption>
    </figure>
  );
};
