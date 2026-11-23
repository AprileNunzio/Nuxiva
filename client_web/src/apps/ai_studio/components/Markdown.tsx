import React, { useState } from 'react';
import { useStudioI18n } from '../scope';

/**
 * Renderer Markdown leggero e sicuro: costruisce elementi React (nessun innerHTML).
 * Supporta titoli, grassetto/corsivo, codice inline e a blocchi (con copia),
 * liste, citazioni, tabelle GFM, linee e link http(s).
 */

const SAFE_URL = /^(https?:\/\/|mailto:)/i;

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\n]+\*)|(\[[^\]]+\]\([^)\s]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyPrefix}-${i++}`;
    if (m[1]) {
      out.push(
        <code key={key} className="px-1 py-0.5 rounded bg-slate-800 text-cyan-300 text-[0.85em] font-mono">
          {tok.slice(1, -1)}
        </code>,
      );
    } else if (m[2]) {
      out.push(<strong key={key}>{renderInline(tok.slice(2, -2), key)}</strong>);
    } else if (m[3]) {
      out.push(<em key={key}>{renderInline(tok.slice(1, -1), key)}</em>);
    } else {
      const lm = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(tok);
      if (lm && SAFE_URL.test(lm[2])) {
        out.push(
          <a key={key} href={lm[2]} target="_blank" rel="noopener noreferrer" className="text-cyan-400 underline underline-offset-2">
            {lm[1]}
          </a>,
        );
      } else {
        out.push(tok);
      }
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const CodeBlock: React.FC<{ code: string; lang: string }> = ({ code, lang }) => {
  const { t } = useStudioI18n();
  const copyLabel = t('code_copy');
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard?.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div className="my-2 rounded-xl overflow-hidden border border-white/10 bg-slate-950/80">
      <div className="flex items-center justify-between px-3 py-1 bg-slate-900/80 text-[10px] uppercase tracking-wider text-slate-400">
        <span>{lang || 'code'}</span>
        <button type="button" onClick={copy} className="hover:text-cyan-300 transition-colors">
          {copied ? '✓' : copyLabel}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-xs leading-relaxed font-mono text-slate-200">
        <code>{code}</code>
      </pre>
    </div>
  );
};

function splitRow(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}

export function parseMarkdown(src: string): React.ReactNode[] {
  const lines = src.replace(/\r\n/g, '\n').split('\n');
  const nodes: React.ReactNode[] = [];
  let i = 0;
  let k = 0;
  const key = () => `md-${k++}`;

  while (i < lines.length) {
    const line = lines[i];

    const fence = /^```\s*([\w+-]*)\s*$/.exec(line);
    if (fence) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i])) buf.push(lines[i++]);
      i++;
      nodes.push(<CodeBlock key={key()} code={buf.join('\n')} lang={fence[1]} />);
      continue;
    }

    if (!line.trim()) {
      i++;
      continue;
    }

    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      const size = ['text-lg', 'text-base', 'text-sm', 'text-sm'][h[1].length - 1];
      nodes.push(
        <div key={key()} className={`${size} font-bold text-slate-50 mt-3 mb-1`}>
          {renderInline(h[2], `h${k}`)}
        </div>,
      );
      i++;
      continue;
    }

    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      nodes.push(<hr key={key()} className="my-3 border-white/10" />);
      i++;
      continue;
    }

    if (line.includes('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(lines[i + 1])) {
      const head = splitRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(splitRow(lines[i++]));
      nodes.push(
        <div key={key()} className="my-2 overflow-x-auto">
          <table className="text-xs border-collapse">
            <thead>
              <tr>
                {head.map((c, ci) => (
                  <th key={ci} className="border border-white/10 px-2 py-1 text-left bg-slate-800/60">
                    {renderInline(c, `th${k}-${ci}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>
                  {r.map((c, ci) => (
                    <td key={ci} className="border border-white/10 px-2 py-1">
                      {renderInline(c, `td${k}-${ri}-${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    if (/^>\s?/.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ''));
      nodes.push(
        <blockquote key={key()} className="my-2 pl-3 border-l-2 border-cyan-500/50 text-slate-300 italic">
          {renderInline(buf.join(' '), `q${k}`)}
        </blockquote>,
      );
      continue;
    }

    const ul = /^\s*[-*+]\s+/.test(line);
    const ol = /^\s*\d+[.)]\s+/.test(line);
    if (ul || ol) {
      const items: string[] = [];
      const re = ul ? /^\s*[-*+]\s+/ : /^\s*\d+[.)]\s+/;
      while (i < lines.length && re.test(lines[i])) items.push(lines[i++].replace(re, ''));
      const children = items.map((it, ii) => <li key={ii}>{renderInline(it, `li${k}-${ii}`)}</li>);
      nodes.push(
        ul ? (
          <ul key={key()} className="my-1 ml-5 list-disc space-y-0.5">{children}</ul>
        ) : (
          <ol key={key()} className="my-1 ml-5 list-decimal space-y-0.5">{children}</ol>
        ),
      );
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(```|#{1,4}\s|>\s?|\s*[-*+]\s+|\s*\d+[.)]\s+)/.test(lines[i])
    ) {
      para.push(lines[i++]);
    }
    if (para.length === 0) {
      para.push(lines[i++]);
    }
    nodes.push(
      <p key={key()} className="my-1 whitespace-pre-wrap">
        {renderInline(para.join('\n'), `p${k}`)}
      </p>,
    );
  }
  return nodes;
}

export const Markdown: React.FC<{ source: string }> = ({ source }) => <div className="space-y-0.5">{parseMarkdown(source)}</div>;

/** Esporta una conversazione come testo Markdown. */
export function messagesToMarkdown(title: string, msgs: { role: string; content: string; created_at: number }[]): string {
  const body = msgs
    .map((m) => `### ${m.role === 'user' ? 'User' : 'Nuxiva'} — ${new Date(m.created_at * 1000).toLocaleString()}\n\n${m.content}`)
    .join('\n\n---\n\n');
  return `# ${title}\n\n${body}\n`;
}

export function downloadMarkdown(title: string, msgs: { role: string; content: string; created_at: number }[]): void {
  const url = URL.createObjectURL(new Blob([messagesToMarkdown(title, msgs)], { type: 'text/markdown;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title.replace(/[^\w-]+/g, '_') || 'chat'}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
