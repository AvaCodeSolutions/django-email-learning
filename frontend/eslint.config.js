import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // `dist` is the vite build output; `htmlcov` and `coverage` are generated
  // coverage reports. None of it is source we control.
  globalIgnores(['dist', 'htmlcov', 'coverage']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      // `configs['recommended-latest']` is still the legacy eslintrc shape
      // (`plugins: ['react-hooks']`), which ESLint 10 flat config rejects
      // outright - the flat equivalents live under `configs.flat`.
      reactHooks.configs.flat['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],

      // eslint-plugin-react-hooks 7 turned the React Compiler diagnostics on by
      // default. They flag real patterns worth cleaning up, but the existing
      // components trip them in dozens of places, so they are warnings for now
      // rather than a wall that blocks every commit. Promote to 'error' as the
      // components get cleaned up.
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/static-components': 'warn',
      'react-hooks/immutability': 'warn',
      'react-hooks/refs': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',

      // Every page module exports both its component and a `render()` call, so
      // fast refresh granularity is a known trade-off in this codebase.
      'react-refresh/only-export-components': 'warn',
    },
  },
  {
    // Vitest runs these with `globals: true`, and the setup files reach for
    // node globals (`global`, `process`) as well.
    files: ['**/*.test.{js,jsx}', 'src/test/**/*.{js,jsx}', 'src/__mocks__/**/*.{js,jsx}'],
    languageOptions: {
      globals: {
        ...globals.vitest,
        ...globals.node,
      },
    },
  },
])
