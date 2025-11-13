import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createTheme, ThemeProvider } from '@mui/material/styles';
import './index.css'
import App from './App.jsx'


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

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <App />
    </ThemeProvider>
  </StrictMode>,
)
