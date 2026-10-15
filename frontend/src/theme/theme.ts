"use client";

import { alpha, createTheme } from "@mui/material/styles";

const primaryMain = "#2196F3";
const divider = "#E0E0E0";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: primaryMain, dark: "#1976D2", contrastText: "#FFFFFF" },
    error: { main: "#D32F2F" },
    success: { main: "#2E7D32" },
    warning: { main: "#ED6C02" },
    background: { default: "#FFFFFF", paper: "#FFFFFF" },
    text: { primary: "rgba(0, 0, 0, 0.87)", secondary: "rgba(0, 0, 0, 0.6)", disabled: "rgba(0, 0, 0, 0.38)" },
    divider,
  },
  shape: { borderRadius: 4 },
  typography: {
    fontFamily: "var(--font-lato), 'Lato', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    h5: { fontSize: "1.5rem", fontWeight: 700, lineHeight: 1.334 },
    h6: { fontSize: "1.25rem", fontWeight: 700, lineHeight: 1.6 },
    subtitle1: { fontWeight: 700 },
    button: { fontWeight: 500, letterSpacing: "0.46px" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: { body: { WebkitFontSmoothing: "antialiased" } },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { whiteSpace: "nowrap" },
      },
    },
    MuiBackdrop: {
      styleOverrides: {
        root: {
          "&:not(.MuiBackdrop-invisible)": {
            backgroundColor: "rgba(255, 255, 255, 0.35)",
            backdropFilter: "blur(3px)",
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: { paper: { borderRadius: 4, boxShadow: "0 11px 15px -7px rgba(0,0,0,0.2), 0 24px 38px 3px rgba(0,0,0,0.14), 0 9px 46px 8px rgba(0,0,0,0.12)" } },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: divider, fontSize: "0.875rem" },
        head: { fontWeight: 700, backgroundColor: "#FAFAFA", whiteSpace: "nowrap" },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          "&.Mui-selected, &.Mui-selected:hover": { backgroundColor: alpha(primaryMain, 0.08) },
        },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 400 } },
    },
    MuiTooltip: {
      defaultProps: { arrow: true },
    },
  },
});
