import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const SOURCE_ROOT = join(__dirname, '..', '..');
const SOURCE_FILE = /\.(ts|tsx)$/;
const TEST_FILE = /\.test\.(ts|tsx)$/;
const SINKS: readonly RegExp[] = [
  /\.innerHTML\s*[+]?=(?!=)/,
  /\.outerHTML\s*[+]?=(?!=)/,
  /\binsertAdjacentHTML\s*\(/,
  /\bdangerouslySetInnerHTML\b/,
  /\bsrcDoc\b/,
  /\.srcdoc\s*=(?!=)/,
  /\bdocument\.write(ln)?\s*\(/,
  /\bparseFromString\s*\(/,
  /\bcreateContextualFragment\s*\(/,
  /\bsetHTMLUnsafe\s*\(/,
  /\bnew Function\s*\(/,
  /\beval\s*\(/,
];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      return sourceFiles(path);
    }
    return SOURCE_FILE.test(entry.name) && !TEST_FILE.test(entry.name) ? [path] : [];
  });
}

describe('trusted types sinks', () => {
  it('keeps the admin bundle free of string HTML and script sinks', () => {
    const offenders = sourceFiles(SOURCE_ROOT).flatMap((file) =>
      readFileSync(file, 'utf8')
        .split('\n')
        .flatMap((line, index) =>
          SINKS.some((sink) => sink.test(line)) ? [`${relative(SOURCE_ROOT, file)}:${index + 1}: ${line.trim()}`] : [],
        ),
    );
    expect(offenders).toEqual([]);
  });
});
