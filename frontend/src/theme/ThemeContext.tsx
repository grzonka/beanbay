import { CssBaseline, ThemeProvider as MuiThemeProvider } from '@mui/material';
import {
  type ReactNode,
  createContext,
  useContext,
  useMemo,
  useState,
} from 'react';
import { craftLight } from './craftLight';
import { espressoDark } from './espressoDark';

type ThemeMode = 'dark' | 'light';

interface ThemeContextValue {
  mode: ThemeMode;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  mode: 'dark',
  toggleTheme: () => {},
});

export const useThemeMode = () => useContext(ThemeContext);

const STORAGE_KEY = 'beanbay-theme';

function getInitialMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return 'dark';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(getInitialMode);

  const toggleTheme = () => {
    setMode((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  };

  const theme = useMemo(
    () => (mode === 'dark' ? espressoDark : craftLight),
    [mode],
  );

  const value = useMemo(() => ({ mode, toggleTheme }), [mode]);

  return (
    <ThemeContext.Provider value={value}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
}
