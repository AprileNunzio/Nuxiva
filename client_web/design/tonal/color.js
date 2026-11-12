const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));

export const hexToRgb = (hex) => {
  const value = hex.replace('#', '');
  const full = value.length === 3 ? [...value].map((c) => c + c).join('') : value;
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
};

export const rgbToHex = (rgb) => `#${rgb.map((c) => Math.round(clamp(c, 0, 255)).toString(16).padStart(2, '0')).join('')}`;

const toLinear = (c) => {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
};

const fromLinear = (v) => 255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055);

export const luminance = (rgb) => {
  const [r, g, b] = rgb.map(toLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

export const contrast = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

export const rgbToOklch = (rgb) => {
  const [r, g, b] = rgb.map(toLinear);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return [L, Math.hypot(A, B), Math.atan2(B, A)];
};

const oklchToLinear = ([L, C, H]) => {
  const A = C * Math.cos(H);
  const B = C * Math.sin(H);
  const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
  const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
  const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
};

export const oklchToRgb = ([L, C, H]) => {
  let chroma = C;
  for (let i = 0; i < 40; i += 1) {
    const linear = oklchToLinear([L, chroma, H]);
    if (linear.every((v) => v >= -1e-4 && v <= 1 + 1e-4)) return linear.map((v) => fromLinear(clamp(v)));
    chroma *= 0.92;
  }
  return oklchToLinear([L, 0, H]).map((v) => fromLinear(clamp(v)));
};

export const mix = (a, b, weight) => a.map((c, i) => c * weight + b[i] * (1 - weight));

export const ensureContrast = (rgb, surface, target) => {
  if (contrast(rgb, surface) >= target) return rgb.map(Math.round);
  const [L, C, H] = rgbToOklch(rgb);
  const direction = luminance(surface) > 0.18 ? -1 : 1;
  for (let step = 1; step <= 100; step += 1) {
    const candidate = oklchToRgb([clamp(L + direction * step * 0.01), C, H]).map(Math.round);
    if (contrast(candidate, surface) >= target) return candidate;
  }
  return direction < 0 ? [0, 0, 0] : [255, 255, 255];
};
