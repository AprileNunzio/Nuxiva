import React from 'react';

interface ExpertAvatarProps {
  readonly icon: string;
  readonly color: string;
  readonly busy?: boolean;
  readonly size?: 'sm' | 'lg';
}

export const ExpertAvatar: React.FC<ExpertAvatarProps> = ({ icon, color, busy = false, size = 'sm' }) => {
  const box = size === 'lg' ? 'h-16 w-16 text-3xl 3xl:h-20 3xl:w-20 3xl:text-4xl' : 'h-11 w-11 text-xl';
  return (
    <span
      className={`relative flex shrink-0 items-center justify-center rounded-2xl border ${box}`}
      style={{
        borderColor: `${color}99`,
        background: `radial-gradient(circle at 30% 25%, ${color}55, rgba(2,6,23,0.92) 70%)`,
        boxShadow: `0 0 ${busy ? 28 : 16}px ${color}${busy ? '88' : '40'}`,
      }}
      aria-hidden="true"
    >
      {icon || '◆'}
      {busy && <span className="absolute -inset-1 animate-ping rounded-2xl border motion-reduce:animate-none" style={{ borderColor: `${color}66` }} />}
    </span>
  );
};
