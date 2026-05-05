import '@testing-library/jest-dom';

// Mock window.matchMedia (required by MUI responsive hooks)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: vi.fn((key) => store[key] ?? null),
    setItem: vi.fn((key, value) => { store[key] = String(value); }),
    removeItem: vi.fn((key) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock global fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
  })
);

// Mock document.cookie for getCookie utility
Object.defineProperty(document, 'cookie', {
  writable: true,
  value: '',
});

// Mock static asset imports (logo images used in MenuBar)
vi.mock('../assets/logo-h-light.png', () => ({ default: 'logo-h-light.png' }));
vi.mock('../assets/logo-h-dark.png', () => ({ default: 'logo-h-dark.png' }));
vi.mock('../assets/logo-v-light.png', () => ({ default: 'logo-v-light.png' }));
vi.mock('../assets/logo-v-dark.png', () => ({ default: 'logo-v-dark.png' }));

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
  localStorageMock.clear();
  global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
});
