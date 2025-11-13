import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createTheme, ThemeProvider } from '@mui/material/styles';
import './index.css'


const theme = createTheme({
  palette: {
    primary: {
      main: '#00d5be',
    },
    secondary: {
      main: '#7c86ff',
    },
  },
  components: {
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
