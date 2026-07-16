import { MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import { alpha } from '@mui/material/styles';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
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
        // MUI's MenuItem ships its own `.MuiMenuItem-root .MuiListItemIcon-root { minWidth: 36px }`
        // rule with higher specificity than a plain sx on ListItemIcon, so it silently wins over
        // the 30px set below unless forced here (matches NavItem in MenuBar.jsx).
        '& .MuiListItemIcon-root': { minWidth: '30px !important' },
        '&:hover': { backgroundColor: theme.palette.primary.main },
        '&:hover .MuiListItemIcon-root': { color: '#ffffff' },
        '&:hover .MuiListItemText-primary': { color: '#ffffff' },
      })}
    >
      <ListItemIcon sx={(theme) => ({
        minWidth: 30,
        color: alpha(theme.palette.text.primary, 0.6),
        '& .MuiSvgIcon-root': { fontSize: '1.1rem' },
      })}>
        {isLightTheme ? <DarkModeOutlinedIcon fontSize="small" /> : <LightModeOutlinedIcon fontSize="small" />}
      </ListItemIcon>
      <ListItemText
        primary={isLightTheme ? 'Dark' : 'Light'}
        slotProps={{ primary: { fontSize: '0.9rem', fontWeight: 400 } }}
      />
    </MenuItem>
  );
};

export default ThemeSwitcher;
