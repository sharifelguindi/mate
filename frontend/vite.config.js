import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  root: resolve(__dirname, 'src'),
  base: '/static/vite/',  // Updated to match Django's static_url_prefix
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
      disableGlobbing: false,
    },
  },
  build: {
    outDir: resolve(__dirname, '../staticfiles/vite'),
    emptyOutDir: true,
    manifest: 'manifest.json',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/main.js'),
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
})
