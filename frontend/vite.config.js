import { defineConfig } from 'vite'
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';


import react from '@vitejs/plugin-react-swc';

const __dirname = dirname(fileURLToPath(import.meta.url));




// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  css: { transformer: 'lightningcss' },
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
        platform_organization: resolve(__dirname, 'platform/organization/index.html'),
        learners: resolve(__dirname, 'platform/learners/index.html'),
        settings_api_keys: resolve(__dirname, 'platform/settings_api_keys/index.html'),
        organization: resolve(__dirname, 'public/organization/index.html'),
        quiz_public: resolve(__dirname, "personalised/quiz_public/index.html"),
        certificate: resolve(__dirname, "personalised/certificate/index.html"),
        certtificate_form: resolve(__dirname, "personalised/certificate_form/index.html"),
        command_result: resolve(__dirname, "personalised/command_result/index.html"),
      }
    },
    manifest: 'manifest.json',
    outDir: resolve(__dirname, '../dist'),
    emptyOutDir: true,
    sourcemap: true,
    optimizeDeps: {
      include: [
      'react',
      'react-dom',
      '@mui/material',
      '@mui/icons-material',
      '@mui/lab',
      '@mui/x-charts',
      '@emotion/react',
      '@emotion/styled',
    ], // Force pre-bundling
      entries: ['./platform/courses/Courses.jsx', './platform/course/Course.jsx', './platform/organizations/Organizations.jsx', './platform/learners/Learners.jsx', './platform/settings_api_keys/SettingsApiKeys.jsx', './public/organization/Organization.jsx', './personalised/quiz_public/QuizPublic.jsx', './personalised/command_result/CommandResult.jsx'],
  },
  }
})
