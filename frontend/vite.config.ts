import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Evita CORS en desarrollo: el backend corre en 8000.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
// `test` es una propiedad de Vitest; se declara aquí para no arrastrar
// `vitest/config` en el build de Vite.
// @ts-expect-error -- configuración extendida por Vitest
test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
