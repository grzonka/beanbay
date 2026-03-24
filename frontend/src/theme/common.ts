import type { ThemeOptions } from '@mui/material/styles';

export const commonThemeOptions: ThemeOptions = {
  typography: {
    fontFamily: '"DM Sans", sans-serif',
    h1: { fontFamily: '"DM Serif Display", serif' },
    h2: { fontFamily: '"DM Serif Display", serif' },
    h3: { fontFamily: '"DM Serif Display", serif' },
    h4: { fontFamily: '"DM Serif Display", serif' },
    h5: { fontFamily: '"DM Sans", sans-serif', fontWeight: 600 },
    h6: { fontFamily: '"DM Sans", sans-serif', fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { minHeight: 40 } },
    },
    MuiTextField: {
      defaultProps: { size: 'small', fullWidth: true },
    },
    MuiDialog: {
      defaultProps: { fullWidth: true, maxWidth: 'sm' },
    },
  },
};
