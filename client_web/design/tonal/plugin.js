import plugin from 'tailwindcss/plugin.js';
import { CONTEXTS, KEYS, KINDS, naturalTable, resolveContext } from './palette.js';

const channels = (rgb) => rgb.map((c) => Math.round(c)).join(' ');
const same = (a, b) => a.every((c, i) => Math.round(c) === Math.round(b[i]));
const variable = (kind, key) => `--tw-${kind}-${key}`;

const reference = (kind, key) => {
  const base = channels(naturalTable()[key]);
  const surface = `var(${variable('s', key)}, ${base})`;
  return kind === 's' ? surface : `var(${variable(kind, key)}, ${surface})`;
};

const paletteFor = (kind) => {
  const out = {};
  for (const key of KEYS) {
    const value = `rgb(${reference(kind, key)} / <alpha-value>)`;
    const [hue, shade] = key.split('-');
    if (shade) (out[hue] ??= {})[shade] = value;
    else out[hue] = value;
  }
  return out;
};

export const declarations = (context) => {
  const resolved = resolveContext(context);
  const base = naturalTable();
  const out = {};
  for (const key of KEYS) {
    const s = resolved.s[key];
    if (!same(s, base[key])) out[variable('s', key)] = channels(s);
    for (const kind of ['l', 't']) if (!same(resolved[kind][key], s)) out[variable(kind, key)] = channels(resolved[kind][key]);
  }
  return out;
};

const reset = () => Object.fromEntries(KEYS.flatMap((key) => KINDS.map((kind) => [variable(kind, key), 'initial'])));

const role = (name) => `color-mix(in oklab, var(--md-sys-color-${name}) calc(<alpha-value> * 100%), transparent)`;

const ROLES = [
  'primary', 'on-primary', 'primary-container', 'on-primary-container',
  'secondary', 'on-secondary', 'secondary-container', 'on-secondary-container',
  'tertiary', 'on-tertiary', 'tertiary-container', 'on-tertiary-container',
  'error', 'on-error', 'error-container', 'on-error-container',
  'success', 'on-success', 'success-container', 'on-success-container',
  'warning', 'on-warning', 'warning-container', 'on-warning-container',
  'background', 'on-background', 'surface', 'on-surface', 'surface-variant', 'on-surface-variant',
  'surface-container-lowest', 'surface-container-low', 'surface-container', 'surface-container-high', 'surface-container-highest',
  'inverse-surface', 'inverse-on-surface', 'inverse-primary', 'outline', 'outline-variant', 'scrim',
];

export const semanticColors = () => ({
  ...Object.fromEntries(ROLES.map((name) => [name, role(name)])),
  foreground: role('on-surface'),
  border: role('outline'),
  input: role('outline'),
  ring: role('primary'),
  card: { DEFAULT: role('surface-container'), foreground: role('on-surface') },
  popover: { DEFAULT: role('surface-container-high'), foreground: role('on-surface') },
  muted: { DEFAULT: role('surface-container-high'), foreground: role('on-surface-variant') },
  accent: { DEFAULT: role('secondary-container'), foreground: role('on-secondary-container') },
  destructive: { DEFAULT: role('error'), foreground: role('on-error') },
});

export const tonalTheme = () => {
  const surface = paletteFor('s');
  const line = paletteFor('l');
  const text = paletteFor('t');
  const fixed = { transparent: 'transparent', current: 'currentColor', inherit: 'inherit' };
  const semantic = semanticColors();
  const merged = (palette) => ({ ...fixed, ...palette, ...semantic });
  const shell = { ...merged(surface), primary: { DEFAULT: role('primary'), foreground: role('on-primary') }, secondary: { DEFAULT: role('surface-container-high'), foreground: role('on-surface') } };
  const ink = { ...merged(text), primary: { DEFAULT: role('primary'), foreground: role('on-primary') }, secondary: { DEFAULT: role('secondary'), foreground: role('on-surface') } };
  const edge = { ...merged(line), primary: { DEFAULT: role('primary'), foreground: role('on-primary') } };
  return {
    colors: shell,
    textColor: ink,
    placeholderColor: ink,
    caretColor: ink,
    stroke: ink,
    textDecorationColor: ink,
    borderColor: { ...edge, DEFAULT: 'var(--md-sys-color-outline)' },
    ringColor: { ...edge, DEFAULT: 'var(--md-sys-color-primary)' },
    divideColor: edge,
    outlineColor: edge,
    ringOffsetColor: shell,
  };
};

export const tonalPlugin = plugin(({ addBase }) => {
  const rules = {};
  for (const context of Object.values(CONTEXTS)) rules[context.selector] = declarations(context);
  rules[':root [data-tone] [data-tone="fixed"]'] = reset();
  addBase(rules);
});

export const DARK_VARIANT = '&:is(:root:not([data-theme="light"]) *:not([data-tone="light"] *), [data-tone="dark"] *)';
