import { useState } from "react";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";

export default function Profile() {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState({ full_name: user.full_name, email: user.email, phone: user.phone });
  const [pwd, setPwd] = useState({ current_password: "", new_password: "" });

  const save = async (e) => {
    e.preventDefault();
    try { await api.post("/auth/profile", form); await refresh(); toast.show("Profil diperbarui", "success"); }
    catch (er) { toast.show(er.message, "danger"); }
  };
  const changePwd = async (e) => {
    e.preventDefault();
    try {
      await api.post("/auth/change-password", pwd);
      toast.show("Password diubah", "success"); setPwd({ current_password: "", new_password: "" });
    } catch (er) { toast.show(er.message, "danger"); }
  };
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">AKUN SAYA</p><h1>Profil</h1><p className="subtitle">Kelola data pribadi dan keamanan akun.</p></div>
      </div>
      <div className="detail-grid">
        <section className="panel">
          <div className="panel-head"><div><h3>Data pribadi</h3><p>Perbarui informasi akun.</p></div></div>
          <div style={{ display: "flex", alignItems: "center", gap: 16, margin: "18px 0 6px" }}>
            <div className="avatar lg">{user.initials}</div>
            <div>
              <b style={{ fontSize: 14 }}>{user.full_name}</b>
              <p style={{ margin: "4px 0", fontSize: 11, color: "#64748b" }}>{user.role === "admin" ? "Administrator" : "User"} · {user.email}</p>
            </div>
          </div>
          <form onSubmit={save}>
            <label>Nama lengkap<input required data-testid="prof-fullname" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
            <label>Email<input required type="email" data-testid="prof-email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            <label>Telepon<input data-testid="prof-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
            <div className="modal-actions"><button className="primary-button" data-testid="prof-save">Simpan perubahan <span>→</span></button></div>
          </form>
        </section>
        <section className="panel">
          <div className="panel-head"><div><h3>Ubah password</h3><p>Pastikan password Anda kuat.</p></div></div>
          <form onSubmit={changePwd}>
            <label>Password saat ini<input required type="password" data-testid="pwd-current" value={pwd.current_password} onChange={(e) => setPwd({ ...pwd, current_password: e.target.value })} /></label>
            <label>Password baru<input required type="password" minLength={6} data-testid="pwd-new" value={pwd.new_password} onChange={(e) => setPwd({ ...pwd, new_password: e.target.value })} /></label>
            <div className="modal-actions"><button className="primary-button" data-testid="pwd-save">Ubah password <span>→</span></button></div>
          </form>
        </section>
      </div>
    </>
  );
}
