import { createTheme, darken, alpha } from '@mui/material/styles';
import { blueGrey, indigo, teal, lightGreen, amber, red, pink, deepPurple, blue } from '@mui/material/colors';

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
          color: theme.palette.mode === 'dark' ? theme.palette.link?.main ?? theme.palette.primary.light : theme.palette.primary.main,
          textDecorationColor: theme.palette.mode === 'dark' ? theme.palette.link?.main ?? theme.palette.primary.light : theme.palette.primary.main,
          transition: 'color 0.2s ease, text-decoration-color 0.2s ease',
          '&:hover': {
            color: theme.palette.mode === 'dark'
              ? theme.palette.link?.hover ?? theme.palette.primary.light
              : alpha(theme.palette.primary.main, 0.85),
            textDecorationColor: theme.palette.mode === 'dark'
              ? theme.palette.link?.hover ?? theme.palette.primary.light
              : alpha(theme.palette.primary.main, 0.85),
          },
        }),
      },
    },
    MuiLink: {
      styleOverrides: {
        root: ({ theme }) => ({
          color: theme.palette.mode === 'dark' ? theme.palette.link?.main ?? theme.palette.primary.light : theme.palette.primary.main,
          textDecorationColor: theme.palette.mode === 'dark' ? theme.palette.link?.main ?? theme.palette.primary.light : theme.palette.primary.main,
          transition: 'color 0.2s ease, text-decoration-color 0.2s ease',
          '&:hover': {
            color: theme.palette.mode === 'dark'
              ? theme.palette.link?.hover ?? theme.palette.primary.light
              : alpha(theme.palette.primary.main, 0.85),
            textDecorationColor: theme.palette.mode === 'dark'
              ? theme.palette.link?.hover ?? theme.palette.primary.light
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
        root: {
          borderRadius: 8,
          border: 'none',
          boxShadow: 'none',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: ({ theme }) => ({
          '.MuiTableBody-root &': {
            backgroundColor: theme.palette.mode === 'light' ? alpha(theme.palette.background.dark, 0.5) : 'rgba(255, 255, 255, 0.03)',
            '&:hover': {
              backgroundColor: theme.palette.mode === 'light' ? alpha(theme.palette.background.dark, 0.25) : 'rgba(255, 255, 255, 0.08)',
            },
            '& td, & th': {
              paddingTop: 12,
              paddingBottom: 12,
            },
            'a': {
              color: theme.palette.mode === 'light' ? theme.palette.primary.dark : theme.palette.link?.main ?? theme.palette.primary.light,
              textDecoration: 'none',
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
                : `${theme.palette.link?.main ?? theme.palette.primary.light} !important`,
              '&:hover': {
                color: theme.palette.mode === 'light'
                  ? undefined
                  : `${theme.palette.link?.hover ?? theme.palette.primary.light} !important`,
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
        root: ({ theme }) => ({
          lineHeight: 1.4,
          borderColor: theme.palette.mode === 'light' ? '#f0f0f0' : 'rgba(255,255,255,0.06)',
        }),
      },
    },
    MuiSwitch: {
      defaultProps: {
        size: 'small',
      },
      styleOverrides: {
        colorPrimary: ({ theme }) => theme.palette.mode === 'dark' ? {
          '&.Mui-checked': {
            color: '#9899c8',
            '& + .MuiSwitch-track': {
              backgroundColor: '#6b6d9e',
            },
          },
        } : {},
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
            backgroundColor: theme.palette.mode === 'light' ? alpha(theme.palette.primary.main, 0.16) : 'rgba(255, 255, 255, 0.12)',
            borderColor: theme.palette.primary.main,
          },
          transition: 'color 0.3s, background-color 0.3s, border-color 0.3s',
        }),
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: '8px',
          boxShadow: theme.palette.mode === 'dark'
            ? '0 1px 2px rgba(0,0,0,0.3), 0 2px 8px rgba(0,0,0,0.2)'
            : '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)',
        }),
      },
    },
    MuiButton: {
      defaultProps: {
        size: 'small',
      },
      styleOverrides: {
        root: {
          padding: '8px 20px',
        },
      },
      variants: [
        {
            props: { variant: 'contained' },
            style: ({ theme }) => ({
                textTransform: 'none',
                boxShadow: 'none',
                borderRadius: 8,
                color: '#ffffff',
                backgroundColor: theme.palette.primary.main,
                transition: 'background-color 0.25s ease, box-shadow 0.25s ease',
                '&:hover': {
                    backgroundColor: theme.palette.primary.dark,
                    boxShadow: theme.palette.mode === 'dark'
                      ? `0 0 0 1px ${alpha(theme.palette.primary.main, 0.7)}, 0 0 10px 1px ${alpha(theme.palette.primary.main, 0.3)}`
                      : `0 0 0 1px ${alpha(theme.palette.primary.main, 0.2)}, 0 0 18px 3px ${alpha(theme.palette.primary.main, 0.14)}`,
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
    MuiTab: {
      styleOverrides: {
        root: ({ theme }) => theme.palette.mode === 'dark' ? {
          color: theme.palette.text.primary,
          '&.Mui-selected': {
            color: theme.palette.primary.light,
          },
        } : {},
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: ({ theme }) => ({
          backgroundColor: theme.palette.mode === 'light' ? theme.palette.common.white : theme.palette.background.dark,
          '* th': {
            fontWeight: 600,
            paddingTop: '10px',
            paddingBottom: '10px',
            backgroundColor: theme.palette.mode === 'light' ? theme.palette.common.white : theme.palette.background.dark,
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
      main: '#fbfcfc',
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
      main: '#4f46e5',
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
      // 4 distinct surface levels — darkest to lightest
      dark: '#0f0f11',      // level 0: deepest (sidebar base, page chrome)
      main: '#18181b',      // level 1: page background
      nav: '#27272a',       // level 2: nav bar, header, sidebar surface (same as cards)
      box: '#27272a',       // level 3: cards, papers, raised content
    },
    border: {
      main: '#3f3f46',
    },
    errorText: {
      main: '#ff6b9d',
    },
    primary: {
      main: '#4f46e5',
      text: 'rgb(184, 190, 255)',
    },
    // soft lavender-white for links — matches outlined button text, distinct from pure purple chrome
    link: {
      main: 'rgb(184, 190, 255)',
      hover: 'rgb(210, 214, 255)',
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
    blue: blue,
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
