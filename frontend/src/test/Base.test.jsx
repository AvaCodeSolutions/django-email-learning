import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import Base from '../components/Base';

vi.mock('../render.jsx');

// MenuBar fetches job status and organizations on mount.
// Provide benign responses so state updates don't throw.
function setupFetch() {
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

describe('Base', () => {
  beforeEach(() => {
    setupFetch();
  });

  it('renders children', () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
        <p>Page content</p>
      </Base>
    );
    expect(screen.getByText('Page content')).toBeInTheDocument();
  });

  it('renders a single breadcrumb as the active (non-linked) crumb', () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Dashboard', href: '/dashboard' }]}>
        <div />
      </Base>
    );
    // The last crumb is rendered as Typography, not a link
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders intermediate breadcrumbs as links', () => {
    renderWithProviders(
      <Base
        breadCrumbList={[
          { label: 'Home', href: '/' },
          { label: 'Courses', href: '/courses' },
          { label: 'Module 1', href: '/courses/1' },
        ]}
      >
        <div />
      </Base>
    );
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Courses' })).toHaveAttribute('href', '/courses');
    // Last crumb is plain text, not a link
    expect(screen.getByText('Module 1')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Module 1' })).not.toBeInTheDocument();
  });

  it('renders the AvaCode Solutions footer link', () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
        <div />
      </Base>
    );
    expect(screen.getByRole('link', { name: /avacode solutions/i })).toBeInTheDocument();
  });

  it('calls organizationIdRefreshCallback when organization changes', async () => {
    const onOrgRefresh = vi.fn();
    renderWithProviders(
      <Base
        breadCrumbList={[{ label: 'Home', href: '/' }]}
        organizationIdRefreshCallback={onOrgRefresh}
      >
        <div />
      </Base>
    );
    // Called immediately on mount with null (initial state)
    await waitFor(() => expect(onOrgRefresh).toHaveBeenCalledWith(null));
  });

  it('renders without BottomDrawer when bottomDrawerParams is omitted', () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
        <div />
      </Base>
    );
    // FAB for BottomDrawer must not be present
    expect(screen.queryByRole('button', { name: /filter list/i })).not.toBeInTheDocument();
  });

  it('exposes window.DialogAPI.show to open a dialog with arbitrary content', () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
        <div />
      </Base>
    );
    expect(screen.queryByText('Hello from DialogAPI')).not.toBeInTheDocument();
    act(() => window.DialogAPI.show(<p>Hello from DialogAPI</p>));
    expect(screen.getByText('Hello from DialogAPI')).toBeInTheDocument();
  });

  it('closes the dialog via window.DialogAPI.close', async () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
        <div />
      </Base>
    );
    act(() => window.DialogAPI.show(<p>Hello from DialogAPI</p>));
    expect(screen.getByText('Hello from DialogAPI')).toBeInTheDocument();
    act(() => window.DialogAPI.close());
    await waitFor(() => expect(screen.queryByText('Hello from DialogAPI')).not.toBeInTheDocument());
  });

  it('does not close the dialog on backdrop click by default', () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
        <div />
      </Base>
    );
    act(() => window.DialogAPI.show(<p>Hello from DialogAPI</p>));
    // eslint-disable-next-line testing-library/no-node-access
    act(() => document.querySelector('.MuiBackdrop-root').click());
    expect(screen.getByText('Hello from DialogAPI')).toBeInTheDocument();
  });

  it('closes the dialog on backdrop click after setCloseOnBackdropClick(true)', async () => {
    renderWithProviders(
      <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
        <div />
      </Base>
    );
    act(() => window.DialogAPI.setCloseOnBackdropClick(true));
    expect(window.DialogAPI.getDialogBackdropClickSetting()).toBe(true);
    act(() => window.DialogAPI.show(<p>Hello from DialogAPI</p>));
    // eslint-disable-next-line testing-library/no-node-access
    act(() => document.querySelector('.MuiBackdrop-root').click());
    await waitFor(() => expect(screen.queryByText('Hello from DialogAPI')).not.toBeInTheDocument());
  });

  describe('switching organizations', () => {
    let originalLocation;

    beforeEach(() => {
      originalLocation = window.location;
      Object.defineProperty(window, 'location', {
        writable: true,
        value: {
          href: '',
          pathname: originalLocation.pathname,
          origin: originalLocation.origin,
          reload: vi.fn(),
        },
      });
      global.fetch.mockImplementation((url) => {
        if (url.includes('/status/jobs/')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ jobs: { deliver_contents: null } }) });
        }
        if (url.includes('/organizations/')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                organizations: [
                  { id: 1, name: 'Org One' },
                  { id: 2, name: 'Org Two' },
                ],
              }),
          });
        }
        if (url.includes('/session')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ status: 'ok' }) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
    });

    afterEach(() => {
      Object.defineProperty(window, 'location', { writable: true, value: originalLocation });
    });

    it('reloads the page after picking a different organization', async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
          <div />
        </Base>
      );

      // The nav drawer is "temporary" (closed, content unmounted) at jsdom's
      // default viewport size, matching a real small-screen user - open it
      // via the hamburger button before the organization switcher is queryable.
      await user.click(await screen.findByTestId('MenuIcon'));
      await user.click(await screen.findByLabelText('Select organization'));
      await user.click(await screen.findByRole('option', { name: 'Org Two' }));

      await waitFor(() => expect(window.location.reload).toHaveBeenCalled());
    });

    it('does not reload on initial mount when an organization is restored from localStorage', async () => {
      const user = userEvent.setup();
      localStorage.setItem('activeOrganizationId', '1');
      renderWithProviders(
        <Base breadCrumbList={[{ label: 'Home', href: '/' }]}>
          <div />
        </Base>
      );

      await user.click(await screen.findByTestId('MenuIcon'));
      await screen.findByLabelText('Select organization');
      // Give any stray effects a tick to run before asserting nothing navigated.
      await waitFor(() => expect(global.fetch).toHaveBeenCalled());
      expect(window.location.reload).not.toHaveBeenCalled();
    });
  });
});
