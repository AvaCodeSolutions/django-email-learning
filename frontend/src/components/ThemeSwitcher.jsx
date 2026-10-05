import { MenuItem, ListItemIcon, ListItemText, Tooltip } from '@mui/material';
import { alpha } from '@mui/material/styles';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import { useThemeContext } from '../theme/ThemeContext';
import { lightTheme, darkTheme } from '../theme/themes';


const ThemeSwitcher = ({ mini = false, tooltipPlacement = 'right' }) => {
  const { currentTheme, changeTheme } = useThemeContext();

  const isLightTheme = currentTheme.palette.mode === 'light';

  const toggleTheme = () => {
    localStorage.setItem('theme', isLightTheme ? 'dark' : 'light');
    changeTheme(isLightTheme ? darkTheme : lightTheme);
  };

  const label = isLightTheme ? 'Dark' : 'Light';

  const item = (
    <MenuItem
      onClick={toggleTheme}
      aria-label={isLightTheme ? 'Switch to dark mode' : 'Switch to light mode'}
      sx={(theme) => ({
        py: mini ? '10px' : '8px',
        px: mini ? 0 : '16px',
        justifyContent: mini ? 'center' : undefined,
        // MUI's MenuItem ships its own `.MuiMenuItem-root .MuiListItemIcon-root { minWidth: 36px }`
        // rule with higher specificity than a plain sx on ListItemIcon, so it silently wins over
        // the 30px set below unless forced here (matches NavItem in MenuBar.jsx).
        '& .MuiListItemIcon-root': { minWidth: mini ? '0 !important' : '30px !important' },
        '&:hover': { backgroundColor: theme.palette.primary.main },
        '&:hover .MuiListItemIcon-root': { color: '#ffffff' },
        '&:hover .MuiListItemText-primary': { color: '#ffffff' },
      })}
    >
      <ListItemIcon sx={(theme) => ({
        minWidth: mini ? 0 : 30,
        color: alpha(theme.palette.text.primary, 0.6),
        '& .MuiSvgIcon-root': { fontSize: '1.1rem' },
      })}>
        {isLightTheme ? <DarkModeOutlinedIcon fontSize="small" /> : <LightModeOutlinedIcon fontSize="small" />}
      </ListItemIcon>
      {!mini && <ListItemText
        primary={label}
        slotProps={{ primary: { fontSize: '0.9rem', fontWeight: 400 } }}
      />}
    </MenuItem>
  );

  return mini ? <Tooltip title={label} placement={tooltipPlacement}>{item}</Tooltip> : item;
};

export default ThemeSwitcher;
