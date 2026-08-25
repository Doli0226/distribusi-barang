import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import "@/App.css";
import "@/Mobile.css";
import "@/Extra.css";

import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";

import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ResetPassword from "@/pages/ResetPassword";
import Dashboard from "@/pages/Dashboard";
import Products from "@/pages/Products";
import Categories from "@/pages/Categories";
import Warehouses from "@/pages/Warehouses";
import Stock from "@/pages/Stock";
import Recipients from "@/pages/Recipients";
import Vehicles from "@/pages/Vehicles";
import Requests from "@/pages/Requests";
import RequestDetail from "@/pages/RequestDetail";
import Distributions from "@/pages/Distributions";
import DistributionDetail from "@/pages/DistributionDetail";
import Tracking from "@/pages/Tracking";
import Notifications from "@/pages/Notifications";
import Activities from "@/pages/Activities";
import Reports from "@/pages/Reports";
import ReportSchedules from "@/pages/ReportSchedules";
import ReportInbox from "@/pages/ReportInbox";
import Users from "@/pages/Users";
import Profile from "@/pages/Profile";

function AdminRoute({ children }) {
  const { isAdmin, ready } = useAuth();
  if (!ready) return null;
  return isAdmin ? children : <Navigate to="/dashboard" replace />;
}

function ProtectedShell() {
  const { user, ready } = useAuth();
  const location = useLocation();
  const [mobileNav, setMobileNav] = useState(false);
  if (!ready) return null;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return (
    <div className={`app-shell ${user.role === "user" ? "role-user" : ""}`}>
      <Sidebar mobileOpen={mobileNav} onNavigate={() => setMobileNav(false)} />
      <main className="main-content">
        <Topbar onToggleMobile={() => setMobileNav((x) => !x)} mobileOpen={mobileNav} />
        <div className="page-wrap">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/permintaan" element={<Requests />} />
            <Route path="/permintaan/:id" element={<RequestDetail />} />
            <Route path="/barang" element={<AdminRoute><Products /></AdminRoute>} />
            <Route path="/kategori" element={<AdminRoute><Categories /></AdminRoute>} />
            <Route path="/gudang" element={<AdminRoute><Warehouses /></AdminRoute>} />
            <Route path="/stok" element={<AdminRoute><Stock /></AdminRoute>} />
            <Route path="/penerima" element={<AdminRoute><Recipients /></AdminRoute>} />
            <Route path="/kendaraan" element={<AdminRoute><Vehicles /></AdminRoute>} />
            <Route path="/distribusi" element={<Distributions />} />
            <Route path="/distribusi/:id" element={<DistributionDetail />} />
            <Route path="/tracking" element={<Tracking />} />
            <Route path="/notifikasi" element={<Notifications />} />
            <Route path="/aktivitas" element={<AdminRoute><Activities /></AdminRoute>} />
            <Route path="/laporan" element={<AdminRoute><Reports /></AdminRoute>} />
            <Route path="/jadwal-laporan" element={<AdminRoute><ReportSchedules /></AdminRoute>} />
            <Route path="/inbox-laporan" element={<AdminRoute><ReportInbox /></AdminRoute>} />
            <Route path="/pengguna" element={<AdminRoute><Users /></AdminRoute>} />
            <Route path="/profil" element={<Profile />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function PublicOnly({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return null;
  return user ? <Navigate to="/dashboard" replace /> : children;
}

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
            <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
            <Route path="/reset-password" element={<PublicOnly><ResetPassword /></PublicOnly>} />
            <Route path="/*" element={<ProtectedShell />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ToastProvider>
  );
}
