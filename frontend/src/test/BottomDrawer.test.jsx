import { describe, it, expect } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import BottomDrawer from '../components/BottomDrawer';

// vite/modulepreload-polyfill is mocked globally in setup.js

describe('BottomDrawer', () => {
  it('renders children inside the drawer when it is open', () => {
    renderWithProviders(
      <BottomDrawer icon={<span>icon</span>}>
        <p>Filter options</p>
      </BottomDrawer>
    );
    // Drawer children are only mounted after the FAB is clicked
    fireEvent.click(screen.getByRole('button', { name: /filter list/i }));
    expect(screen.getByText('Filter options')).toBeInTheDocument();
  });

  it('renders the FAB trigger button', () => {
    renderWithProviders(
      <BottomDrawer icon={<span>icon</span>}>
        <p>Content</p>
      </BottomDrawer>
    );
    expect(screen.getByRole('button', { name: /filter list/i })).toBeInTheDocument();
  });

  it('clicking the FAB opens the drawer (content accessible)', () => {
    renderWithProviders(
      <BottomDrawer icon={<span>icon</span>}>
        <p>Drawer content</p>
      </BottomDrawer>
    );
    fireEvent.click(screen.getByRole('button', { name: /filter list/i }));
    expect(screen.getByText('Drawer content')).toBeInTheDocument();
  });

  it('accepts any icon element', () => {
    const { container } = renderWithProviders(
      <BottomDrawer icon={<span data-testid="custom-icon">★</span>}>
        <p>Content</p>
      </BottomDrawer>
    );
    expect(container.querySelector('[data-testid="custom-icon"]')).toBeInTheDocument();
  });

  it('renders multiple children inside the drawer when open', () => {
    renderWithProviders(
      <BottomDrawer icon={<span>icon</span>}>
        <p>Child One</p>
        <p>Child Two</p>
      </BottomDrawer>
    );
    fireEvent.click(screen.getByRole('button', { name: /filter list/i }));
    expect(screen.getByText('Child One')).toBeInTheDocument();
    expect(screen.getByText('Child Two')).toBeInTheDocument();
  });
});
