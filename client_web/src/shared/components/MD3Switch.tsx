import React, { useId } from 'react';
import { Check } from 'lucide-react';
import './md3_switch.css';

export interface MD3SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  name?: string;
  id?: string;
  ariaLabel?: string;
}

export const MD3Switch: React.FC<MD3SwitchProps> = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  name,
  id,
  ariaLabel,
}) => {
  const generatedId = useId();
  const inputId = id || generatedId;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLLabelElement>) => {
    if (disabled) return;
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      onChange(!checked);
    }
  };

  return (
    <label
      htmlFor={inputId}
      className={`md3-switch-wrapper ${disabled ? 'is-disabled' : ''}`}
      onKeyDown={handleKeyDown}
      tabIndex={disabled ? -1 : 0}
      role="switch"
      aria-checked={checked}
      aria-disabled={disabled}
      aria-label={ariaLabel || label}
    >
      <input
        type="checkbox"
        id={inputId}
        name={name}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="md3-switch-input"
        tabIndex={-1}
        aria-hidden="true"
      />
      <div className="md3-switch-track" aria-hidden="true">
        <div className="md3-switch-thumb">
          <Check className="md3-switch-icon" strokeWidth={3} />
        </div>
      </div>
      {(label || description) && (
        <div className="md3-switch-text-container">
          {label && <div className="md3-switch-label">{label}</div>}
          {description && <div className="md3-switch-description">{description}</div>}
        </div>
      )}
    </label>
  );
};
