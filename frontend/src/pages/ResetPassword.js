import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/api";
import { useToast } from "@/context/ToastContext";

export default function ResetPassword() {
  const toast = useToast();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [pwd, setPwd] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setLoading(true);
    try {
      await api.post("/auth/reset-password", { email, new_password: pwd });
      toast.show("Password berhasil direset. Silakan login.", "success");
      nav("/login");
    } catch (er) { setErr(er.message); }
    finally { setLoading(false); }
  };
  return (
    <main className="login-page">
      <div className="login-visual">
        <div className="brand-mark">L<span>/</span>P</div>
        <div className="visual-copy">
          <p className="eyebrow">RESET PASSWORD</p>
          <h1>Atur ulang<br /><em>password Anda.</em></h1>
          <p>Reset demo langsung mengubah password akun.</p>
        </div>
        <div className="visual-footer">© 2024 LogistiPro Indonesia</div>
      </div>
      <section className="login-card">
        <div className="login-brand"><div className="small-logo">L<span>/</span>P</div><strong>Logisti<span>Pro</span></strong></div>
        <div className="login-heading">
          <p className="eyebrow">RESET</p>
          <h2>Reset password</h2>
        </div>
        <form onSubmit={submit}>
          <label>Email akun
            <input required type="email" data-testid="reset-email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>Password baru
            <input required type="password" minLength={6} data-testid="reset-new-password" value={pwd} onChange={(e) => setPwd(e.target.value)} />
          </label>
          {err && <div className="form-error" data-testid="reset-error">{err}</div>}
          <button className="primary-button" data-testid="reset-submit" style={{ marginTop: 25 }} disabled={loading}>
            {loading ? "Memproses..." : "Reset password"} <span>→</span>
          </button>
        </form>
        <p style={{ textAlign: "center", fontSize: 11, color: "#64748b", marginTop: 20 }}>
          <Link to="/login" className="link-btn">← Kembali login</Link>
        </p>
      </section>
    </main>
  );
}
