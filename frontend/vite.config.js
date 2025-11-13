import { defineConfig } from 'vite'
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';


import react from '@vitejs/plugin-react'

const __dirname = dirname(fileURLToPath(import.meta.url));




// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  appType: 'mpa',
  base: "/static/",
  server: {
    port: 3000,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        courses: resolve(__dirname, 'courses/index.html'),
        organizations: resolve(__dirname, 'organizations/index.html'),
        users: resolve(__dirname, 'users/index.html')
      }
    },
    manifest: 'manifest.json',
    outDir: resolve(__dirname, '../dist'),
    emptyOutDir: true,
    sourcemap: true,
  }
})
