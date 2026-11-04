import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const language = id.match(/\/language\/(it|en|fr|es)\.json$/);
          if (language) return `locale-${language[1]}`;
          if (id.includes('/node_modules/three/')) return 'graphics-three';
          if (id.includes('/node_modules/hls.js/')) return 'media-hls';
          return undefined;
        },
      },
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
