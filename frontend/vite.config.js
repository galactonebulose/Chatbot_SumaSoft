import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://localhost:8001'
const BACKEND_WS_URL = BACKEND_URL.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/chat/ws': {
        target: BACKEND_WS_URL,
        ws: true,
      },
      '/chat': {
        target: BACKEND_URL,
      },
      '/tool': {
        target: BACKEND_URL,
      },
      '/resource': {
        target: BACKEND_URL,
      },
      '/feedback': {
        target: BACKEND_URL,
      },
      '/user': {
        target: BACKEND_URL,
      },
      '/api': {
        target: BACKEND_URL,
      },
    }
  }
})
