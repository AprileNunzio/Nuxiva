import { describe, expect, it } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { Markdown, messagesToMarkdown } from './Markdown';

const html = (src: string) => renderToStaticMarkup(React.createElement(Markdown, { source: src }));

describe('Markdown renderer', () => {
  it('renders bold, inline code and lists', () => {
    const out = html('**ciao** `x`\n\n- a\n- b');
    expect(out).toContain('<strong>ciao</strong>');
    expect(out).toContain('<code');
    expect(out.match(/<li>/g)).toHaveLength(2);
  });

  it('renders fenced code blocks and tables', () => {
    const out = html('```py\nprint(1)\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |');
    expect(out).toContain('print(1)');
    expect(out).toContain('<table');
    expect(out).toContain('<th');
  });

  it('escapes HTML and blocks unsafe links', () => {
    const out = html('<script>alert(1)</script> [x](javascript:alert(1)) [ok](https://a.it)');
    expect(out).not.toContain('<script>');
    expect(out).not.toContain('href="javascript:');
    expect(out).toContain('href="https://a.it"');
  });

  it('exports conversation to markdown', () => {
    const md = messagesToMarkdown('T', [{ role: 'user', content: 'hi', created_at: 0 }]);
    expect(md).toContain('# T');
    expect(md).toContain('hi');
  });
});
