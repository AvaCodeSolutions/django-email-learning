import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { LinearProgress } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import { lightTheme, darkTheme } from '../theme/themes';

const barStyle = (theme, props = {}) => {
  const { container } = render(
    <ThemeProvider theme={theme}>
      <LinearProgress variant="determinate" value={50} {...props} />
    </ThemeProvider>
  );
  return getComputedStyle(container.querySelector('.MuiLinearProgress-bar'));
};

describe('LinearProgress theme', () => {
  it.each([['light', lightTheme], ['dark', darkTheme]])('fills the bar with the plain primary colour in the %s theme', (_, theme) => {
    const style = barStyle(theme);
    expect(style.getPropertyValue('background-image')).not.toMatch(/gradient/);
    expect(style.getPropertyValue('background')).not.toMatch(/gradient/);
    expect(style.getPropertyValue('background-color')).not.toBe('');
    expect(style.getPropertyValue('background-color')).toBe(barStyle(theme, { color: 'primary' }).getPropertyValue('background-color'));
  });

  it('lets a color prop pick the bar colour', () => {
    expect(barStyle(lightTheme, { color: 'success' }).getPropertyValue('background-color'))
      .not.toBe(barStyle(lightTheme).getPropertyValue('background-color'));
  });
});
