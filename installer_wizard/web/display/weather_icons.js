(() => {
  const CLOUD = "M14 40h22a9 9 0 0 0 0-18 11 11 0 0 0-21 2.5A7.5 7.5 0 0 0 14 40z";
  const SUN = (cx, cy, r, ray) => `<g class="wxi-sun"><g class="wxi-rays" stroke="#ffd166" stroke-width="2.6" stroke-linecap="round">${Array.from({ length: 8 }, (_, i) => {
    const a = (i * Math.PI) / 4, c = Math.cos(a), s = Math.sin(a);
    return `<path d="M${(cx + c * (r + 4)).toFixed(1)} ${(cy + s * (r + 4)).toFixed(1)}L${(cx + c * (r + ray)).toFixed(1)} ${(cy + s * (r + ray)).toFixed(1)}"/>`;
  }).join("")}</g><circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#wxg-sun)"/></g>`;
  const MOON = (cx, cy, r) => `<g class="wxi-moon"><path d="M${cx + r * 0.5} ${cy - r}a${r} ${r} 0 1 0 ${r * 0.9} ${r * 1.5}a${r * 0.85} ${r * 0.85} 0 0 1-${r * 0.9}-${r * 1.5}z" fill="url(#wxg-moon)"/><circle cx="${cx + r * 1.3}" cy="${cy - r * 0.9}" r="1.2" fill="#fff" class="wxi-star"/></g>`;
  const cloud = (fill, cls = "wxi-cloud", dx = 0, dy = 0) => `<path class="${cls}" d="${CLOUD}" transform="translate(${dx} ${dy})" fill="${fill}"/>`;
  const drops = (n, color) => `<g class="wxi-drops" stroke="${color}" stroke-width="2.6" stroke-linecap="round">${Array.from({ length: n }, (_, i) =>
    `<path style="animation-delay:${i * 0.28}s" d="M${17 + i * 8} 41l-2 6"/>`).join("")}</g>`;
  const flakes = `<g class="wxi-flakes" fill="#fff">${[18, 26, 34].map((x, i) => `<circle style="animation-delay:${i * 0.45}s" cx="${x}" cy="43" r="2"/>`).join("")}</g>`;
  const BODY = {
    clear: SUN(24, 24, 9, 8),
    night: MOON(22, 24, 11),
    partly: `${SUN(18, 17, 7, 6)}${cloud("#cfe3f1", "wxi-cloud", 2, -2)}`,
    night_partly: `${MOON(17, 16, 8)}${cloud("#b8cde0", "wxi-cloud", 2, -2)}`,
    cloudy: `${cloud("#7f98ad", "wxi-cloud wxi-back", -4, -6)}${cloud("#cfe3f1")}`,
    fog: `${cloud("#a9bfce", "wxi-cloud", 0, -6)}<g class="wxi-fog" stroke="#a9bfce" stroke-width="2.6" stroke-linecap="round"><path d="M10 38h28"/><path d="M14 44h22"/></g>`,
    drizzle: `${cloud("#9fb7c9", "wxi-cloud", 0, -6)}${drops(3, "#6cc1ff")}`,
    rain: `${cloud("#8aa3b8", "wxi-cloud", 0, -6)}${drops(4, "#3d9bff")}`,
    snow: `${cloud("#bcd3e3", "wxi-cloud", 0, -6)}${flakes}`,
    storm: `${cloud("#5f768a", "wxi-cloud", 0, -6)}<path class="wxi-bolt" d="M26 28l-6 10h5l-3 9 9-12h-5l3-7z" fill="#ffd166"/>`,
  };
  const DEFS = `<defs><radialGradient id="wxg-sun" cx="35%" cy="35%"><stop offset="0" stop-color="#fff3b0"/><stop offset="1" stop-color="#ffb627"/></radialGradient>
    <linearGradient id="wxg-moon" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f4f7ff"/><stop offset="1" stop-color="#9db4ff"/></linearGradient></defs>`;
  const icon = (key, size = 48) => `<svg class="wxi" viewBox="0 0 48 48" width="${size}" height="${size}" aria-hidden="true">${DEFS}${BODY[key] || BODY.cloudy}</svg>`;
  const THEME = { clear: "clear", night: "night", partly: "partly", night_partly: "night", cloudy: "cloud", fog: "fog", drizzle: "rain", rain: "rain", snow: "snow", storm: "storm" };
  window.NuxivaWeatherIcons = Object.freeze({ icon, theme: (key) => THEME[key] || "cloud", keys: Object.freeze(Object.keys(BODY)) });
})();
