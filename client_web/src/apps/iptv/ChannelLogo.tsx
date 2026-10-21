import React, { useState } from 'react';
import { Tv } from 'lucide-react';
import { getLogoProxyUrl } from './api';

interface ChannelLogoProps {
  readonly url?: string;
  readonly name: string;
  readonly size?: 'sm' | 'md' | 'lg' | 'hero';
  readonly className?: string;
}

export const ChannelLogo: React.FC<ChannelLogoProps> = ({
  url,
  name,
  size = 'md',
  className = '',
}) => {
  const [error, setError] = useState(false);

  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase() || name.slice(0, 2).toUpperCase();

  const dimensions = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-11 w-11 text-sm',
    lg: 'h-14 w-14 text-base',
    hero: 'h-24 w-24 text-xl',
  }[size];

  if (!url || error) {
    return (
      <div
        className={`flex shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-800 via-slate-850 to-slate-900 border border-slate-700/60 font-bold text-cyan-300 shadow-md select-none transition-all ${dimensions} ${className}`}
      >
        <div className="flex flex-col items-center justify-center gap-0.5">
          <Tv className="h-4 w-4 text-cyan-400/80" />
          <span className="font-mono tracking-wider text-[11px] font-extrabold">{initials}</span>
        </div>
      </div>
    );
  }

  const src = getLogoProxyUrl(url);

  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-2xl bg-slate-900/90 border border-slate-700/60 p-1.5 overflow-hidden shadow-md backdrop-blur-sm transition-all group-hover:border-cyan-500/50 ${dimensions} ${className}`}
    >
      <img
        src={src}
        alt={name}
        referrerPolicy="no-referrer"
        onError={() => setError(true)}
        className="h-full w-full object-contain filter drop-shadow select-none transition-transform duration-300 group-hover:scale-105"
      />
    </div>
  );
};
