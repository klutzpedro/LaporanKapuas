import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useEffect, useState } from "react";
import {
  House, Newspaper, UserFocus, Megaphone,
  ChartLineUp, Crosshair, ClipboardText, FilePdf, SignOut, Users, Archive,
  MagnifyingGlass, Sun,
  CaretLeft, CaretRight,
} from "@phosphor-icons/react";
import { ROLE_LABEL } from "@/lib/api";

const TEAM_NAV = [
  { to: "/team/lid", label: "TIM LID", role: "tim_lid", icon: Newspaper },
  { to: "/team/kontra", label: "TIM KONTRA", role: "tim_kontra", icon: UserFocus },
  { to: "/team/gal", label: "TIM GAL", role: "tim_gal", icon: Megaphone },
  { to: "/team/medmon", label: "TIM MEDMON", role: "tim_medmon", icon: ChartLineUp },
  { to: "/team/geoint", label: "TIM GEOINT", role: "tim_geoint", icon: Crosshair },
  { to: "/team/piket", label: "PIKET", role: "piket", icon: ClipboardText },
];

const LS_KEY = "bais_sidebar_collapsed";

export default function Sidebar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_KEY) === "1"; } catch { return false; }
  });

  useEffect(() => {
    try { localStorage.setItem(LS_KEY, collapsed ? "1" : "0"); } catch { /* */ }
  }, [collapsed]);

  const teamLinks = TEAM_NAV.filter(
    (n) => user?.role === "admin" || user?.role === n.role
  );

  return (
    <aside
      className={`bg-zinc-950 border-r border-zinc-800 flex flex-col relative transition-[width] duration-200 ease-out ${
        collapsed ? "w-[68px]" : "w-64"
      }`}
      data-testid="sidebar"
      data-collapsed={collapsed ? "true" : "false"}
    >
      {/* Collapse toggle button */}
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        data-testid="sidebar-toggle"
        aria-label={collapsed ? "Buka sidebar" : "Tutup sidebar"}
        title={collapsed ? "Buka sidebar" : "Tutup sidebar"}
        className="absolute -right-3 top-6 z-30 w-6 h-6 rounded-full bg-amber-500 hover:bg-amber-400 text-zinc-950 flex items-center justify-center shadow-md border-2 border-zinc-950"
      >
        {collapsed ? <CaretRight size={12} weight="bold" /> : <CaretLeft size={12} weight="bold" />}
      </button>

      {/* Header */}
      <div className="p-5 border-b border-zinc-800 overflow-hidden">
        <div className="flex items-center gap-3">
          <img
            src="/logo.png"
            alt="BAIS TNI"
            className="w-10 h-10 object-contain shrink-0 rounded-sm"
            data-testid="sidebar-logo"
          />
          {!collapsed && (
            <div className="min-w-0">
              <p className="text-[9px] tracking-[0.25em] text-zinc-500 font-bold uppercase">BAIS TNI</p>
              <h1 className="text-base font-black uppercase tracking-tighter leading-none truncate">Geospasika</h1>
            </div>
          )}
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-1">
        {!collapsed && <p className="overline px-2 pt-2 pb-1">Dashboard</p>}
        <SideLink to="/" icon={House} label="Ringkasan Harian" testid="nav-dashboard" collapsed={collapsed} />
        {(user?.role === "admin" || user?.role === "piket") && (
          <>
            <SideLink to="/summary" icon={FilePdf} label="Summary & PDF" testid="nav-summary" collapsed={collapsed} />
            <SideLink to="/history" icon={Archive} label="Arsip Laporan" testid="nav-history" collapsed={collapsed} />
            <SideLink to="/search" icon={MagnifyingGlass} label="Cari Laporan" testid="nav-search" collapsed={collapsed} />
            <SideLink to="/morning" icon={Sun} label="Laporan Pagi" testid="nav-morning" collapsed={collapsed} />
          </>
        )}
        {user?.role !== "admin" && user?.role !== "piket" && user && (
          <SideLink to="/search" icon={MagnifyingGlass} label="Cari Laporan" testid="nav-search" collapsed={collapsed} />
        )}

        {!collapsed && <p className="overline px-2 pt-4 pb-1">Input Data Tim</p>}
        {collapsed && <div className="h-px bg-zinc-800 my-3 mx-2" />}
        {teamLinks.map((n) => (
          <SideLink key={n.to} to={n.to} icon={n.icon} label={n.label} testid={`nav-${n.role}`} collapsed={collapsed} />
        ))}

        {user?.role === "admin" && (
          <>
            {!collapsed && <p className="overline px-2 pt-4 pb-1">Admin</p>}
            {collapsed && <div className="h-px bg-zinc-800 my-3 mx-2" />}
            <SideLink to="/admin/users" icon={Users} label="Manajemen User" testid="nav-users" collapsed={collapsed} />
          </>
        )}
      </nav>

      <div className="border-t border-zinc-800 p-3">
        {!collapsed && (
          <div className="px-2 py-2">
            <p className="overline text-zinc-500">Sesi Aktif</p>
            <p className="text-sm font-semibold mt-0.5 truncate" data-testid="current-user-name">{user?.name || "—"}</p>
            <p className="text-[10px] font-mono text-amber-500 mt-0.5" data-testid="current-user-role">
              {ROLE_LABEL[user?.role] || user?.role}
            </p>
          </div>
        )}
        <button
          onClick={async () => { await logout(); nav("/login"); }}
          data-testid="logout-button"
          title="Logout"
          className={`w-full flex items-center justify-center gap-2 py-2 px-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-red-500/50 hover:text-red-400 text-zinc-300 btn-tactical rounded-sm transition-colors ${
            collapsed ? "" : "mt-2"
          }`}
        >
          <SignOut size={14} weight="bold" />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
}

function SideLink({ to, icon: Icon, label, testid, collapsed }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      data-testid={testid}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 text-xs font-bold uppercase tracking-wider rounded-sm transition-colors ${
          isActive
            ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
            : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100 border-l-2 border-transparent"
        } ${collapsed ? "justify-center" : ""}`
      }
    >
      <Icon size={16} weight="bold" className="shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  );
}
