import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API is served by the same FastAPI process in production, so the app talks
// to a relative path. In dev, Vite proxies /api to the local uvicorn server —
// which means no CORS configuration is needed in either environment.
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/healthz': { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // the bundle is small; splitting react out keeps repeat visits cheap
    rollupOptions: {
      output: {
        manualChunks: { react: ['react', 'react-dom'] },
      },
    },
  },
})
