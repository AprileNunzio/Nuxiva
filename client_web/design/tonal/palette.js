import colors from 'tailwindcss/colors.js';
import { ensureContrast, hexToRgb, mix } from './color.js';

export const NEUTRALS = ['slate', 'gray', 'zinc', 'neutral', 'stone'];
export const ACCENTS = ['red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal', 'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose'];
export const HUES = [...NEUTRALS, ...ACCENTS];
export const SHADES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
export const KINDS = ['s', 'l', 't'];
export const TEXT_CONTRAST = 4.5;

const WHITE = [255, 255, 255];
const BLACK = [0, 0, 0];

export const SURFACES = {
  dark: {
    lowest: [6, 11, 25],
    low: [10, 19, 41],
    base: [15, 26, 54],
    high: [22, 36, 77],
    highest: [30, 48, 97],
    ink: [2, 6, 23],
  },
  light: {
    background: [241, 245, 249],
    base: [255, 255, 255],
    low: [248, 250, 252],
    high: [226, 232, 240],
    ink: [15, 23, 42],
  },
};

export const TEXT_REFERENCE = {
  light: [241, 245, 249],
  dark: [22, 36, 77],
  darkAuthored: [30, 41, 59],
};

const natural = (hue, shade) => hexToRgb(colors[hue][shade]);
const mirror = (shade) => (shade === 50 ? 950 : shade === 950 ? 50 : 1000 - shade);

const keyOf = (hue, shade) => `${hue}-${shade}`;

export const naturalTable = () => {
  const table = { white: WHITE, black: BLACK };
  for (const hue of HUES) for (const shade of SHADES) table[keyOf(hue, shade)] = natural(hue, shade);
  return table;
};

const invertedLine = () => {
  const table = {};
  for (const hue of HUES) for (const shade of SHADES) table[keyOf(hue, shade)] = natural(hue, mirror(shade));
  return table;
};

const towardDark = () => {
  const d = SURFACES.dark;
  const line = { ...invertedLine(), white: d.base, black: WHITE };
  const surface = { ...line, black: BLACK };
  for (const hue of NEUTRALS) Object.assign(surface, { [keyOf(hue, 50)]: d.low, [keyOf(hue, 100)]: d.high, [keyOf(hue, 200)]: d.highest });
  for (const hue of ACCENTS) {
    const core = natural(hue, 500);
    Object.assign(surface, { [keyOf(hue, 50)]: mix(core, d.base, 0.14), [keyOf(hue, 100)]: mix(core, d.base, 0.22), [keyOf(hue, 200)]: mix(core, d.base, 0.34) });
  }
  const text = { ...line, white: d.ink, black: WHITE };
  return { s: surface, l: line, t: text };
};

const towardLight = () => {
  const l = SURFACES.light;
  const line = { ...invertedLine(), white: l.ink, black: BLACK };
  const surface = { ...line };
  for (const hue of NEUTRALS) Object.assign(surface, { [keyOf(hue, 950)]: l.background, [keyOf(hue, 900)]: l.base, [keyOf(hue, 800)]: l.low, [keyOf(hue, 700)]: l.high });
  for (const hue of ACCENTS) {
    const core = natural(hue, 600);
    Object.assign(surface, { [keyOf(hue, 950)]: mix(core, WHITE, 0.1), [keyOf(hue, 900)]: mix(core, WHITE, 0.16), [keyOf(hue, 800)]: mix(core, WHITE, 0.26) });
  }
  const text = { ...line, white: l.ink, black: WHITE };
  return { s: surface, l: line, t: text };
};

const foreground = (authored) => {
  const keys = new Set([authored === 'light' ? 'black' : 'white']);
  for (const hue of HUES) for (const shade of SHADES) if (authored === 'light' ? shade >= 400 : shade <= 400) keys.add(keyOf(hue, shade));
  return keys;
};

const enforce = (text, authored, reference) => {
  const out = { ...text };
  for (const key of foreground(authored)) out[key] = ensureContrast(text[key], reference, TEXT_CONTRAST);
  return out;
};

export const CONTEXTS = {
  lightInLight: { selector: ':root[data-theme="light"] [data-tone="light"]', authored: 'light', theme: 'light' },
  lightInDark: { selector: ':root:not([data-theme="light"]) [data-tone="light"]', authored: 'light', theme: 'dark' },
  darkInDark: { selector: ':root:not([data-theme="light"]) [data-tone="dark"]', authored: 'dark', theme: 'dark' },
  darkInLight: { selector: ':root[data-theme="light"] [data-tone="dark"]', authored: 'dark', theme: 'light' },
};

export const resolveContext = ({ authored, theme }) => {
  const base = naturalTable();
  if (authored === theme) {
    const reference = authored === 'light' ? TEXT_REFERENCE.light : TEXT_REFERENCE.darkAuthored;
    return { s: base, l: base, t: enforce(base, authored, reference) };
  }
  const shifted = authored === 'light' ? towardDark() : towardLight();
  const reference = theme === 'dark' ? TEXT_REFERENCE.dark : TEXT_REFERENCE.light;
  return { s: { ...base, ...shifted.s }, l: { ...base, ...shifted.l }, t: enforce({ ...base, ...shifted.t }, authored, reference) };
};

export const KEYS = ['white', 'black', ...HUES.flatMap((hue) => SHADES.map((shade) => keyOf(hue, shade)))];
