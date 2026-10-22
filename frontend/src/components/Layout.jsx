import { NavLink, Outlet, Link } from "react-router-dom";
import { FilePlus2, LayoutDashboard, Map as MapIcon, Home, Bot } from "lucide-react";
import { Logo } from "./ui.jsx";
import { useConfig } from "../ConfigContext.jsx";
import { ErrorState, Loading } from "./ui.jsx";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/report", label: "Report a hazard", icon: FilePlus2 },
  { to: "/chat", label: "Safety Assistant", icon: Bot },
  { to: "/map", label: "Campus map", icon: MapIcon },
];

export default function Layout() {
  const { config, error } = useConfig();
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/" className="side-brand"><Logo light /></Link>
        <nav aria-label="Main">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `side-link ${isActive ? "active" : ""}`}>
              <Icon size={18} /> <span>{label}</span>
            </NavLink>
          ))}
          <Link to="/" className="side-link"><Home size={18} /> <span>Home</span></Link>
        </nav>
        <p className="side-note">Early-stage prototype. AI output is a suggestion; humans decide.</p>
      </aside>
      <main className="main">
        {error ? <ErrorState message={error} onRetry={() => window.location.reload()} />
          : !config ? <Loading label="Connecting to backend…" /> : <Outlet />}
      </main>
    </div>
  );
}
