import { render } from '@testing-library/react';
import { createContext, useContext } from 'react';
import { ThemeContextProvider } from '../theme/ThemeContext';
import { lightTheme } from '../theme/themes';

// ---------------------------------------------------------------------------
// Default mock values for AppContext (mirrors the shape used by render.jsx)
// ---------------------------------------------------------------------------
export const defaultAppContext = {
  direction: 'ltr',
  apiBaseUrl: '/api',
  platformBaseUrl: '/platform',
  localeMessages: {
    organizations: 'Organizations',
    course_management: 'Courses',
    learners: 'Learners',
    api_keys: 'API Keys',
    settings: 'Settings',
    content_delivery_tooltip: 'Content delivery job status',
    content_delivery_job: 'Content delivery',
    last_run: 'Last run:',
    never_run: 'Never run',
    upload_button_label: 'Upload',
    uploaded_image_alt: 'Uploaded image',
    remove_image: 'Remove',
  },
  isPlatformAdmin: false,
  isOrganizationAdmin: false,
  isInstructor: false,
  sidebarCustomComponent: null,
  customLogo: null,
};

// AppContext is re-created here so tests don't depend on render.jsx's
// createRoot side-effects.
export const AppContext = createContext(defaultAppContext);
export const useAppContext = () => useContext(AppContext);

// ---------------------------------------------------------------------------
// renderWithProviders — drop-in for @testing-library/react render with full
// theme + app context wrappers.
// ---------------------------------------------------------------------------
export function renderWithProviders(ui, { appContext = {}, theme = lightTheme, ...renderOptions } = {}) {
  const mergedCtx = { ...defaultAppContext, ...appContext };

  function Wrapper({ children }) {
    return (
      <AppContext.Provider value={mergedCtx}>
        <ThemeContextProvider initialTheme={theme}>
          {children}
        </ThemeContextProvider>
      </AppContext.Provider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
