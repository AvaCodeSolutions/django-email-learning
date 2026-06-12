import { Box, Button } from '@mui/material';
import { alpha } from '@mui/material/styles';
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded';
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded';
import { useThemeContext } from '../theme/ThemeContext';
import { lightTheme, darkTheme } from '../theme/themes';
import { useAppContext } from '../render.jsx';
import { use } from 'react';


const ThemeSwitcher = () => {
  const { currentTheme, changeTheme } = useThemeContext();
  const { direction } = useAppContext();

  const isLightTheme = currentTheme.palette.mode === 'light';

  const toggleTheme = () => {
    localStorage.setItem('theme', isLightTheme ? 'dark' : 'light');
    changeTheme(isLightTheme ? darkTheme : lightTheme);
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      <Button
        onClick={toggleTheme}
        size="small"
        aria-label={isLightTheme ? 'Switch to dark mode' : 'Switch to light mode'}
        startIcon={isLightTheme ? <DarkModeRoundedIcon fontSize="small" sx={{ml: direction === 'rtl' ? 1 : 0, mr: direction === 'rtl' ? 0 : 1}} /> : <LightModeRoundedIcon fontSize="small" sx={{ml: direction === 'rtl' ? 1 : 0, mr: direction === 'rtl' ? 0 : 1}} />}
        sx={(theme) => ({
          minWidth: 0,
          px: 1.25,
          py: 0.5,
          direction: direction,
          borderRadius: 2,
          border: `1px solid ${alpha(theme.palette.border.main, 0.4)}`,
          color: 'text.primary',
          backgroundColor: theme.palette.mode === 'light' ? 'rgba(124, 134, 255, 0.08)' : 'rgba(0, 0, 0, 0.35)',
          '&:hover': {
            backgroundColor: theme.palette.mode === 'light' ? 'rgba(124, 134, 255, 0.16)' : 'rgba(0, 0, 0, 0.5)',
            borderColor: theme.palette.primary.main,
          },
        })}
      >
        {isLightTheme ? 'Dark' : 'Light'}
      </Button>
    </Box>
  );
};

export default ThemeSwitcher;
