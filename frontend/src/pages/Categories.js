import { useEffect, useState } from "react";
import { api } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import StatusBadge from "@/components/ui/StatusBadge";

export default function Categories() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [modal, setModal] = useState(null);
  const load = () => api.get("/categories").then((r) => setItems(r.data.items));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!modal.form.name) return toast.show("Nama wajib", "danger");
    try {
      if (modal.editing) await api.put(`/categories/${modal.editing}`, modal.form);
      else await api.post("/categories", modal.form);
      toast.show("Kategori tersimpan", "success"); setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">MASTER DATA</p><h1>Kategori barang</h1><p className="subtitle">Kelompokkan barang berdasarkan kategori.</p></div>
        <button className="primary-button compact" onClick={() => setModal({ form: { name: "", description: "", active: true }, editing: null })} data-testid="add-category-button">＋ Tambah kategori</button>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>NAMA</th><th>DESKRIPSI</th><th>STATUS</th><th></th></tr></thead>
            <tbody>{items.map((c) => (
              <tr key={c.id} data-testid={`category-row-${c.id}`}>
                <td><strong>{c.name}</strong></td><td>{c.description || "-"}</td>
                <td><StatusBadge status={c.active ? "Aktif" : "Nonaktif"} /></td>
                <td><div className="row-actions">
                  <button onClick={() => setModal({ form: { ...c }, editing: c.id })} data-testid={`edit-category-${c.id}`}>Edit</button>
                  {c.active && <button className="danger" onClick={async () => { await api.delete(`/categories/${c.id}`); load(); toast.show("Kategori dinonaktifkan", "success"); }} data-testid={`deact-category-${c.id}`}>Nonaktifkan</button>}
                </div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow="KATEGORI" title={modal.editing ? "Edit kategori" : "Kategori baru"}>
          <label>Nama<input required data-testid="category-name-input" value={modal.form.name} onChange={(e) => setModal({ ...modal, form: { ...modal.form, name: e.target.value } })} /></label>
          <label>Deskripsi<textarea data-testid="category-desc-input" value={modal.form.description} onChange={(e) => setModal({ ...modal, form: { ...modal.form, description: e.target.value } })} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={save} data-testid="category-save-button">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
