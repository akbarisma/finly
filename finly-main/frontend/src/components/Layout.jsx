import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  House, Receipt, ChartBar, ListBullets, Cpu, ClockCounterClockwise, SignOut, List,
} from "@phosphor-icons/react";
import api from "../services/api";
import Logo from "./Logo";

const NAV = [
  { to: "/", label: "Beranda", icon: House, end: true, testid: "nav-dashboard" },
  { to: "/transaksi", label: "Transaksi", icon: Receipt, testid: "nav-transaksi" },
  { to: "/budgeting", label: "Anggaran", icon: ChartBar, testid: "nav-budgeting" },
  { to: "/detail", label: "Detail", icon: ListBullets, testid: "nav-detail" },
  { to: "/prediksi", label: "Prediksi ML", icon: Cpu, testid: "nav-prediksi" },
  { to: "/history", label: "Riwayat", icon: ClockCounterClockwise, testid: "nav-history" },
];

function SidebarBody({ onNavigate, onLogout, user }) {
  const displayName = user?.name || user?.email || "User";
  const initials = (displayName.split(" ").map((p) => p[0]).join("").slice(0, 2) || "F").toUpperCase();

  return (
    <>
      <div className="p-5 border-b-2 hairline-strong flex items-center gap-3 bg-[var(--brand-bg-deep)] relative">
        <Logo size="md" />
        <div>
          <div className="overline leading-none font-bold">Financial · ID</div>
          <div className="text-[10px] font-mono text-[var(--ink-soft)] mt-1">LEDGER · LSTM</div>
        </div>
        <div className="absolute right-0 top-0 bottom-0 w-4 stripes-corner" />
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto scroll-custom bg-[var(--brand-bg)]">
        <div className="overline px-2 pb-2 pt-1 font-bold">Modul</div>
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            data-testid={item.testid}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 text-sm font-semibold border-2 transition-all ${
                isActive
                  ? "bg-black text-[var(--brand-bg)] border-black shadow-[3px_3px_0_0_var(--ink)]"
                  : "bg-white text-[var(--ink)] border-black hover:translate-x-[-2px] hover:shadow-[3px_3px_0_0_var(--ink)]"
              }`
            }
          >
            <item.icon size={18} weight="bold" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t-2 hairline-strong space-y-3 bg-[var(--brand-bg-soft)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black text-[var(--brand-bg)] border-2 border-black flex items-center justify-center font-mono font-bold text-sm">{initials}</div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold truncate" data-testid="user-name">{displayName}</div>
            <div className="text-[11px] text-[var(--ink-soft)] truncate font-mono">{user?.email}</div>
          </div>
        </div>
        <button
          onClick={onLogout}
          data-testid="logout-button"
          className="w-full btn-ghost flex items-center justify-center gap-2 py-2 !text-xs"
        >
          <SignOut size={14} /> Keluar
        </button>
      </div>
    </>
  );
}

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("user_data") || "{}"); }
    catch { return {}; }
  });
  const [clock, setClock] = useState(new Date());
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 60_000);
    return () => clearInterval(t);
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  // Keep user state in sync if it changes elsewhere
  useEffect(() => {
    const sync = () => {
      try { setUser(JSON.parse(localStorage.getItem("user_data") || "{}")); } catch (e) { console.error("user_data parse failed:", e); }
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);

  const handleLogout = async () => {
    try { await api.logout(); } catch (e) { console.error("Logout API failed (continuing):", e); }
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-[var(--brand-bg)]">
      {/* Desktop sidebar */}
      <aside
        className="hidden lg:flex w-64 shrink-0 border-r-2 hairline-strong bg-white flex-col sticky top-0 h-screen"
        data-testid="sidebar"
      >
        <SidebarBody onNavigate={() => {}} onLogout={handleLogout} user={user} />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <>
          <div className="backdrop lg:hidden" onClick={() => setMobileOpen(false)} data-testid="mobile-backdrop" />
          <aside
            className="fixed top-0 left-0 bottom-0 z-50 w-72 bg-white border-r-2 hairline-strong flex flex-col lg:hidden slide-in-left"
            data-testid="sidebar-mobile"
          >
            <SidebarBody onNavigate={() => setMobileOpen(false)} onLogout={handleLogout} user={user} />
          </aside>
        </>
      )}

      {/* Main column */}
      <main className="flex-1 min-w-0 flex flex-col canvas-noise">
        {/* Top bar — yellow */}
        <div className="topbar-y sticky top-0 z-20">
          <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8 py-3 text-[11px] font-mono text-[var(--ink)]">
            <div className="flex items-center gap-3 sm:gap-6">
              <button
                onClick={() => setMobileOpen(true)}
                className="lg:hidden btn-ghost !p-2 !shadow-none !border-2"
                data-testid="mobile-menu-toggle"
                aria-label="Buka menu"
              >
                <List size={18} />
              </button>
              <span className="hidden sm:flex items-center gap-2 font-bold">
                <span className="pulse-dot" />
                FINLY·LEDGER <span className="opacity-60">v1.0</span>
              </span>
              <span className="hidden md:inline font-bold">UPTIME · {clock.toLocaleDateString("id-ID")}</span>
            </div>
            <div className="flex items-center gap-3 sm:gap-6 font-bold">
              <span>{clock.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })} WIB</span>
              <span className="hidden sm:inline">IDR · ID-ID</span>
            </div>
          </div>
        </div>
        <div className="flex-1">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
