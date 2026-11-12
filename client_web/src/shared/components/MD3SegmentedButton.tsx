import React from 'react';
import './md3_segmented.css';

export interface SegmentOption<T extends string = string> {
  value: T;
  label: React.ReactNode;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface MD3SegmentedButtonProps<T extends string = string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel?: string;
  className?: string;
}

export function MD3SegmentedButton<T extends string = string>({
  options,
  value,
  onChange,
  ariaLabel,
  className = '',
}: MD3SegmentedButtonProps<T>): React.ReactElement {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`md3-segmented-group ${className}`.trim()}
    >
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            disabled={opt.disabled}
            onClick={() => onChange(opt.value)}
            className={`md3-segmented-item ${isSelected ? 'is-selected' : ''}`}
          >
            {opt.icon && <span className="md3-segmented-icon" aria-hidden="true">{opt.icon}</span>}
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
