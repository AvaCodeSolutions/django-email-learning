import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
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
});
