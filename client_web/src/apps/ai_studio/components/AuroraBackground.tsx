import React from 'react';

export const ACCENTS: Record<string, [string, string]> = {
  cyan: ['0,240,255', '99,102,241'],
  violet: ['167,139,250', '236,72,153'],
  emerald: ['52,211,153', '56,189,248'],
};

const CSS = `
  @keyframes studio-aurora-drift { 0%,100% { transform: translate3d(0,0,0) scale(1); } 50% { transform: translate3d(1.5%,1%,0) scale(1.04); } }
  .studio-aurora { animation: studio-aurora-drift 18s ease-in-out infinite; }
  @keyframes studio-rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  [role="dialog"], [role="listbox"] { animation: studio-rise 160ms ease-out; }
  @media (prefers-reduced-motion: reduce) { .studio-aurora, [role="dialog"], [role="listbox"] { animation: none; } }
`;

export const AuroraBackground: React.FC<{ accent: string }> = ({ accent }) => {
  const [a1, a2] = ACCENTS[accent] || ACCENTS.cyan;
  return (
    <>
      <div
        aria-hidden="true"
        className="studio-aurora pointer-events-none absolute inset-0 opacity-60"
        style={{
          background: `radial-gradient(60% 50% at 15% 0%, rgba(${a1},0.12), transparent 70%), radial-gradient(50% 45% at 100% 100%, rgba(${a2},0.14), transparent 70%)`,
        }}
      />
      <style>{CSS}</style>
    </>
  );
};
