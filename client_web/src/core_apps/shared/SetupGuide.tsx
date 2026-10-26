import React from 'react';
import { ExternalLink } from 'lucide-react';
import { FeatureGuide } from './featureTypes';

interface Props {
  readonly guide?: FeatureGuide | null;
}

const safe = (url: string): boolean => /^https:\/\//.test(url);

export const SetupGuide: React.FC<Props> = ({ guide }) => {
  if (!guide || (guide.steps.length === 0 && guide.links.length === 0)) {
    return null;
  }
  return (
    <section className="mb-5 rounded-xl border border-sky-200 bg-sky-50 p-4 text-slate-800" aria-label={guide.title}>
      <h2 className="mb-2 text-sm font-bold text-sky-900">{guide.title}</h2>
      <ol className="list-decimal space-y-1.5 pl-5 text-sm">
        {guide.steps.map((step, index) => (
          <li key={index}>{step}</li>
        ))}
      </ol>
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
