import React from 'react';
import { CORE_COLOR } from '../domain/palette';
import { Point } from '../domain/types';

interface NucleusCoreProps {
  readonly center: Point;
  readonly radius: number;
  readonly active: boolean;
  readonly title: string;
  readonly subtitle: string;
  readonly counter: string;
  readonly ariaLabel: string;
  readonly onPreview: () => void;
  readonly onOpen: () => void;
}

const TICKS = Array.from({ length: 48 }, (_, i) => (i / 48) * Math.PI * 2);
const DENDRITES = Array.from({ length: 14 }, (_, i) => (i / 14) * Math.PI * 2 + 0.11);

export const NucleusCore: React.FC<NucleusCoreProps> = ({
  center,
  radius,
  active,
  title,
  subtitle,
  counter,
  ariaLabel,
  onPreview,
  onOpen,
}) => {
  const size = radius * 2.6;
  return (
    <div
      className="absolute z-20"
      style={{ left: center.x, top: center.y, width: size, height: size, transform: 'translate(-50%, -50%)' }}
    >
      <span
        aria-hidden="true"
        className="nm-ripple pointer-events-none absolute rounded-full border border-cyan-300/40"
        style={{ inset: size * 0.16 }}
      />
      <button
        type="button"
        aria-label={ariaLabel}
        data-active={active}
        onPointerEnter={(event) => event.pointerType === 'mouse' && onPreview()}
        onFocus={onPreview}
        onClick={onOpen}
        className="nm-lift group relative h-full w-full rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/80"
      >
        <svg viewBox="-130 -130 260 260" className="absolute inset-0 h-full w-full" aria-hidden="true">
          <defs>
            <radialGradient id="nm-soma" cx="50%" cy="42%" r="60%">
              <stop offset="0%" stopColor="#e0f2fe" stopOpacity="0.95" />
              <stop offset="28%" stopColor={CORE_COLOR} stopOpacity="0.75" />
              <stop offset="62%" stopColor="#1d4ed8" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#020617" stopOpacity="0.95" />
            </radialGradient>
            <linearGradient id="nm-arc" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#67e8f9" />
              <stop offset="100%" stopColor="#818cf8" />
            </linearGradient>
          </defs>
          <g className="nm-spin-slow">
            <circle r="122" fill="none" stroke="#38bdf8" strokeOpacity="0.25" strokeDasharray="1.5 7" />
            {TICKS.map((angle, index) => (
              <line
                key={angle}
                x1={Math.cos(angle) * 112}
                y1={Math.sin(angle) * 112}
                x2={Math.cos(angle) * (index % 4 === 0 ? 102 : 107)}
                y2={Math.sin(angle) * (index % 4 === 0 ? 102 : 107)}
                stroke="#7dd3fc"
                strokeOpacity={index % 4 === 0 ? 0.6 : 0.25}
                strokeWidth="1.2"
              />
            ))}
          </g>
          <g className="nm-spin-mid">
            <circle r="94" fill="none" stroke="url(#nm-arc)" strokeWidth="2.4" strokeDasharray="120 60 40 70" strokeLinecap="round" />
          </g>
          <g className="nm-spin-fast">
            <circle r="84" fill="none" stroke="#a5b4fc" strokeOpacity="0.35" strokeWidth="1" strokeDasharray="4 10" />
          </g>
          {DENDRITES.map((angle) => (
            <path
              key={angle}
              d={`M ${Math.cos(angle) * 70} ${Math.sin(angle) * 70} Q ${Math.cos(angle + 0.12) * 78} ${Math.sin(angle + 0.12) * 78} ${Math.cos(angle) * 86} ${Math.sin(angle) * 86}`}
              fill="none"
              stroke="#67e8f9"
              strokeOpacity="0.5"
              strokeWidth="1.4"
              strokeLinecap="round"
            />
          ))}
          <g className="nm-breathe">
            <circle r="70" fill="url(#nm-soma)" />
            <circle r="70" fill="none" stroke="#a5f3fc" strokeOpacity={active ? 0.9 : 0.55} strokeWidth="1.6" />
          </g>
        </svg>
        <span className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          <span
            className="nm-display font-bold uppercase tracking-[0.16em] text-white drop-shadow-[0_0_12px_rgba(125,211,252,0.9)]"
            style={{ fontSize: Math.max(12, radius * 0.26) }}
          >
            {title}
          </span>
          <span
            className="mt-0.5 font-mono uppercase tracking-[0.12em] text-cyan-100/80"
            style={{ fontSize: Math.max(8, radius * 0.11) }}
          >
            {subtitle}
          </span>
          <span
            className="mt-1.5 rounded-full border border-cyan-300/40 bg-slate-950/60 px-2 py-0.5 font-mono text-cyan-200"
            style={{ fontSize: Math.max(9, radius * 0.13) }}
          >
            {counter}
          </span>
        </span>
      </button>
    </div>
  );
};
