import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { lightTheme, darkTheme } from '../theme/themes';
import ThemeSwitcher from '../components/ThemeSwitcher';

vi.mock('../render.jsx');

describe('ThemeSwitcher', () => {
  it('shows "Dark" button when rendered with the light theme', () => {
    renderWithProviders(<ThemeSwitcher />, { theme: lightTheme });
    expect(screen.getByText('Dark')).toBeInTheDocument();
  });

  it('shows "Light" button when rendered with the dark theme', () => {
    renderWithProviders(<ThemeSwitcher />, { theme: darkTheme });
    expect(screen.getByText('Light')).toBeInTheDocument();
  });

  it('stores "dark" in localStorage when switching from light theme', () => {
    renderWithProviders(<ThemeSwitcher />, { theme: lightTheme });
    fireEvent.click(screen.getByRole('button'));
    expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark');
  });

  it('stores "light" in localStorage when switching from dark theme', () => {
    renderWithProviders(<ThemeSwitcher />, { theme: darkTheme });
    fireEvent.click(screen.getByRole('button'));
    expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'light');
  });

  it('toggles the button label after click', () => {
    renderWithProviders(<ThemeSwitcher />, { theme: lightTheme });
    expect(screen.getByText('Dark')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Light')).toBeInTheDocument();
  });

  it('shows the Dark mode icon in light theme', () => {
    const { container } = renderWithProviders(<ThemeSwitcher />, { theme: lightTheme });
    // DarkModeRoundedIcon is rendered as an SVG inside the button
    expect(container.querySelector('button svg')).toBeInTheDocument();
  });
});
