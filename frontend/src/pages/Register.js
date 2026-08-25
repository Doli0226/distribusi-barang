import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";

export default function Register() {
  const { register } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const change = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setLoading(true);
    try { await register(form); toast.show("Registrasi berhasil", "success"); nav("/dashboard"); }
    catch (er) { setErr(er.message); }
    finally { setLoading(false); }
  };

  return (
    <main className="login-page">
      <div className="login-visual">
        <div className="brand-mark">L<span>/</span>P</div>
        <div className="visual-copy">
          <p className="eyebrow">GABUNG SEKARANG</p>
          <h1>Kelola distribusi<br /><em>lebih cepat.</em></h1>
          <p>Buat akun untuk mengakses workspace distribusi.</p>
        </div>
        <div className="visual-footer">© 2024 LogistiPro Indonesia <span>v1.0.0</span></div>
      </div>
      <section className="login-card">
        <div className="login-brand"><div className="small-logo">L<span>/</span>P</div><strong>Logisti<span>Pro</span></strong></div>
        <div className="login-heading">
          <p className="eyebrow">REGISTRASI PENGGUNA</p>
          <h2>Buat akun baru</h2>
          <p>Isi data berikut untuk mulai menggunakan sistem.</p>
        </div>
        <form onSubmit={submit}>
          <label>Nama lengkap
            <input data-testid="register-fullname" required value={form.full_name} onChange={change("full_name")} placeholder="Nama Anda" />
          </label>
          <label>Email kerja
            <input data-testid="register-email" type="email" required value={form.email} onChange={change("email")} placeholder="nama@perusahaan.com" />
          </label>
          <label>Password
            <input data-testid="register-password" type="password" required value={form.password} onChange={change("password")} placeholder="Minimal 6 karakter" />
          </label>
          {err && <div className="form-error" data-testid="register-error">{err}</div>}
          <button className="primary-button" style={{ marginTop: 25 }} data-testid="register-submit" disabled={loading}>
            {loading ? "Memproses..." : "Daftar Sekarang"} <span>→</span>
          </button>
        </form>
        <p style={{ textAlign: "center", fontSize: 11, color: "#64748b", marginTop: 20 }}>
          Sudah punya akun? <Link to="/login" className="link-btn" data-testid="goto-login">Masuk di sini</Link>
        </p>
      </section>
    </main>
  );
}
