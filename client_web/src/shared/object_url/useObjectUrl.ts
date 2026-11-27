import { useEffect, useState } from 'react';

export function useObjectUrl(content: string, type: string): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const next = URL.createObjectURL(new Blob([content], { type }));
    setUrl(next);
    return () => {
      URL.revokeObjectURL(next);
    };
  }, [content, type]);

  return url;
}
