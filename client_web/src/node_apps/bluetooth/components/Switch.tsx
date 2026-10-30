import React from 'react';

interface SwitchProps {
  readonly checked: boolean;
  readonly disabled?: boolean;
  readonly label: string;
  readonly onChange: (next: boolean) => void;
}

export const Switch: React.FC<SwitchProps> = ({ checked, disabled = false, label, onChange }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
      checked ? 'border-blue-600 bg-blue-600' : 'border-slate-300 bg-slate-200'
    }`}
  >
    <span className={`inline-block h-5 w-5 rounded-full bg-white shadow-sm transition ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} />
  </button>
);
