export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    screens: {
      'xs': '480px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
      '3xl': '1920px',
      '4xl': '2560px',
      '5xl': '3840px', // 4K UHD
      '6xl': '5120px', // 5K
      '8k': '7680px',  // 8K UHD
    },
    extend: {
      colors: {
        nuxiva: {
          cyan: '#00f0ff',
          blue: '#0051ff',
          dark: '#030712',
          card: '#0b132b',
          border: '#1c2541'
        }
      },
      maxWidth: {
        '8k': '7680px',
        '6k': '5120px',
        '4k': '3840px',
        '2k': '2560px'
      }
    },
  },
  plugins: [],
}
