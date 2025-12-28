import { createTheme, ThemeOptions } from '@mui/material/styles';

type PaletteMode = 'light' | 'dark';

// Figma-inspired color system
// These will be enhanced with actual Figma variables when accessible
const colors = {
  light: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
      contrastText: '#ffffff',
    },
    background: {
      default: '#fafafa',
      paper: '#ffffff',
      elevated: '#ffffff',
    },
    text: {
      primary: 'rgba(0, 0, 0, 0.87)',
      secondary: 'rgba(0, 0, 0, 0.6)',
      disabled: 'rgba(0, 0, 0, 0.38)',
    },
    divider: 'rgba(0, 0, 0, 0.12)',
    border: 'rgba(0, 0, 0, 0.12)',
    surface: {
      default: '#ffffff',
      hover: 'rgba(0, 0, 0, 0.04)',
      active: 'rgba(0, 0, 0, 0.08)',
    },
  },
  dark: {
    primary: {
      main: '#90caf9',
      light: '#e3f2fd',
      dark: '#42a5f5',
      contrastText: 'rgba(0, 0, 0, 0.87)',
    },
    secondary: {
      main: '#f48fb1',
      light: '#fce4ec',
      dark: '#ad1457',
      contrastText: 'rgba(0, 0, 0, 0.87)',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
      elevated: '#2d2d2d',
    },
    text: {
      primary: 'rgba(255, 255, 255, 0.87)',
      secondary: 'rgba(255, 255, 255, 0.6)',
      disabled: 'rgba(255, 255, 255, 0.38)',
    },
    divider: 'rgba(255, 255, 255, 0.12)',
    border: 'rgba(255, 255, 255, 0.12)',
    surface: {
      default: '#1e1e1e',
      hover: 'rgba(255, 255, 255, 0.08)',
      active: 'rgba(255, 255, 255, 0.12)',
    },
  },
};

// Spacing scale (8px base unit)
const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

// Typography scale
const typography = {
  fontFamily: [
    '-apple-system',
    'BlinkMacSystemFont',
    '"Segoe UI"',
    'Roboto',
    '"Helvetica Neue"',
    'Arial',
    'sans-serif',
  ].join(','),
  h1: {
    fontSize: '2.5rem',
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: '-0.02em',
  },
  h2: {
    fontSize: '2rem',
    fontWeight: 600,
    lineHeight: 1.3,
    letterSpacing: '-0.01em',
  },
  h3: {
    fontSize: '1.75rem',
    fontWeight: 600,
    lineHeight: 1.3,
  },
  h4: {
    fontSize: '1.5rem',
    fontWeight: 600,
    lineHeight: 1.4,
  },
  h5: {
    fontSize: '1.25rem',
    fontWeight: 600,
    lineHeight: 1.4,
  },
  h6: {
    fontSize: '1rem',
    fontWeight: 600,
    lineHeight: 1.5,
  },
  body1: {
    fontSize: '1rem',
    lineHeight: 1.5,
  },
  body2: {
    fontSize: '0.875rem',
    lineHeight: 1.5,
  },
  button: {
    fontWeight: 500,
    textTransform: 'none' as const,
    letterSpacing: '0.02em',
  },
};

// Create theme function
export const createAppTheme = (mode: PaletteMode = 'light') => {
  const colorSet = colors[mode as keyof typeof colors];

  const themeOptions: ThemeOptions = {
    palette: {
      mode,
      primary: colorSet.primary,
      secondary: colorSet.secondary,
      background: {
        default: colorSet.background.default,
        paper: colorSet.background.paper,
      },
      text: colorSet.text,
      divider: colorSet.divider,
      success: {
        main: mode === 'light' ? '#2e7d32' : '#66bb6a',
        light: mode === 'light' ? '#4caf50' : '#81c784',
        dark: mode === 'light' ? '#1b5e20' : '#388e3c',
      },
      error: {
        main: mode === 'light' ? '#d32f2f' : '#f44336',
        light: mode === 'light' ? '#ef5350' : '#e57373',
        dark: mode === 'light' ? '#c62828' : '#d32f2f',
      },
      warning: {
        main: mode === 'light' ? '#ed6c02' : '#ffa726',
        light: mode === 'light' ? '#ff9800' : '#ffb74d',
        dark: mode === 'light' ? '#e65100' : '#f57c00',
      },
      info: {
        main: mode === 'light' ? '#0288d1' : '#29b6f6',
        light: mode === 'light' ? '#03a9f4' : '#4fc3f7',
        dark: mode === 'light' ? '#01579b' : '#0277bd',
      },
    },
    typography,
    spacing: 8, // Base spacing unit
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: colorSet.background.default,
            color: colorSet.text.primary,
            transition: 'background-color 0.3s ease, color 0.3s ease',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundColor: colorSet.background.paper,
            borderRadius: 12,
            boxShadow: mode === 'light'
              ? '0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24)'
              : '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.4)',
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              boxShadow: mode === 'light'
                ? '0 4px 12px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.12)'
                : '0 4px 12px rgba(0, 0, 0, 0.5), 0 2px 4px rgba(0, 0, 0, 0.4)',
              transform: 'translateY(-2px)',
            },
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            padding: '10px 24px',
            fontWeight: 500,
            textTransform: 'none',
            boxShadow: 'none',
            '&:hover': {
              boxShadow: mode === 'light'
                ? '0 2px 8px rgba(0, 0, 0, 0.15)'
                : '0 2px 8px rgba(0, 0, 0, 0.3)',
            },
          },
          contained: {
            '&:hover': {
              boxShadow: mode === 'light'
                ? '0 4px 12px rgba(0, 0, 0, 0.2)'
                : '0 4px 12px rgba(0, 0, 0, 0.4)',
            },
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              borderRadius: 8,
              backgroundColor: mode === 'light' ? '#ffffff' : colorSet.background.elevated,
              transition: 'all 0.2s ease',
              '&:hover': {
                backgroundColor: mode === 'light' ? '#fafafa' : colorSet.surface.hover,
              },
              '&.Mui-focused': {
                backgroundColor: mode === 'light' ? '#ffffff' : colorSet.background.elevated,
              },
            },
          },
        },
      },
      MuiTable: {
        styleOverrides: {
          root: {
            '& .MuiTableRow-root': {
              transition: 'background-color 0.15s ease',
              '&:hover': {
                backgroundColor: colorSet.surface.hover,
              },
            },
          },
        },
      },
      MuiTableHead: {
        styleOverrides: {
          root: {
            '& .MuiTableRow-root': {
              backgroundColor: mode === 'light' ? '#f5f5f5' : colorSet.background.elevated,
            },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            fontWeight: 500,
            transition: 'all 0.2s ease',
            '&:hover': {
              transform: 'translateY(-1px)',
              boxShadow: mode === 'light'
                ? '0 2px 4px rgba(0, 0, 0, 0.1)'
                : '0 2px 4px rgba(0, 0, 0, 0.3)',
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            borderRadius: 12,
          },
          elevation1: {
            boxShadow: mode === 'light'
              ? '0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24)'
              : '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.4)',
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: mode === 'light' ? '#ffffff' : colorSet.background.paper,
            color: colorSet.text.primary,
            boxShadow: mode === 'light'
              ? '0 1px 3px rgba(0, 0, 0, 0.12)'
              : '0 1px 3px rgba(0, 0, 0, 0.3)',
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          root: {
            borderBottom: `1px solid ${colorSet.divider}`,
          },
          indicator: {
            height: 3,
            borderRadius: '3px 3px 0 0',
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 500,
            minHeight: 48,
            '&.Mui-selected': {
              fontWeight: 600,
            },
          },
        },
      },
    },
  };

  return createTheme(themeOptions);
};

// Export spacing and colors for direct use
export { spacing, colors };





