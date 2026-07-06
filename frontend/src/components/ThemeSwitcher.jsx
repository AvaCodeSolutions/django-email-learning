import { MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded';
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded';
import { useThemeContext } from '../theme/ThemeContext';
import { lightTheme, darkTheme } from '../theme/themes';


const ThemeSwitcher = () => {
  const { currentTheme, changeTheme } = useThemeContext();

  const isLightTheme = currentTheme.palette.mode === 'light';

  const toggleTheme = () => {
    localStorage.setItem('theme', isLightTheme ? 'dark' : 'light');
    changeTheme(isLightTheme ? darkTheme : lightTheme);
  };

  return (
    <MenuItem
      onClick={toggleTheme}
      aria-label={isLightTheme ? 'Switch to dark mode' : 'Switch to light mode'}
      sx={(theme) => ({
        py: '8px',
        px: '16px',
        '&:hover .MuiListItemIcon-root': { color: theme.palette.primary.main },
      })}
    >
      <ListItemIcon sx={(theme) => ({
        minWidth: 35,
        color: theme.palette.mode === 'dark' ? theme.palette.deepPurple[300] : theme.palette.deepPurple[500],
      })}>
        {isLightTheme ? <DarkModeRoundedIcon fontSize="small" /> : <LightModeRoundedIcon fontSize="small" />}
      </ListItemIcon>
      <ListItemText
        primary={isLightTheme ? 'Dark' : 'Light'}
        slotProps={{ primary: { fontSize: '0.95rem', fontWeight: 400 } }}
      />
    </MenuItem>
  );
};

export default ThemeSwitcher;
