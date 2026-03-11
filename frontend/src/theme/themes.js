import { createTheme, darken, alpha } from '@mui/material/styles';
import { blueGrey, indigo, teal, lightGreen, amber, red, pink, deepPurple } from '@mui/material/colors';

const statusPalette = {
  healthy: {
    bg: teal[50],
    border: teal[50],
    text: '#374151',
    icon: teal[800],
  },
  warning: {
    bg: amber[50],
    border: amber[100],
    text: '#374151',
    icon: amber[800],
  },
  critical: {
    bg: pink[50],
    border: pink[100],
    text: '#374151',
    icon: pink[800],
  },
};

const darkStatusPalette = {
  healthy: {
    bg: '#153532',
    border: '#1f4d49',
    text: '#e5e7eb',
    icon: teal[300],
  },
  warning: {
    bg: '#3f3218',
    border: '#5a4720',
    text: '#e5e7eb',
    icon: amber[300],
  },
  critical: {
    bg: '#45252a',
    border: '#64343c',
    text: '#e5e7eb',
    icon: red[300],
  },
};

const defaultOptions = {
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        a: ({ theme }) => ({
          color: theme.palette.mode === 'dark' ? theme.palette.primary.light : theme.palette.primary.main,
          textDecorationColor: theme.palette.mode === 'dark' ? theme.palette.primary.light : theme.palette.primary.main,
          transition: 'color 0.2s ease, text-decoration-color 0.2s ease',
          '&:hover': {
            color: theme.palette.mode === 'dark'
              ? alpha(theme.palette.primary.light, 0.85)
              : alpha(theme.palette.primary.main, 0.85),
            textDecorationColor: theme.palette.mode === 'dark'
              ? alpha(theme.palette.primary.light, 0.85)
              : alpha(theme.palette.primary.main, 0.85),
          },
        }),
      },
    },
    MuiLink: {
      styleOverrides: {
        root: ({ theme }) => ({
          color: theme.palette.mode === 'dark' ? theme.palette.primary.light : theme.palette.primary.main,
          textDecorationColor: theme.palette.mode === 'dark' ? theme.palette.primary.light : theme.palette.primary.main,
          transition: 'color 0.2s ease, text-decoration-color 0.2s ease',
          '&:hover': {
            color: theme.palette.mode === 'dark'
              ? alpha(theme.palette.primary.light, 0.85)
              : alpha(theme.palette.primary.main, 0.85),
            textDecorationColor: theme.palette.mode === 'dark'
              ? alpha(theme.palette.primary.light, 0.85)
              : alpha(theme.palette.primary.main, 0.85),
          },
        }),
      },
    },
    MuiTable: {
      defaultProps: {
        size: 'small',
        stickyHeader: true,
      },
      styleOverrides: {
        root: {
          width: '100%',
        },
      },
    },
    MuiTableContainer: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          border: `1px solid ${theme.palette.border.main}`,
        }),
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: ({ theme }) => ({
          '.MuiTableBody-root &': {
            '&:nth-of-type(odd)': {
              backgroundColor: theme.palette.mode === 'light' ? 'rgba(124, 134, 255, 0.05)' : 'rgba(255, 255, 255, 0.03)',
            },
            '&:hover': {
              backgroundColor: theme.palette.mode === 'light' ? 'rgba(124, 134, 255, 0.12)' : 'rgba(255, 255, 255, 0.08)',
            },
            '& td, & th': {
              paddingTop: 12,
              paddingBottom: 12,
            },
            '& .MuiIconButton-root': {
              borderRadius: 8,
              color: theme.palette.mode === 'light'
                ? darken(theme.palette.primary.dark, 0.15)
                : alpha(theme.palette.common.white, 0.9),
            },
            '& .MuiLink-root': {
              color: theme.palette.mode === 'light'
                ? undefined
                : `${alpha(theme.palette.secondary.light, 0.92)} !important`,
              '&:hover': {
                color: theme.palette.mode === 'light'
                  ? undefined
                  : `${alpha(theme.palette.secondary.light, 1)} !important`,
              },
            },
            '&:last-child td, &:last-child th': {
              border: 0,
            },
          },
        }),
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          lineHeight: 1.4,
        },
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
      styleOverrides: {
        root: {
          '& + .MuiTextField-root': {
            marginTop: 12,
          },
        },
      },
    },
    MuiFormControl: {
      styleOverrides: {
        root: {
          '& + .MuiFormControl-root': {
            marginTop: 12,
          },
        },
      },
    },
    MuiFormHelperText: {
      styleOverrides: {
        root: {
          marginTop: 4,
          lineHeight: 1.35,
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          backgroundColor: 'transparent',
        },
        bar: ({ theme }) => ({
          background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 70%)`,
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
    MuiTooltip: {
      styleOverrides: {
        tooltip: ({ theme }) => ({
          lineHeight: 1.6,
          color: theme.palette.text.primary,
          backgroundColor: theme.palette.mode === 'light'
            ? darken(theme.palette.background.main, 0.03)
            : darken(theme.palette.background.main, 0.12),
          border: `1px solid ${alpha(theme.palette.border.main, 0.8)}`,
        }),
        arrow: ({ theme }) => ({
          color: theme.palette.mode === 'light'
            ? darken(theme.palette.background.main, 0.03)
            : darken(theme.palette.background.main, 0.12),
        }),
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
          border: '1px solid transparent',
          '*': {
            fontSize: '1.2rem',
          },
          '&:hover': {
            backgroundColor: theme.palette.mode === 'light' ? 'rgba(124, 134, 255, 0.16)' : 'rgba(255, 255, 255, 0.12)',
            borderColor: theme.palette.primary.main,
          },
          transition: 'color 0.3s, background-color 0.3s, border-color 0.3s',
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
                backgroundColor: theme.palette.primary.dark,
                position: 'relative',
                isolation: 'isolate',
                zIndex: 0,
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  inset: 0,
                  borderRadius: 'inherit',
                  backgroundImage: theme.palette.mode === 'dark'
                    ? `linear-gradient(135deg, ${darken(theme.palette.secondary.main, 0.5)} 0%, ${theme.palette.primary.dark} 100%)`
                    : `linear-gradient(135deg, ${theme.palette.secondary.dark} 0%, ${theme.palette.primary.dark} 100%)`,
                  opacity: 0,
                  zIndex: -1,
                  transition: 'opacity 400ms ease-in-out',
                  pointerEvents: 'none',
                },
                '&:hover': {
                    boxShadow: theme.palette.mode === 'dark'
                      ? `0 0 0 1px ${alpha(theme.palette.primary.main, 0.7)}, 0 0 10px 1px ${alpha(theme.palette.primary.main, 0.3)}`
                      : `0 0 0 1px ${alpha(theme.palette.primary.main, 0.2)}, 0 0 18px 3px ${alpha(theme.palette.primary.main, 0.14)}`,
                    '&::before': {
                      opacity: 1,
                    },
                },
            }),
        },
        {
            props: { variant: 'text' },
            style: ({ theme }) => ({
                textTransform: 'none',
                color: theme.palette.primary.text,
                borderRadius: 8,
            transition: 'background-color 0.25s ease, color 0.25s ease',
            '&:hover': {
              backgroundColor: theme.palette.mode === 'light' ? 'rgba(124, 134, 255, 0.16)' : 'rgba(255, 255, 255, 0.12)',
            },
            }),
        },
        {
            props: { variant: 'outlined' },
            style: ({ theme }) => ({
                textTransform: 'none',
                borderRadius: 8,
                color: theme.palette.primary.text,
            borderColor: theme.palette.border.main,
            transition: 'background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease',
            '&:hover': {
              backgroundColor: theme.palette.mode === 'light' ? 'rgba(124, 134, 255, 0.16)' : 'rgba(255, 255, 255, 0.12)',
              borderColor: theme.palette.primary.main,
            },
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
            fontWeight: 400,
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
      box: '#ffffff',
      dark: '#f2f4f5ff',
      nav: '#ffffffff',
    },
    border: {
      main: '#ccccccff',
    },
    errorText: {
      main: '#a93e6bff',
    },
    primary: {
      main: '#7c86ff',
      text: 'rgb(91, 103, 243)',
    },
    status: statusPalette,
};

const darkPalette = {
    mode: 'dark',
    text: {
      primary: '#ffffffde',
      secondary: '#ffffff99',
    },
    background: {
      main: '#383539',
      box: '#2c2c2eff',
      dark: '#232324ff',
      nav: '#2c2c2eff',
    },
    border: {
      main: '#555555ff',
    },
    errorText: {
      main: '#ff6b9d',
    },
    primary: {
      main: '#7c86ff',
      text: 'rgb(184, 190, 255)',
    },
    status: darkStatusPalette,

};

const commonPalette = {
    secondary: {
      main: '#00d5be',
    },
    grey: blueGrey,
    teal: teal,
    indigo: indigo,
    lightGreen: lightGreen,
    amber: amber,
    red: red,
    deepPurple: deepPurple,
}

const baseTypography = {
  fontFamily: [
    'Inter',
    'Roboto',
    '-apple-system',
    'BlinkMacSystemFont',
    'Segoe UI',
    'Helvetica Neue',
    'Arial',
    'sans-serif',
  ].join(','),
  body1: {
    fontSize: '1rem',
    lineHeight: 1.55,
  },
  body2: {
    fontSize: '0.95rem',
    lineHeight: 1.5,
  },
  subtitle1: {
    fontSize: '0.95rem',
    fontWeight: 500,
    lineHeight: 1.45,
  },
  subtitle2: {
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: 1.4,
  },
  h4: {
    fontSize: '1.125rem',
    fontWeight: 600,
    lineHeight: 1.35,
  },
  h5: {
    fontSize: '1rem',
    fontWeight: 600,
    lineHeight: 1.4,
  },
  h6: {
    fontSize: '0.95rem',
    fontWeight: 600,
    lineHeight: 1.45,
  },
  button: {
    textTransform: 'none',
    fontWeight: 500,
  },
  caption: {
    fontSize: '0.8rem',
    lineHeight: 1.4,
  },
  overline: {
    fontSize: '0.75rem',
    fontWeight: 600,
    letterSpacing: '0.06em',
    lineHeight: 1.4,
    textTransform: 'uppercase',
  },
}

const lightTheme = createTheme({
  palette: {...lightPalette, ...commonPalette},
  typography: baseTypography,
  components: {
    ...defaultOptions.components
  },
});

const darkTheme = createTheme({
  palette: {...darkPalette, ...commonPalette},
  typography: baseTypography,
  components: {
    ...defaultOptions.components
  },
});


export { lightTheme, darkTheme };
