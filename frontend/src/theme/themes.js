import { createTheme } from '@mui/material/styles';
import { blueGrey } from '@mui/material/colors';
import { Margin, Padding } from '@mui/icons-material';

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
    primary: {
      main: '#00d5be',
    },
    secondary: {
      main: '#7c86ff',
      text: '#313ba9ff',
    },
    errorText: {
      main: '#a93e6bff',
    },
    grey: blueGrey,
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
    primary: {
      main: '#00d5be',
    },
    secondary: {
      main: '#7c86ff',
      text: '#b8bdfaff',
    },
    errorText: {
      main: '#ff6b9d',
    },
    grey: blueGrey,
};

const lightTheme = createTheme({
  palette: lightPalette,
  components: {
    ...defaultOptions.components
  },
});

const darkTheme = createTheme({
  palette: darkPalette,
  components: {
    ...defaultOptions.components
  },
});


export { lightTheme, darkTheme };
