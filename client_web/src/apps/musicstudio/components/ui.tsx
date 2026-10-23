import React from 'react';

export const cx = (...parts: Array<string | false | null | undefined>) => parts.filter(Boolean).join(' ');

interface BtnProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  readonly tone?: 'plain' | 'accent' | 'danger' | 'soft';
  readonly active?: boolean;
}

export const Btn: React.FC<BtnProps> = ({ tone = 'plain', active, className, ...rest }) => (
  <button
    type="button"
    {...rest}
    className={cx(
      'inline-flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40',
      tone === 'plain' && 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
      tone === 'soft' && 'bg-violet-50 text-violet-700 hover:bg-violet-100',
      tone === 'accent' && 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white shadow-sm hover:from-violet-500 hover:to-fuchsia-500',
      tone === 'danger' && 'border border-rose-200 bg-white text-rose-600 hover:bg-rose-50',
      active && 'ring-2 ring-violet-400',
      className,
    )}
  />
);

interface SliderProps {
  readonly value: number;
  readonly min: number;
  readonly max: number;
  readonly step?: number;
  readonly label: string;
  readonly onChange: (value: number) => void;
  readonly className?: string;
}

export const Slider: React.FC<SliderProps> = ({ value, min, max, step = 0.01, label, onChange, className }) => (
  <input
    type="range"
    aria-label={label}
    min={min}
    max={max}
    step={step}
    value={value}
    onChange={(e) => onChange(Number(e.target.value))}
    className={cx('h-1.5 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-violet-600', className)}
  />
);

export const Tabs: React.FC<{
  readonly items: ReadonlyArray<{ readonly id: string; readonly label: string }>;
  readonly value: string;
  readonly onChange: (id: string) => void;
}> = ({ items, value, onChange }) => (
  <div role="tablist" className="flex gap-1 rounded-xl bg-slate-100 p-1">
    {items.map((item) => (
      <button
        key={item.id}
        type="button"
        role="tab"
        aria-selected={item.id === value}
        onClick={() => onChange(item.id)}
        className={cx(
          'flex-1 rounded-lg px-2 py-1 text-xs font-medium transition',
          item.id === value ? 'bg-white text-violet-700 shadow-sm' : 'text-slate-500 hover:text-slate-700',
        )}
      >
        {item.label}
      </button>
    ))}
  </div>
);

export const Meter: React.FC<{ readonly value: number; readonly vertical?: boolean }> = ({ value, vertical }) => {
  const pct = Math.round(Math.min(1, Math.sqrt(value)) * 100);
  return (
    <div className={cx('overflow-hidden rounded-full bg-slate-100', vertical ? 'h-full w-2' : 'h-1.5 w-full')}>
      <div
        className={cx('rounded-full bg-gradient-to-t from-emerald-400 via-amber-400 to-rose-500', vertical ? 'w-full' : 'h-full')}
        style={vertical ? { height: `${pct}%`, marginTop: `${100 - pct}%` } : { width: `${pct}%` }}
      />
    </div>
  );
};

export const Field: React.FC<{ readonly label: string; readonly children: React.ReactNode }> = ({ label, children }) => (
  <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-slate-500">
    {label}
    {children}
  </label>
);

export const selectClass = 'rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs normal-case tracking-normal text-slate-800 outline-none focus:border-violet-400';
export const inputClass = selectClass;
