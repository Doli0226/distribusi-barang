import { useEffect, useState } from "react";
import { api } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import StatusBadge from "@/components/ui/StatusBadge";

const empty = { code: "", name: "", phone: "", email: "", address: "", city: "", province: "", active: true };

export default function Recipients() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [modal, setModal] = useState(null);
  const load = () => api.get("/recipients").then((r) => setItems(r.data.items));
  useEffect(() => { load(); }, []);
  const save = async () => {
    try {
      if (modal.editing) await api.put(`/recipients/${modal.editing}`, modal.form);
      else await api.post("/recipients", modal.form);
      toast.show("Penerima tersimpan", "success"); setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">MASTER DATA</p><h1>Data penerima</h1><p className="subtitle">Kelola daftar penerima untuk distribusi.</p></div>
        <button className="primary-button compact" onClick={() => setModal({ form: { ...empty }, editing: null })} data-testid="add-recipient-button">＋ Tambah penerima</button>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>KODE</th><th>NAMA</th><th>KONTAK</th><th>KOTA</th><th>PROVINSI</th><th>STATUS</th><th></th></tr></thead>
            <tbody>{items.map((r) => (
              <tr key={r.id} data-testid={`recipient-row-${r.code}`}>
                <td><b className="request-id">{r.code}</b></td>
                <td><strong>{r.name}</strong><small className="table-sub">{r.address}</small></td>
                <td>{r.phone}<small className="table-sub">{r.email}</small></td>
                <td>{r.city}</td><td>{r.province}</td>
                <td><StatusBadge status={r.active ? "Aktif" : "Nonaktif"} /></td>
                <td><div className="row-actions">
                  <button onClick={() => setModal({ form: { ...r }, editing: r.id })} data-testid={`edit-recipient-${r.code}`}>Edit</button>
                </div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow="PENERIMA" title={modal.editing ? "Edit penerima" : "Penerima baru"}>
          <div className="two-col-form">
            <label>Kode<input required data-testid="rec-code" value={modal.form.code} onChange={(e) => setModal({ ...modal, form: { ...modal.form, code: e.target.value } })} /></label>
            <label>Nama<input required data-testid="rec-name" value={modal.form.name} onChange={(e) => setModal({ ...modal, form: { ...modal.form, name: e.target.value } })} /></label>
            <label>Telepon<input data-testid="rec-phone" value={modal.form.phone} onChange={(e) => setModal({ ...modal, form: { ...modal.form, phone: e.target.value } })} /></label>
            <label>Email<input type="email" data-testid="rec-email" value={modal.form.email} onChange={(e) => setModal({ ...modal, form: { ...modal.form, email: e.target.value } })} /></label>
            <label>Kota<input required data-testid="rec-city" value={modal.form.city} onChange={(e) => setModal({ ...modal, form: { ...modal.form, city: e.target.value } })} /></label>
            <label>Provinsi<input required data-testid="rec-province" value={modal.form.province} onChange={(e) => setModal({ ...modal, form: { ...modal.form, province: e.target.value } })} /></label>
          </div>
          <label>Alamat<textarea required data-testid="rec-address" value={modal.form.address} onChange={(e) => setModal({ ...modal, form: { ...modal.form, address: e.target.value } })} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={save} data-testid="rec-save">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
