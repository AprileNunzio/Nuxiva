import { useEffect, useState } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => window.matchMedia(query).matches);

  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    update();
    list.addEventListener('change', update);
    return () => list.removeEventListener('change', update);
  }, [query]);

  return matches;
}

export const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
export const TOUCH_ONLY_QUERY = '(hover: none)';
export const DOCKED_PANEL_QUERY = '(min-width: 1280px)';
