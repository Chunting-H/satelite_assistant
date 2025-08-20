import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:2025',
        changeOrigin: true,
      },
      '/api/ws': {
        target: 'ws://127.0.0.1:2025',
        ws: true,
      }
    },
    fs: {
      allow: ['..']
    }
  },
  assetsInclude: ['**/*.czml'],
  publicDir: 'public',
  build: {
    chunkSizeWarningLimit: 1600, // Cesium很大，需要增加限制
  },
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium')
  },
  resolve: {
    alias: {
      // 使用一个确定存在的路径，注意路径是相对于项目根目录的
      'cesium': path.resolve(__dirname, 'node_modules/cesium')
    }
  },
  optimizeDeps: {
    include: [
      'cesium',
      'resium'
    ]
  }
});