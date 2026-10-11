import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AcademyPage } from "./pages/Academy";
import { CockpitPage } from "./pages/Cockpit";
import { CompanyPage } from "./pages/Company";
import { ScreenerPage } from "./pages/Screener";
import { Shell } from "./shell";
import { ThemeProvider } from "./theme";

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/" element={<CockpitPage />} />
            <Route path="/screener" element={<ScreenerPage />} />
            <Route path="/company" element={<CompanyPage />} />
            <Route path="/learn" element={<AcademyPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
