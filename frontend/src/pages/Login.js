import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";

export default function Login() {
  const { login } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [email, setEmail] = useState("admin@logistipro.id");
  const [password, setPassword] = useState("admin123");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const u = await login(email, password);
      toast.show(`Selamat datang, ${u.full_name || u.username}`, "success");
      nav("/dashboard");
    } catch (err) {
      setError(err.message || "Login gagal");
    } finally { setLoading(false); }
  };

  return (
    <main className="login-page">
      <div className="login-visual">
        <div className="brand-mark">L<span>/</span>P</div>
        <div className="visual-copy">
          <p className="eyebrow">DISTRIBUTION CONTROL CENTER</p>
          <h1>Semua kiriman,<br /><em>terkendali.</em></h1>
          <p>Pantau inventori, kelola permintaan, dan pastikan distribusi tiba tepat waktu.</p>
        </div>
        <div className="visual-footer">© 2024 LogistiPro Indonesia <span>v1.0.0</span></div>
      </div>
      <section className="login-card">
        <div className="login-brand"><div className="small-logo">L<span>/</span>P</div><strong>Logisti<span>Pro</span></strong></div>
        <div className="login-heading">
          <p className="eyebrow">SELAMAT DATANG KEMBALI</p>
          <h2>Masuk ke workspace</h2>
          <p>Kelola operasional distribusi Anda dengan lebih cerdas.</p>
        </div>
        <form onSubmit={submit}>
          <label>Email kerja
            <input data-testid="login-email-input" type="email" placeholder="nama@perusahaan.com"
                   value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>Password
            <div className="password-input">
              <input data-testid="login-password-input" type={show ? "text" : "password"} placeholder="••••••••"
                     value={password} onChange={(e) => setPassword(e.target.value)} required />
              <span onClick={() => setShow((x) => !x)} style={{ cursor: "pointer" }} data-testid="toggle-password">
                {show ? "Sembunyikan" : "Tampilkan"}
              </span>
            </div>
          </label>
          {error && <div className="form-error" data-testid="login-error">{error}</div>}
          <div className="form-row">
            <label className="check"><input type="checkbox" defaultChecked /> Ingat saya</label>
            <Link to="/reset-password" data-testid="reset-password-link">Lupa password?</Link>
          </div>
          <button className="primary-button" data-testid="login-submit-button" disabled={loading}>
            {loading ? "Memproses..." : "Masuk ke Dashboard"} <span>→</span>
          </button>
        </form>
        <p className="login-hint">
          Demo: <b>admin@logistipro.id</b> / admin123 · <b>user@logistipro.id</b> / user123
        </p>
        <p style={{ textAlign: "center", fontSize: 11, color: "#64748b", marginTop: 14 }}>
          Belum punya akun? <Link to="/register" className="link-btn" data-testid="goto-register">Daftar sekarang</Link>
        </p>
      </section>
    </main>
  );
}
