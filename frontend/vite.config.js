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
  esbuild: {
    sourcemap: false,
  },
  build: {
    rollupOptions: {
      input: {
        courses: resolve(__dirname, 'platform/courses/index.html'),
        course: resolve(__dirname, 'platform/course/index.html'),
        organizations: resolve(__dirname, 'platform/organizations/index.html'),
        learners: resolve(__dirname, 'platform/learners/index.html'),
        settings_api_keys: resolve(__dirname, 'platform/settings_api_keys/index.html'),
        organization: resolve(__dirname, 'public/organization/index.html'),
        quiz_public: resolve(__dirname, "personalised/quiz_public/index.html"),
        command_result: resolve(__dirname, "personalised/command_result/index.html"),
      }
    },
    manifest: 'manifest.json',
    outDir: resolve(__dirname, '../dist'),
    emptyOutDir: true,
    sourcemap: true,
  },
  optimizeDeps: {
    include: ['esm-dep > cjs-dep'],
  },
})
