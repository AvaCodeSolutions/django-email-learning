import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { useMediaQuery } from '@mui/material';
import MenuBar from '../components/MenuBar';

vi.mock('../render.jsx');

// In jsdom, window.matchMedia always reports no matches, which makes MUI's
// useMediaQuery return false.  That causes the nav Drawer to use the
// "temporary" variant (closed by default), so nav links are unmounted.
// Mocking useMediaQuery to return true simulates an md+ screen, so the
// Drawer is rendered as "permanent" and links are always in the DOM.
vi.mock('@mui/material', async () => ({
  ...(await vi.importActual('@mui/material')),
  useMediaQuery: vi.fn(() => true),
}));

// ---------------------------------------------------------------------------
// Default fetch mock — returns empty organizations and healthy job status.
// Individual tests override this with vi.fn().mockImplementation when needed.
// ---------------------------------------------------------------------------
function setupDefaultFetch() {
  global.fetch.mockImplementation((url) => {
    if (url.includes('/status/jobs/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ jobs: { deliver_contents: null } }),
      });
    }
    if (url.includes('/organizations/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ organizations: [] }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

const defaultProps = {
  activeOrganizationId: null,
  changeOrganizationCallback: vi.fn(),
  showOrganizationSwitcher: true,
  drawerWidth: 250,
  miniDrawerWidth: 64,
};

describe('MenuBar', () => {
  beforeEach(() => {
    setupDefaultFetch();
    defaultProps.changeOrganizationCallback.mockClear();
  });

  it('renders the logo image', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    const logos = screen.getAllByAltText('Logo');
    expect(logos.length).toBeGreaterThan(0);
  });

  it('always shows the Courses navigation link', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(screen.getByText('Courses')).toBeInTheDocument();
  });

  it('does not show Organizations link for a regular user', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(screen.queryByText('Organizations')).not.toBeInTheDocument();
  });

  it('does not show Learners link for a regular user', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(screen.queryByText('Learners')).not.toBeInTheDocument();
  });

  it('shows Organizations link for organization admin', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isOrganizationAdmin: true },
    });
    expect(screen.getByText('Organizations')).toBeInTheDocument();
  });

  it('shows Learners link for organization admin', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isOrganizationAdmin: true },
    });
    expect(screen.getByText('Learners')).toBeInTheDocument();
  });

  it('shows Learners link for instructor', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isInstructor: true },
    });
    expect(screen.getByText('Learners')).toBeInTheDocument();
  });

  it('shows Learners link for platform admin', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isPlatformAdmin: true },
    });
    expect(screen.getByText('Learners')).toBeInTheDocument();
  });

  it('shows Settings section label for platform admin', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isPlatformAdmin: true },
    });
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows API Keys immediately without needing a click for platform admin', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isPlatformAdmin: true },
    });
    expect(screen.getByText('API Keys')).toBeInTheDocument();
  });

  it('does not show Settings section for non-platform-admin', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
    expect(screen.queryByText('API Keys')).not.toBeInTheDocument();
  });

  it('shows Administration section label for org admin', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isOrganizationAdmin: true },
    });
    expect(screen.getByText('Administration')).toBeInTheDocument();
  });

  it('does not show Administration section label for regular user', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(screen.queryByText('Administration')).not.toBeInTheDocument();
  });

  it('always shows Platform section label', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(screen.getByText('Platform')).toBeInTheDocument();
  });

  it('populates the organization selector after fetch', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/organizations/')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ organizations: [{ id: '1', name: 'Acme Corp' }] }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ jobs: { deliver_contents: null } }),
      });
    });

    renderWithProviders(<MenuBar {...defaultProps} activeOrganizationId="1" />);

    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument());
  });

  it('hides the organization selector when showOrganizationSwitcher is false', () => {
    renderWithProviders(<MenuBar {...defaultProps} showOrganizationSwitcher={false} />);
    // No combobox / select for org switching
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('does not render any navbar custom component slots by default', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(document.querySelector('my-notifications')).not.toBeInTheDocument();
  });

  it('renders navbar custom components from appContext', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: {
        navbarCustomComponents: [
          { slot: 'notifications', html: '<my-notifications></my-notifications>' },
          { slot: 'search', html: '<my-search></my-search>' },
        ],
      },
    });
    expect(document.querySelector('my-notifications')).toBeInTheDocument();
    expect(document.querySelector('my-search')).toBeInTheDocument();
  });

  it('also renders navbar custom components inside the sidebar, for mobile', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: {
        navbarCustomComponents: [{ slot: 'notifications', html: '<my-notifications></my-notifications>' }],
      },
    });
    // Once in the AppBar (desktop) slot, once in the sidebar (mobile) slot.
    expect(document.querySelectorAll('my-notifications')).toHaveLength(2);
  });

  it('renders navbar custom components above the sidebar custom component slot', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: {
        navbarCustomComponents: [{ slot: 'notifications', html: '<my-notifications></my-notifications>' }],
        sidebarCustomComponent: { componentTag: '<my-widget></my-widget>' },
      },
    });
    const notifications = document.querySelectorAll('my-notifications');
    const widget = document.querySelector('my-widget');
    expect(widget).toBeInTheDocument();
    // The sidebar copy of the navbar component must precede the sidebar widget in DOM order.
    const sidebarNotifications = notifications[notifications.length - 1];
    expect(
      sidebarNotifications.compareDocumentPosition(widget) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  it('does not render the sidebar custom components wrapper when neither slot has content', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(document.querySelector('my-notifications')).not.toBeInTheDocument();
    expect(document.querySelector('my-widget')).not.toBeInTheDocument();
  });

  it('shows content delivery chip for platform admin when job status is present', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/status/jobs/')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              jobs: {
                deliver_contents: {
                  job_health_status: 'healthy',
                  last_execution_started_at: null,
                },
              },
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ organizations: [] }),
      });
    });

    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isPlatformAdmin: true },
    });

    await waitFor(() =>
      expect(screen.getByText('Content delivery')).toBeInTheDocument()
    );
  });

  it('does not request job status for non-platform-admins', async () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { isPlatformAdmin: false },
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(global.fetch.mock.calls.some(([url]) => String(url).includes('/status/jobs/'))).toBe(false);
    expect(screen.queryByText('Content delivery')).not.toBeInTheDocument();
  });

});

describe('MenuBar mini drawer (md up to xl)', () => {
  beforeEach(() => {
    setupDefaultFetch();
    // Match the md breakpoint but not xl (MUI's default xl is 1536px).
    useMediaQuery.mockImplementation((query) => !String(query).includes('1536'));
  });

  afterEach(() => {
    useMediaQuery.mockImplementation(() => true);
  });

  function getPermanentDrawerPaper() {
    return document.querySelector('.MuiDrawer-docked .MuiDrawer-paper');
  }

  it('renders a permanent drawer at the mini width', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(getPermanentDrawerPaper()).toHaveStyle({ width: '64px' });
  });

  it('shows nav items as icons labelled through aria-label instead of text', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    const drawer = within(getPermanentDrawerPaper());
    expect(drawer.getByLabelText('Courses')).toBeInTheDocument();
    expect(drawer.queryByText('Courses')).not.toBeInTheDocument();
  });

  it('hides section labels and the organization selector', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    const drawer = within(getPermanentDrawerPaper());
    expect(drawer.queryByText('Platform')).not.toBeInTheDocument();
    expect(drawer.queryByLabelText('Select organization')).not.toBeInTheDocument();
  });

  it('shows the logo mark without the text lockup', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    const logo = within(getPermanentDrawerPaper()).getByAltText('Logo');
    expect(logo.getAttribute('src')).toMatch(/logo\.png/);
  });

  it('uses the custom mark from the logo settings when set', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { customLogo: { verticalLight: '/vertical-light.png', markLight: '/mark-light.png' } },
    });
    const logo = within(getPermanentDrawerPaper()).getByAltText('Logo');
    expect(logo).toHaveAttribute('src', '/mark-light.png');
  });

  it('falls back to the custom vertical lockup when no custom mark is set', () => {
    renderWithProviders(<MenuBar {...defaultProps} />, {
      appContext: { customLogo: { verticalLight: '/vertical-light.png' } },
    });
    const logo = within(getPermanentDrawerPaper()).getByAltText('Logo');
    expect(logo).toHaveAttribute('src', '/vertical-light.png');
  });

  it('expands to the full drawer from the arrow on the mini drawer', async () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    fireEvent.click(within(getPermanentDrawerPaper()).getByRole('button', { name: 'Expand menu' }));
    await waitFor(() => expect(screen.getByText('Courses')).toBeInTheDocument());
    expect(screen.getByLabelText('Select organization')).toBeInTheDocument();
  });

  it('collapses the expanded drawer from its arrow', async () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    fireEvent.click(within(getPermanentDrawerPaper()).getByRole('button', { name: 'Expand menu' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Collapse menu' }));
    await waitFor(() => expect(screen.queryByText('Courses')).not.toBeInTheDocument());
  });
});

describe('MenuBar full drawer (xl up)', () => {
  beforeEach(() => {
    setupDefaultFetch();
    useMediaQuery.mockImplementation(() => true);
  });

  it('renders a permanent drawer at the full width', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(document.querySelector('.MuiDrawer-docked .MuiDrawer-paper')).toHaveStyle({ width: '250px' });
  });

  it('does not show the expand arrow', () => {
    renderWithProviders(<MenuBar {...defaultProps} />);
    expect(screen.queryByRole('button', { name: 'Expand menu' })).not.toBeInTheDocument();
  });
});
