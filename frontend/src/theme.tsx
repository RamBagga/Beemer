import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type ThemeName = "light" | "dark";

export interface Palette {
  bg: string; surface: string; raised: string; line: string; grid: string; text: string; body: string;
  muted: string; dim: string; chart: string; blue: string; ice: string; cobalt: string; red: string;
  green: string; amber: string; ember: string; violet: string; teal: string; bar: string; sidebar: string;
  pos: string; neg: string; shadow: string; hero: string;
}

export const PALETTES: Record<ThemeName, Palette> = {
  light: {
    bg: "#F5F7FB", surface: "#FFFFFF", raised: "#F0F3F8", line: "#E2E7EF", grid: "#ECEFF5", text: "#0A1022", body: "#283145",
    muted: "#556073", dim: "#828CA0", chart: "#5E687B", blue: "#2D6BFF", ice: "#2563C9", cobalt: "#2A4BD7", red: "#E0283A",
    green: "#10B981", amber: "#F59E0B", ember: "#F43F5E", violet: "#7466E8", teal: "#14B8A6", bar: "#D3DDF1", sidebar: "#FBFCFE",
    pos: "#047857", neg: "#BE123C", shadow: "0 1px 2px rgba(10,16,34,.04), 0 12px 28px -16px rgba(10,16,34,.20)",
    hero: "linear-gradient(120deg,#FFFFFF 0%,#F4F7FC 55%,#E9EEF8 100%)",
  },
  dark: {
    bg: "#06080E", surface: "#0C111B", raised: "#121926", line: "#1C2433", grid: "#151C29", text: "#EAEFF7", body: "#C3CBD9",
    muted: "#97A1B4", dim: "#6E788E", chart: "#A3ADBF", blue: "#5B8CFF", ice: "#7DB8FF", cobalt: "#2A4BD7", red: "#F0303F",
    green: "#34D399", amber: "#FBBF24", ember: "#FB7185", violet: "#A08FFF", teal: "#2DD4BF", bar: "#22355C", sidebar: "#0A0E17",
    pos: "#6EE7B7", neg: "#FDA4AF", shadow: "none",
    hero: "linear-gradient(120deg,#0E1424,#06080E 70%)",
  },
};

export const SUBSECTOR: Record<string, string> = {
  "IT services": "#3B82F6",
  "SaaS & software products": "#8B5CF6",
  "AI & data": "#06B6D4",
  "Engineering & design R&D": "#6366F1",
  "Electronics & semicon design": "#0EA5A4",
  Fintech: "#D946EF",
  "Internet & consumer tech": "#F97316",
};

export function subColor(name?: string | null) {
  return (name && SUBSECTOR[name]) || "#64748B";
}

const Ctx = createContext<{ theme: ThemeName; setTheme: (t: ThemeName) => void }>({
  theme: "light",
  setTheme: () => {},
});

function initial(): ThemeName {
  if (typeof document !== "undefined" && document.documentElement.dataset.theme === "dark") return "dark";
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>(initial);
  const setTheme = (t: ThemeName) => {
    setThemeState(t);
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem("beemer-theme", t === "dark" ? "Dark" : "Light"); } catch { /* private mode */ }
  };
  const value = useMemo(() => ({ theme, setTheme }), [theme]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  return useContext(Ctx);
}

export function usePalette() {
  const { theme } = useTheme();
  return PALETTES[theme];
}
