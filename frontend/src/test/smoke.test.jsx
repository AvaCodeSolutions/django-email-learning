import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders, useAppContext } from './test-utils';

// ---------------------------------------------------------------------------
// Trivial smoke tests — verify the test runner and providers are wired up.
// ---------------------------------------------------------------------------

describe('test infrastructure', () => {
  it('renders a plain element', () => {
    renderWithProviders(<p>Hello Vitest</p>);
    expect(screen.getByText('Hello Vitest')).toBeInTheDocument();
  });

  it('exposes the default app context direction', () => {
    let capturedDirection;
    function Probe() {
      capturedDirection = useAppContext().direction;
      return null;
    }
    renderWithProviders(<Probe />);
    expect(capturedDirection).toBe('ltr');
  });

  it('localStorage mock is in place', () => {
    localStorage.setItem('theme', 'dark');
    expect(localStorage.getItem('theme')).toBe('dark');
  });

  it('fetch mock is in place', async () => {
    const res = await fetch('/api/test');
    expect(res.ok).toBe(true);
  });
});
