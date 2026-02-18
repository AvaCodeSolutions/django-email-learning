import { createTheme } from '@mui/material/styles';
import { blueGrey, indigo, teal, lightGreen, amber, red } from '@mui/material/colors';
import { Margin, Padding } from '@mui/icons-material';
import { Paper } from '@mui/material';

const defaultOptions = {
  components: {
    MuiTable: {
      defaultProps: {
        size: 'small',
      },
    },
    MuiSwitch: {
      defaultProps: {
        size: 'small',
      },
    },
    MuiRadio: {
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
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          backgroundColor: 'transparent',
        },
        bar: ({ theme }) => ({
          background: `linear-gradient(90deg, ${theme.palette.secondary.main} 0%, ${theme.palette.primary.main} 70%)`,
        }),
      },
    },
    MuiTypography: {
      styleOverrides: {
        h1: {
          fontSize: '2rem',
          fontWeight: 600,
          lineHeight: 1.2,
          marginBottom: '1rem',
        },
        h2: {
          fontSize: '1.5rem',
          fontWeight: 600,
          lineHeight: 1.3,
          marginBottom: '0.875rem',
        },
        h3: {
          fontSize: '1.25rem',
          fontWeight: 600,
          lineHeight: 1.4,
          marginBottom: '0.75rem',
        },
      },
    },
    MuiIconButton: {
      defaultProps: {
        size: 'small',
      },
      styleOverrides: {
        root: ({theme}) => ({
          color: 'inherit',
          padding: '3px',
          margin: '2px',
          '*': {
            fontSize: '1.2rem',
          },
          '&:hover': {
            backgroundColor: theme.palette.secondary.dark,
            color: 'white',
          },
          transition: 'color 0.3s, background-color 0.3s',
        }),
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiButton: {
      defaultProps: {
        size: 'small',
      },
      variants: [
        {
            props: { variant: 'contained' },
            style: ({ theme }) => ({
                textTransform: 'none',
                boxShadow: 'none',
                borderRadius: 8,
                color: '#ffffff',
                backgroundColor: theme.palette.secondary.dark,
                '&:hover': {
                    backgroundColor: theme.palette.primary.dark,
                },
            }),
        },
        {
            props: { variant: 'text' },
            style: ({ theme }) => ({
                textTransform: 'none',
                color: theme.palette.secondary.text,
                borderRadius: 8,
            }),
        },
        {
            props: { variant: 'outlined' },
            style: ({ theme }) => ({
                textTransform: 'none',
                borderRadius: 8,
                color: theme.palette.secondary.text,
            }),
        }
    ]
    },
    MuiDrawer: {
      styleOverrides: {
        backdrop: {
          backgroundColor: '#fff'
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: ({ theme }) => ({
          backgroundColor: theme.palette.background.nav,
          '* th': {
            fontWeight: 'bold',
            paddingTop: '10px',
            paddingBottom: '10px',
          },
        }),
      },
    },
  },
}

const lightPalette = {
    mode: 'light',
    text: {
      primary: '#000000de',
      secondary: '#00000099',
    },
    background: {
      main: '#f8f8fa',
      dark: '#f2f4f5ff',
      nav: '#ffffffff',
    },
    border: {
      main: '#ccccccff',
    },
    errorText: {
      main: '#a93e6bff',
    },
    secondary: {
      main: '#7c86ff',
      text: 'rgb(91, 103, 243)',
    },
    successChipBg: teal[50],
    warningChipBg: amber[50],
    criticalChipBg: red[50],
};

const darkPalette = {
    mode: 'dark',
    text: {
      primary: '#ffffffde',
      secondary: '#ffffff99',
    },
    background: {
      main: '#383539',
      dark: '#232324ff',
      nav: '#2c2c2eff',
    },
    border: {
      main: '#555555ff',
    },
    errorText: {
      main: '#ff6b9d',
    },
    secondary: {
      main: '#7c86ff',
      text: 'rgb(184, 190, 255)',
    },
    successChipBg: teal[700],
    warningChipBg: amber[700],
    criticalChipBg: red[700],
};

const commonPalette = {
   primary: {
      main: '#00d5be',
    },
    grey: blueGrey,
    teal: teal,
    indigo: indigo,
    lightGreen: lightGreen,
    amber: amber,
    red: red,
}

const lightTheme = createTheme({
  palette: {...lightPalette, ...commonPalette},
  components: {
    ...defaultOptions.components
  },
});

const darkTheme = createTheme({
  palette: {...darkPalette, ...commonPalette},
  components: {
    ...defaultOptions.components
  },
});


export { lightTheme, darkTheme };
