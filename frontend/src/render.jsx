import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { blueGrey } from '@mui/material/colors';
import './index.css'


const theme = createTheme({
  palette: {
    mode: 'light',
    background: {
      paper: '#ffffffff',
      default: '#f3f3f3',
    },
    primary: {
      main: '#00d5be',
    },
    secondary: {
      main: '#7c86ff',
    },
    errorText: {
      main: '#a93e6bff',
    },
    grey: blueGrey,
  },
  components: {
    defaultProps: {
      size: 'small',
    },
    MuiTable: {
      defaultProps: {
        size: 'small',
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
        size: 'small',
      },
    },
    MuiDrawer: {
      styleOverrides: {
        backdrop: {
          backgroundColor: '#fff'
        },
      },
    },
  },
});

function render({children}) {
    createRoot(document.getElementById('root')).render(
        <StrictMode>
            <ThemeProvider theme={theme}>
            {children}
            </ThemeProvider>
        </StrictMode>,
    )
}

export default render;
