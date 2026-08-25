import { Bell, ChevronDown, LogOut, Menu, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";

const pageTitles = {
  dashboard: "Ringkasan operasional",
  permintaan: "Permintaan barang",
  barang: "Katalog barang",
  kategori: "Kategori barang",
  gudang: "Manajemen gudang",
  stok: "Stok & mutasi",
  distribusi: "Distribusi & pengiriman",
  tracking: "Tracking distribusi",
  kendaraan: "Manajemen kendaraan",
  penerima: "Data penerima",
  pengguna: "Manajemen pengguna",
  laporan: "Laporan operasional",
  aktivitas: "Audit trail",
  notifikasi: "Notifikasi",
  profil: "Profil pengguna",
};

export default function Topbar({ onToggleMobile, mobileOpen }) {
  const { user, isAdmin, logout } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const location = useLocation();
  const [notifs, setNotifs] = useState({ items: [], unread: 0 });
  const [open, setOpen] = useState(false);
  const knownIds = useRef(new Set());
  const bootstrapped = useRef(false);
  const ref = useRef();

  const load = async () => {
    try {
      const r = await api.get("/notifications");
      // Detect new notifications since last load and show toast (realtime UX)
      if (bootstrapped.current) {
        for (const n of r.data.items) {
          if (!knownIds.current.has(n.id) && !n.read) {
            toast.show(`${n.title} — ${n.message}`, n.kind === "warning" ? "warning" : n.kind === "danger" ? "danger" : "success");
          }
        }
      }
      knownIds.current = new Set(r.data.items.map((n) => n.id));
      bootstrapped.current = true;
      setNotifs(r.data);
    } catch {}
  };
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, [location.pathname]);
  useEffect(() => {
    const h = () => load();
    window.addEventListener("notifs:refresh", h);
    return () => window.removeEventListener("notifs:refresh", h);
  }, []);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h);
  }, []);

  const path = location.pathname.split("/")[1] || "dashboard";
  const title = pageTitles[path] || "Workspace";

  const markAll = async () => { await api.post("/notifications", { mark_all: true }); load(); };
  const openItem = async (n) => {
    if (!n.read) await api.post("/notifications", { id: n.id });
    setOpen(false); load();
    if (n.link) nav(n.link);
  };
  const doLogout = async () => { await logout(); toast.show("Logout berhasil", "success"); nav("/login"); };

  return (
    <header className="topbar">
      <button className="mobile-menu" aria-label="Buka menu" onClick={onToggleMobile} data-testid="mobile-menu-button">
        {mobileOpen ? <X /> : <Menu />}
      </button>
      <div className="breadcrumb"><span>Workspace</span><b>/</b><strong>{title}</strong></div>
      <div className="top-actions">
        <div className="role-switch" data-testid="role-indicator">
          {isAdmin && <button className="selected">Admin</button>}
          {!isAdmin && <button className="selected">User</button>}
        </div>
        <div style={{ position: "relative" }} ref={ref}>
          <button className="icon-button notification" onClick={() => setOpen((x) => !x)} data-testid="notifications-button" aria-label="Notifikasi">
            <Bell size={19} />
            {notifs.unread > 0 && <i data-testid="notification-count">{notifs.unread}</i>}
          </button>
          {open && (
            <div className="notif-menu" data-testid="notif-menu">
              <header><b>Notifikasi</b><button onClick={markAll} data-testid="mark-all-read">Tandai semua dibaca</button></header>
              {notifs.items.length === 0 ? (
                <div className="empty-state"><p>Belum ada notifikasi.</p></div>
              ) : (
                <ul>
                  {notifs.items.slice(0, 8).map((n) => (
                    <li key={n.id} className={n.read ? "" : "unread"} onClick={() => openItem(n)} data-testid={`notif-${n.id}`}>
                      <b>{n.title}</b>{n.message}<small>{n.created_at}</small>
                    </li>
                  ))}
                </ul>
              )}
              <div style={{ padding: "10px 16px", borderTop: "1px solid #f1f5f9" }}>
                <Link className="link-btn" to="/notifikasi" onClick={() => setOpen(false)}>Lihat semua →</Link>
              </div>
            </div>
          )}
        </div>
        <div className="top-profile">
          <div className="avatar small">{user?.initials}</div>
          <div><b>{user?.full_name || user?.username}</b><small>{isAdmin ? "Administrator" : "User"}</small></div>
          <ChevronDown size={15} />
        </div>
        <button className="logout icon-button" onClick={doLogout} data-testid="logout-button" aria-label="Keluar"><LogOut size={17} /></button>
      </div>
    </header>
  );
}
