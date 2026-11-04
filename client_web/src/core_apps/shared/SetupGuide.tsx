import React, { useState } from 'react';
import { Check, Copy, ExternalLink } from 'lucide-react';
import { reportError } from '../../shared/errors/errorBus';
import { FeatureGuide } from './featureTypes';

interface Props {
  readonly guide?: FeatureGuide | null;
}

const safe = (url: string): boolean => /^https:\/\/[^\s"'<>]+$/.test(url);

const CopyBlock: React.FC<{ readonly label: string; readonly text: string }> = ({ label, text }) => {
  const [done, setDone] = useState(false);
  const copy = () => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setDone(true);
        window.setTimeout(() => setDone(false), 1800);
      })
      .catch((cause: unknown) => reportError('clipboard_failed', cause));
  };
  return (
    <figure className="mt-3 overflow-hidden rounded-lg border border-sky-200 bg-white">
      <figcaption className="flex items-center gap-2 border-b border-sky-100 px-3 py-1.5 text-xs font-semibold text-sky-900">
        <span className="min-w-0 flex-1">{label}</span>
        <button type="button" onClick={copy} aria-label={label} title={label}
          className="rounded-md p-1 text-sky-800 hover:bg-sky-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
          {done ? <Check className="h-4 w-4 text-emerald-600" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
        </button>
      </figcaption>
      <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all px-3 py-2 font-mono text-[11px] leading-relaxed text-slate-700">{text}</pre>
    </figure>
  );
};

export const SetupGuide: React.FC<Props> = ({ guide }) => {
  if (!guide || (guide.steps.length === 0 && guide.links.length === 0)) {
    return null;
  }
  const items = (guide.items ?? []).filter((item) => typeof item.label === 'string');
  const blocks = (guide.copy ?? []).filter((block) => typeof block.text === 'string' && block.text);
  return (
    <section className="mb-5 rounded-xl border border-sky-200 bg-sky-50 p-4 text-slate-800" aria-label={guide.title}>
      <h2 className="mb-2 text-sm font-bold text-sky-900">{guide.title}</h2>
      <ol className="list-decimal space-y-1.5 pl-5 text-sm">
        {guide.steps.map((step, index) => (
          <li key={index}>{step}</li>
        ))}
      </ol>
      {items.length > 0 && (
        <div className="mt-3">
          {guide.items_title && <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wide text-sky-900">{guide.items_title}</h3>}
          <ul className="grid gap-1.5 sm:grid-cols-2">
            {items.map((item) => (
              <li key={item.label} className="flex items-start gap-2 rounded-lg border border-sky-200 bg-white px-3 py-2 text-xs">
                <span className="min-w-0 flex-1">
                  <b className="block text-slate-900">{item.label}</b>
                  {item.detail && <span className="text-slate-600">{item.detail}</span>}
                </span>
                {item.url && safe(item.url) && (
                  <a href={item.url} target="_blank" rel="noopener noreferrer" aria-label={item.label}
                    className="shrink-0 rounded-md p-1 text-sky-800 hover:bg-sky-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {blocks.map((block) => (
        <CopyBlock key={block.label} label={block.label} text={block.text} />
      ))}
      {guide.links.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {guide.links.filter((link) => safe(link.url)).map((link) => (
            <li key={link.url}>
              <a href={link.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-sky-300 bg-white px-3 py-1.5 text-xs font-semibold text-sky-900 hover:bg-sky-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      )}
      {guide.note && <p className="mt-3 text-xs text-slate-600">{guide.note}</p>}
    </section>
  );
};
