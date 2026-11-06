import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { contrast, hexToRgb } from '../../../design/tonal/color.js';
import { CONTEXTS, HUES, SHADES, TEXT_CONTRAST, TEXT_REFERENCE, resolveContext } from '../../../design/tonal/palette.js';
import { declarations } from '../../../design/tonal/plugin.js';

const foreground = (authored: string) => [
  authored === 'light' ? 'black' : 'white',
  ...HUES.flatMap((hue) => SHADES.filter((shade) => (authored === 'light' ? shade >= 400 : shade <= 400)).map((shade) => `${hue}-${shade}`)),
];

const reference = (authored: string, theme: string) =>
  theme === 'light' ? TEXT_REFERENCE.light : authored === 'dark' ? TEXT_REFERENCE.darkAuthored : TEXT_REFERENCE.dark;

describe('tonal palette', () => {
  for (const [name, context] of Object.entries(CONTEXTS)) {
    it(`keeps every foreground text tone readable in ${name}`, () => {
      const { t } = resolveContext(context);
      for (const key of foreground(context.authored)) {
        expect(contrast(t[key], reference(context.authored, context.theme)), key).toBeGreaterThanOrEqual(TEXT_CONTRAST);
      }
    });
  }

  it('flips neutral surfaces when a light-authored view runs in the dark theme', () => {
    const { s, t } = resolveContext(CONTEXTS.lightInDark);
    expect(contrast(t['slate-900'], s.white)).toBeGreaterThanOrEqual(7);
    expect(contrast(t.white, s['blue-600'])).toBeGreaterThanOrEqual(TEXT_CONTRAST);
  });

  it('flips neutral surfaces when a dark-authored view runs in the light theme', () => {
    const { s, t } = resolveContext(CONTEXTS.darkInLight);
    expect(contrast(t.white, s['slate-900'])).toBeGreaterThanOrEqual(7);
    expect(contrast(t['slate-400'], s['slate-950'])).toBeGreaterThanOrEqual(TEXT_CONTRAST);
  });

  it('emits only channel triplets as variable values', () => {
    for (const context of Object.values(CONTEXTS)) {
      for (const [name, value] of Object.entries(declarations(context))) {
        expect(name).toMatch(/^--tw-[slt]-[a-z]+(-\d+)?$/);
        expect(value).toMatch(/^\d{1,3} \d{1,3} \d{1,3}$/);
      }
    }
  });
});

describe('system color roles', () => {
  const css = readFileSync(new URL('./os_theme.css', import.meta.url), 'utf8');
  const block = (selector: string) => css.split(`${selector} {`)[1].split('}')[0];
  const roles = (text: string) => Object.fromEntries([...text.matchAll(/--md-sys-color-([a-z-]+):\s*(#[0-9a-f]{6})/gi)].map((m) => [m[1], hexToRgb(m[2])]));
  const pairs = [
    ['on-surface', 'surface'], ['on-surface', 'surface-container-high'], ['on-surface-variant', 'surface'], ['on-surface-variant', 'surface-container-high'],
    ['on-primary', 'primary'], ['on-primary-container', 'primary-container'], ['on-secondary', 'secondary'], ['on-secondary-container', 'secondary-container'],
    ['on-tertiary', 'tertiary'], ['on-tertiary-container', 'tertiary-container'], ['on-error', 'error'], ['on-error-container', 'error-container'],
    ['on-success', 'success'], ['on-success-container', 'success-container'], ['on-warning', 'warning'], ['on-warning-container', 'warning-container'],
    ['primary', 'surface'], ['primary', 'surface-container-high'], ['error', 'surface'], ['success', 'surface'], ['warning', 'surface'],
    ['inverse-on-surface', 'inverse-surface'],
  ];
  for (const theme of ['dark', 'light']) {
    it(`meets WCAG AA for every role pair in the ${theme} theme`, () => {
      const palette = roles(block(`[data-theme="${theme}"]`));
      for (const [ink, paper] of pairs) expect(contrast(palette[ink], palette[paper]), `${ink}/${paper}`).toBeGreaterThanOrEqual(4.5);
    });
  }
});
