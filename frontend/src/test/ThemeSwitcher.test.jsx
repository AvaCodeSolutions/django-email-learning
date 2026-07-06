import { describe, it, expect } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { MenuList } from '@mui/material';
import { renderWithProviders } from './test-utils';
import { lightTheme, darkTheme } from '../theme/themes';
import ThemeSwitcher from '../components/ThemeSwitcher';

// ThemeSwitcher renders a MenuItem, which requires a MenuList/Menu ancestor
// (matching how it's actually used inside the sidebar's MenuList).
const renderThemeSwitcher = (theme) =>
  renderWithProviders(<MenuList><ThemeSwitcher /></MenuList>, { theme });

describe('ThemeSwitcher', () => {
  it('shows "Dark" menu item when rendered with the light theme', () => {
    renderThemeSwitcher(lightTheme);
    expect(screen.getByText('Dark')).toBeInTheDocument();
  });

  it('shows "Light" menu item when rendered with the dark theme', () => {
    renderThemeSwitcher(darkTheme);
    expect(screen.getByText('Light')).toBeInTheDocument();
  });

  it('stores "dark" in localStorage when switching from light theme', () => {
    renderThemeSwitcher(lightTheme);
    fireEvent.click(screen.getByRole('menuitem'));
    expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark');
  });

  it('stores "light" in localStorage when switching from dark theme', () => {
    renderThemeSwitcher(darkTheme);
    fireEvent.click(screen.getByRole('menuitem'));
    expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'light');
  });

  it('toggles the menu item label after click', () => {
    renderThemeSwitcher(lightTheme);
    expect(screen.getByText('Dark')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('menuitem'));
    expect(screen.getByText('Light')).toBeInTheDocument();
  });

  it('shows the Dark mode icon in light theme', () => {
    const { container } = renderThemeSwitcher(lightTheme);
    // DarkModeRoundedIcon is rendered as an SVG inside the menu item
    expect(container.querySelector('[role="menuitem"] svg')).toBeInTheDocument();
  });
});
