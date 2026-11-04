import React, { useId, useRef } from 'react';
import { CircuitBoard, Cpu, Lock, LucideIcon, Radio, Smartphone } from 'lucide-react';
import { KIND_COLORS, STALE_COLOR, withAlpha } from '../domain/palette';
import { NeuronKind, PlacedNeuron } from '../domain/types';

const KIND_ICONS: Readonly<Record<NeuronKind, LucideIcon>> = {
  compute: Cpu,
  satellite: Radio,
  micro: CircuitBoard,
  mobile: Smartphone,
};

const ARC_RADIUS = 44;
const ARC_LENGTH = 2 * Math.PI * ARC_RADIUS;

interface NeuronNodeProps {
  readonly placed: PlacedNeuron;
  readonly radius: number;
  readonly compact: boolean;
  readonly active: boolean;
  readonly stale: boolean;
  readonly load: number | null;
  readonly kindLabel: string;
  readonly ariaLabel: string;
  readonly onPreview: (id: string) => void;
  readonly onOpen: (id: string) => void;
}

export const NeuronNode: React.FC<NeuronNodeProps> = ({
  placed,
  radius,
  compact,
  active,
  stale,
  load,
  kindLabel,
  ariaLabel,
  onPreview,
  onOpen,
}) => {
  const pointerType = useRef<string>('mouse');
  const activeAtPress = useRef<boolean>(false);
  const gradientId = `nm-neuron-${useId().replace(/[^A-Za-z0-9_-]/g, '')}`;
  const { neuron, position } = placed;
  const color = stale ? STALE_COLOR : KIND_COLORS[neuron.kind];
  const Icon = KIND_ICONS[neuron.kind];
  const size = radius * 2;

  const handleClick = () => {
    if (pointerType.current !== 'mouse' && !activeAtPress.current) {
      onPreview(neuron.id);
      return;
    }
    onOpen(neuron.id);
  };

  return (
    <div
      className="pointer-events-none absolute z-10 flex flex-col items-center"
      style={{ left: position.x, top: position.y, transform: `translate(-50%, -${radius}px)` }}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        data-active={active}
        onPointerDown={(event) => {
          pointerType.current = event.pointerType;
          activeAtPress.current = active;
        }}
        onKeyDown={() => {
          pointerType.current = 'mouse';
        }}
        onPointerEnter={(event) => event.pointerType === 'mouse' && onPreview(neuron.id)}
        onFocus={() => onPreview(neuron.id)}
        onClick={handleClick}
        className="nm-lift pointer-events-auto relative rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
        style={{ width: size, height: size, ['--tw-ring-color' as string]: color }}
      >
        {active && (
          <span
            aria-hidden="true"
            className="nm-ripple pointer-events-none absolute inset-0 rounded-full border"
            style={{ borderColor: withAlpha(color, 0.6) }}
          />
        )}
        <svg viewBox="-50 -50 100 100" className="absolute inset-0 h-full w-full" aria-hidden="true">
          <defs>
            <radialGradient id={gradientId} cx="45%" cy="38%" r="65%">
              <stop offset="0%" stopColor={withAlpha(color, 0.55)} />
              <stop offset="70%" stopColor={withAlpha(color, 0.12)} />
              <stop offset="100%" stopColor="rgba(2,6,23,0.95)" />
            </radialGradient>
          </defs>
          <circle r="49" fill="rgba(2,6,23,0.88)" />
          <circle r="38" fill={`url(#${gradientId})`} />
          <circle r={ARC_RADIUS} fill="none" stroke={withAlpha(color, 0.18)} strokeWidth="4" />
          {load !== null && (
            <circle
              r={ARC_RADIUS}
              fill="none"
              stroke={color}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={`${Math.max(0.02, load) * ARC_LENGTH} ${ARC_LENGTH}`}
              transform="rotate(-90)"
            />
          )}
          <circle r="49" fill="none" stroke={withAlpha(color, active ? 0.9 : 0.4)} strokeWidth="1.2" />
        </svg>
        <Icon
          aria-hidden="true"
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ width: radius * 0.85, height: radius * 0.85, color }}
        />
        <span
          aria-hidden="true"
          className="absolute right-[6%] top-[6%] h-2.5 w-2.5 rounded-full border border-slate-950"
          style={{ backgroundColor: stale ? STALE_COLOR : '#34d399', boxShadow: `0 0 8px ${stale ? STALE_COLOR : '#34d399'}` }}
        />
        {neuron.isRemoteVpn && (
          <Lock aria-hidden="true" className="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-slate-950 p-0.5 text-violet-300" />
        )}
      </button>
      <span className="pointer-events-none mt-1.5 max-w-[6rem] truncate text-center text-[10px] font-semibold text-slate-100 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)] sm:max-w-[9rem] sm:text-xs">
        {neuron.name}
      </span>
      {!compact && (
        <span className="pointer-events-none font-mono text-[9px] uppercase tracking-[0.18em]" style={{ color: withAlpha(color, 0.85) }}>
          {kindLabel}
        </span>
      )}
    </div>
  );
};
