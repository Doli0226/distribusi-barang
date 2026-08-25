import { Bell, Boxes, ChevronDown, ClipboardList, FileBarChart, History, LayoutDashboard, ListChecks, MapPinned, Package, Settings, Truck, Users, Warehouse } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const adminNav = [
  { to: "/dashboard", label: "Ringkasan", icon: LayoutDashboard },
  { to: "/permintaan", label: "Permintaan", icon: ClipboardList },
  { to: "/barang", label: "Barang", icon: Boxes },
  { to: "/kategori", label: "Kategori", icon: ListChecks },
  { to: "/gudang", label: "Gudang", icon: Warehouse },
  { to: "/stok", label: "Stok", icon: Package },
  { to: "/distribusi", label: "Distribusi", icon: Truck },
  { to: "/tracking", label: "Tracking", icon: MapPinned },
  { to: "/kendaraan", label: "Kendaraan", icon: Truck },
  { to: "/penerima", label: "Penerima", icon: Users },
  { to: "/pengguna", label: "Pengguna", icon: Users },
  { to: "/laporan", label: "Laporan", icon: FileBarChart },
  { to: "/aktivitas", label: "Aktivitas", icon: History },
  { to: "/notifikasi", label: "Notifikasi", icon: Bell },
];

const userNav = [
  { to: "/dashboard", label: "Ringkasan", icon: LayoutDashboard },
  { to: "/permintaan", label: "Permintaan Saya", icon: ClipboardList },
  { to: "/distribusi", label: "Distribusi", icon: Truck },
  { to: "/tracking", label: "Tracking", icon: MapPinned },
  { to: "/notifikasi", label: "Notifikasi", icon: Bell },
];

export default function Sidebar({ mobileOpen, onNavigate }) {
  const { user, isAdmin } = useAuth();
  const nav = isAdmin ? adminNav : userNav;
  return (
    <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`} data-testid="sidebar">
      <div className="brand">
        <div className="brand-square">L<span>/</span>P</div>
        <div><b>Logisti<span>Pro</span></b><small>INDONESIA</small></div>
      </div>
      <div className="workspace">
        <span className="workspace-dot" /> Main Workspace <ChevronDown size={14} />
      </div>
      <nav>
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
            data-testid={`nav-${to.slice(1)}`}
          >
            <Icon size={18} /> {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <NavLink to="/profil" className="nav-item" data-testid="nav-profil"><Settings size={18} /> Profil & Setelan</NavLink>
        <div className="profile">
          <div className="avatar">{user?.initials || "U"}</div>
          <div>
            <b>{user?.full_name || user?.username}</b>
            <small>{isAdmin ? "Administrator" : "User"}</small>
          </div>
          <ChevronDown size={15} />
        </div>
      </div>
    </aside>
  );
}
