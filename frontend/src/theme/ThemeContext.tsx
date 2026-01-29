import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { PaletteMode } from '@mui/material';
import { createAppTheme } from './theme';
import { ThemeProvider as MUIThemeProvider } from '@mui/material/styles';

interface ThemeContextType {
  mode: PaletteMode;
  toggleMode: () => void;
  setMode: (mode: PaletteMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = 'domain-analysis-theme-mode';

export const useThemeMode = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeMode must be used within a ThemeContextProvider');
  }
  return context;
};

interface ThemeContextProviderProps {
  children: ReactNode;
}

export const ThemeContextProvider: React.FC<ThemeContextProviderProps> = ({ children }) => {
  // Initialize mode from localStorage or default to 'light'
  const [mode, setModeState] = useState<PaletteMode>(() => {
    const savedMode = localStorage.getItem(THEME_STORAGE_KEY);
    if (savedMode === 'light' || savedMode === 'dark') {
      return savedMode;
    }
    // Check system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  });

  // Update localStorage when mode changes
  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, mode);
  }, [mode]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      // Only auto-switch if user hasn't manually set a preference
      const savedMode = localStorage.getItem(THEME_STORAGE_KEY);
      if (!savedMode) {
        setModeState(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const toggleMode = () => {
    setModeState((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
  };

  const setMode = (newMode: PaletteMode) => {
    setModeState(newMode);
  };

  const theme = createAppTheme(mode);

  return (
    <ThemeContext.Provider value={{ mode, toggleMode, setMode }}>
      <MUIThemeProvider theme={theme}>
        {children}
      </MUIThemeProvider>
    </ThemeContext.Provider>
  );
};














