import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Escucha en todas las interfaces de red (0.0.0.0)
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true, // CLAVE: Permite a Docker detectar los cambios de archivos desde el host
    },
    hmr: {
      clientPort: 5173, // CLAVE: Garantiza que el navegador conecte el WebSocket a localhost:5173
    },
  },
})