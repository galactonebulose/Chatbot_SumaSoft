import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/chat/ws': {
        target: 'ws://localhost:8001',
        ws: true,
      },
      '/chat': {
        target: 'http://localhost:8001',
      },
      '/tool': {
        target: 'http://localhost:8001',
      },
      '/resource': {
        target: 'http://localhost:8001',
      },
      '/feedback': {
        target: 'http://localhost:8001',
      },
      '/user': {
        target: 'http://localhost:8001',
      },
      '/api': {
        target: 'http://localhost:8001',
      },
    }
  }
})
