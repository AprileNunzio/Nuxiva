import React from 'react';
import { useObjectUrl } from '../../../shared/object_url/useObjectUrl';
import { sanitizeSvg } from '../sanitizeSvg';

interface PreviewProps {
  title: string;
  content: string;
}

export const SandboxedHtmlPreview: React.FC<PreviewProps> = ({ title, content }) => {
  const url = useObjectUrl(content, 'text/html;charset=utf-8');
  if (!url) {
    return null;
  }
  return (
    <iframe
      title={title}
      sandbox="allow-scripts"
      referrerPolicy="no-referrer"
      src={url}
      className="w-full h-full min-h-[400px] rounded-xl border border-slate-800 bg-white"
    />
  );
};

export const SvgImagePreview: React.FC<PreviewProps> = ({ title, content }) => {
  const url = useObjectUrl(sanitizeSvg(content), 'image/svg+xml');
  return (
    <div className="w-full h-full min-h-[400px] flex items-center justify-center p-4 bg-slate-900 rounded-xl border border-slate-800">
      {url && <img src={url} alt={title} className="max-w-full max-h-full object-contain" />}
    </div>
  );
};
