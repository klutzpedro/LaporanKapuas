import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import {
  ShieldStar, House, Newspaper, UserFocus, Megaphone,
  ChartLineUp, Crosshair, ClipboardText, FilePdf, SignOut, Users, Archive,
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

export default function Sidebar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const teamLinks = TEAM_NAV.filter(
    (n) => user?.role === "admin" || user?.role === n.role
  );

  return (
    <aside className="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col" data-testid="sidebar">
      <div className="p-5 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-amber-500 text-zinc-950 flex items-center justify-center">
            <ShieldStar size={20} weight="fill" />
          </div>
          <div>
            <p className="text-[9px] tracking-[0.25em] text-zinc-500 font-bold uppercase">BAIS TNI</p>
            <h1 className="text-base font-black uppercase tracking-tighter leading-none">Geospasika</h1>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        <p className="overline px-2 pt-2 pb-1">Dashboard</p>
        <SideLink to="/" icon={House} label="Ringkasan Harian" testid="nav-dashboard" />
        {(user?.role === "admin" || user?.role === "piket") && (
          <>
            <SideLink to="/summary" icon={FilePdf} label="Summary & PDF" testid="nav-summary" />
            <SideLink to="/history" icon={Archive} label="Arsip Laporan" testid="nav-history" />
          </>
        )}

        <p className="overline px-2 pt-4 pb-1">Input Data Tim</p>
        {teamLinks.map((n) => (
          <SideLink key={n.to} to={n.to} icon={n.icon} label={n.label} testid={`nav-${n.role}`} />
        ))}

        {user?.role === "admin" && (
          <>
            <p className="overline px-2 pt-4 pb-1">Admin</p>
            <SideLink to="/admin/users" icon={Users} label="Manajemen User" testid="nav-users" />
          </>
        )}
      </nav>

      <div className="border-t border-zinc-800 p-3">
        <div className="px-2 py-2">
          <p className="overline text-zinc-500">Sesi Aktif</p>
          <p className="text-sm font-semibold mt-0.5 truncate" data-testid="current-user-name">{user?.name || "—"}</p>
          <p className="text-[10px] font-mono text-amber-500 mt-0.5" data-testid="current-user-role">
            {ROLE_LABEL[user?.role] || user?.role}
          </p>
        </div>
        <button
          onClick={async () => { await logout(); nav("/login"); }}
          data-testid="logout-button"
          className="w-full flex items-center justify-center gap-2 mt-2 py-2 px-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-red-500/50 hover:text-red-400 text-zinc-300 btn-tactical rounded-sm transition-colors"
        >
          <SignOut size={14} weight="bold" />
          Logout
        </button>
      </div>
    </aside>
  );
}

function SideLink({ to, icon: Icon, label, testid }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      data-testid={testid}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 text-xs font-bold uppercase tracking-wider rounded-sm transition-colors ${
          isActive
            ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
            : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100 border-l-2 border-transparent"
        }`
      }
    >
      <Icon size={16} weight="bold" />
      {label}
    </NavLink>
  );
}
