import React from 'react';

interface SparkProps {
  readonly values: readonly (number | null)[];
  readonly label: string;
  readonly tone?: string;
  readonly height?: number;
}

export const Sparkline: React.FC<SparkProps> = ({ values, label, tone = 'text-blue-600', height = 36 }) => {
  const known = values.map((v, i) => ({ v, i })).filter((p): p is { v: number; i: number } => p.v !== null);
  if (known.length < 2) {
    return null;
  }
  const min = Math.min(...known.map((p) => p.v));
  const max = Math.max(...known.map((p) => p.v));
  const span = max - min || 1;
  const w = 120;
  const x = (i: number) => (values.length > 1 ? (i / (values.length - 1)) * w : 0);
  const y = (v: number) => height - 4 - ((v - min) / span) * (height - 8);
  const path = known.map((p, k) => `${k ? 'L' : 'M'}${x(p.i).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' ');
  const last = known[known.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className={`h-9 w-full ${tone}`} role="img" aria-label={label} preserveAspectRatio="none">
      <path d={`${path} L${x(last.i).toFixed(1)} ${height} L${x(known[0].i).toFixed(1)} ${height} Z`} fill="currentColor" opacity="0.08" />
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      <circle cx={x(last.i)} cy={y(last.v)} r="2.4" fill="currentColor" />
    </svg>
  );
};

interface RingProps {
  readonly pct: number;
  readonly size?: number;
  readonly stroke?: number;
  readonly tone: string;
  readonly children?: React.ReactNode;
  readonly label: string;
}

export const Ring: React.FC<RingProps> = ({ pct, size = 112, stroke = 10, tone, children, label }) => {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const fill = Math.max(0, Math.min(100, pct));
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={label}>
      <svg viewBox={`0 0 ${size} ${size}`} className={`h-full w-full -rotate-90 ${tone}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeOpacity="0.14" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${(c * fill) / 100} ${c}`} className="transition-[stroke-dasharray] duration-700" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
    </div>
  );
};
