import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // MapLibre starts its worker as a module ({ type: 'module' }), so build workers as ES modules.
  worker: { format: 'es' },
  server: {
    // The API runs on its own port (uv run uvicorn ... --factory); the client calls /api.
    proxy: {
      '/api': { target: 'http://localhost:8000', rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
})
