import plugin from 'tailwindcss/plugin.js';

export const CONTAINER_STEPS = {
  xs: '24rem',
  sm: '32rem',
  md: '42rem',
  lg: '56rem',
  xl: '68rem',
  '2xl': '84rem',
  '3xl': '104rem',
  '4xl': '136rem',
  '5xl': '200rem',
  '6xl': '270rem',
  '8k': '400rem',
};

export const layoutPlugin = plugin(({ addVariant }) => {
  for (const [name, width] of Object.entries(CONTAINER_STEPS)) {
    addVariant(`cq-${name}`, `@container (min-width: ${width})`);
  }
});
