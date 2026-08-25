import { useEffect, useState } from "react";
import { api } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";

const empty = { full_name: "", email: "", password: "", phone: "", role: "user" };

export default function Users() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [modal, setModal] = useState(null);
  const load = () => api.get("/users").then((r) => setItems(r.data.items));
  useEffect(() => { load(); }, []);
  const save = async () => {
    try {
      await api.post("/users", modal);
      toast.show("Pengguna dibuat", "success"); setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">USER MANAGEMENT</p><h1>Manajemen pengguna</h1><p className="subtitle">Kelola akses admin dan user.</p></div>
        <button className="primary-button compact" onClick={() => setModal({ ...empty })} data-testid="add-user-button">＋ Tambah pengguna</button>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>NAMA</th><th>EMAIL</th><th>ROLE</th><th>STATUS</th><th>DAFTAR</th></tr></thead>
            <tbody>{items.map((u) => (
              <tr key={u.id} data-testid={`user-row-${u.id}`}>
                <td><strong>{u.full_name}</strong></td>
                <td>{u.email}</td>
                <td><span className={`pill ${u.role === "admin" ? "blue" : "green"}`}>{u.role}</span></td>
                <td><span className={`badge ${u.is_active ? "green" : "gray"}`}>{u.is_active ? "Aktif" : "Nonaktif"}</span></td>
                <td>{u.date_joined}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow="PENGGUNA" title="Pengguna baru">
          <div className="two-col-form">
            <label>Nama lengkap<input required data-testid="user-fullname" value={modal.full_name} onChange={(e) => setModal({ ...modal, full_name: e.target.value })} /></label>
            <label>Email<input required type="email" data-testid="user-email" value={modal.email} onChange={(e) => setModal({ ...modal, email: e.target.value })} /></label>
            <label>Password<input required type="password" data-testid="user-password" value={modal.password} onChange={(e) => setModal({ ...modal, password: e.target.value })} /></label>
            <label>Telepon<input data-testid="user-phone" value={modal.phone} onChange={(e) => setModal({ ...modal, phone: e.target.value })} /></label>
            <label>Role<select data-testid="user-role" value={modal.role} onChange={(e) => setModal({ ...modal, role: e.target.value })}>
              <option value="user">User</option><option value="admin">Admin</option>
            </select></label>
          </div>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={save} data-testid="user-save">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
