import React from 'react';

export const OSBackground: React.FC = () => {
  return (
    <div className="os-ambient-root" aria-hidden="true">
      <div className="os-aurora-mesh">
        <div className="os-aurora-blob os-aurora-blob-1" />
        <div className="os-aurora-blob os-aurora-blob-2" />
        <div className="os-aurora-blob os-aurora-blob-3" />
      </div>
      <div className="os-grid-overlay" />
      <div className="os-vignette-overlay" />
    </div>
  );
};
