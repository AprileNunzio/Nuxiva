import React from 'react';
import './md3_card.css';

export interface MD3CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  variant?: 'elevated' | 'filled' | 'outlined';
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  footer?: React.ReactNode;
  children?: React.ReactNode;
}

export const MD3Card: React.FC<MD3CardProps> = ({
  variant = 'elevated',
  title,
  subtitle,
  action,
  footer,
  children,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`md3-card md3-card-${variant} ${className}`.trim()}
      {...props}
    >
      {(title || subtitle || action) && (
        <div className="md3-card-header">
          <div className="md3-card-title-group">
            {title && <div className="md3-card-title">{title}</div>}
            {subtitle && <div className="md3-card-subtitle">{subtitle}</div>}
          </div>
          {action && <div className="md3-card-action">{action}</div>}
        </div>
      )}
      {children && <div className="md3-card-content">{children}</div>}
      {footer && <div className="md3-card-footer">{footer}</div>}
    </div>
  );
};
