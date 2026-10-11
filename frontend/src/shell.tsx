import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { get, type CompanyListItem, type Picks } from "./api";
import { useTheme } from "./theme";

const LINKS = [
  { to: "/", label: "Cockpit", end: true },
  { to: "/screener", label: "Screener", end: false },
  { to: "/company", label: "Company", end: false },
  { to: "/learn", label: "Academy", end: false },
];

export function Shell() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const [meta, setMeta] = useState("");
  useEffect(() => {
    document.documentElement.classList.toggle("bm-open", open);
    return () => document.documentElement.classList.remove("bm-open");
  }, [open]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => {
    Promise.all([get<CompanyListItem[]>("/api/companies"), get<Picks>("/api/picks")])
      .then(([cos, picks]) => setMeta(picks.asOf ? `Data to ${picks.asOf} · ${cos.length} companies` : `${cos.length} companies`))
      .catch(() => setMeta(""));
  }, []);
  const mark = theme === "dark" ? "/beemer-wordmark.svg" : "/beemer-wordmark-light.svg";
  return (
    <>
      <button id="bm-burger" type="button" className={open ? "open" : ""} aria-label="Menu" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <i /><i /><i />
      </button>
      <div id="bm-scrim" onClick={() => setOpen(false)} />
      <header className="topbar">
        <NavLink to="/" aria-label="Beemer"><img className="wordmark" src={mark} alt="Beemer" /></NavLink>
      </header>
      <aside className="drawer" aria-hidden={!open}>
        <img className="wordmark" src={mark} alt="" style={{ height: 26, marginBottom: 12 }} />
        <div className="bm-stripe" />
        <div className="bm-k" style={{ fontSize: ".6rem", marginBottom: 8 }}>Theme</div>
        <div className="bm-theme">
          <button type="button" className={theme === "light" ? "on" : ""} onClick={() => setTheme("light")}>Studio</button>
          <button type="button" className={theme === "dark" ? "on" : ""} onClick={() => setTheme("dark")}>Night</button>
        </div>
        <nav className="nav">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={() => setOpen(false)}>{l.label}</NavLink>
          ))}
        </nav>
        <div className="side-foot">{meta}</div>
      </aside>
      <main className="main"><Outlet /></main>
    </>
  );
}
