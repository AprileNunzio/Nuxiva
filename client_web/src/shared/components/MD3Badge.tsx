import React from 'react';
import './md3_badge.css';

export interface MD3BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'secondary' | 'tertiary' | 'error' | 'success' | 'neutral';
  dot?: boolean;
  children: React.ReactNode;
}

export const MD3Badge: React.FC<MD3BadgeProps> = ({
  variant = 'neutral',
  dot = false,
  children,
  className = '',
  ...props
}) => {
  return (
    <span
      className={`md3-badge md3-badge-${variant} ${className}`.trim()}
      {...props}
    >
      {dot && <span className="md3-badge-dot" aria-hidden="true" />}
      <span>{children}</span>
    </span>
  );
};
