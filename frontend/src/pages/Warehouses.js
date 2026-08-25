import { useEffect, useState } from "react";
import { api } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import StatusBadge from "@/components/ui/StatusBadge";

const empty = { code: "", name: "", location: "", city: "", capacity: 0, active: true };

export default function Warehouses() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [modal, setModal] = useState(null);
  const load = () => api.get("/warehouses").then((r) => setItems(r.data.items));
  useEffect(() => { load(); }, []);
  const save = async () => {
    try {
      if (modal.editing) await api.put(`/warehouses/${modal.editing}`, modal.form);
      else await api.post("/warehouses", modal.form);
      toast.show("Gudang tersimpan", "success"); setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">INFRASTRUKTUR</p><h1>Manajemen gudang</h1><p className="subtitle">Kelola lokasi dan kapasitas gudang.</p></div>
        <button className="primary-button compact" onClick={() => setModal({ form: { ...empty }, editing: null })} data-testid="add-warehouse-button">＋ Tambah gudang</button>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>KODE</th><th>NAMA</th><th>LOKASI</th><th>KOTA</th><th>KAPASITAS</th><th>STATUS</th><th></th></tr></thead>
            <tbody>{items.map((w) => (
              <tr key={w.id} data-testid={`warehouse-row-${w.code}`}>
                <td><b className="request-id">{w.code}</b></td><td><strong>{w.name}</strong></td>
                <td>{w.location}</td><td>{w.city}</td><td>{w.capacity}</td>
                <td><StatusBadge status={w.active ? "Aktif" : "Nonaktif"} /></td>
                <td><div className="row-actions">
                  <button onClick={() => setModal({ form: { ...w }, editing: w.id })} data-testid={`edit-warehouse-${w.code}`}>Edit</button>
                  {w.active && <button className="danger" onClick={async () => { await api.delete(`/warehouses/${w.id}`); toast.show("Dinonaktifkan", "success"); load(); }}>Nonaktifkan</button>}
                </div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow="GUDANG" title={modal.editing ? "Edit gudang" : "Gudang baru"}>
          <div className="two-col-form">
            <label>Kode<input required data-testid="wh-code" value={modal.form.code} onChange={(e) => setModal({ ...modal, form: { ...modal.form, code: e.target.value } })} /></label>
            <label>Nama<input required data-testid="wh-name" value={modal.form.name} onChange={(e) => setModal({ ...modal, form: { ...modal.form, name: e.target.value } })} /></label>
            <label>Kota<input data-testid="wh-city" value={modal.form.city} onChange={(e) => setModal({ ...modal, form: { ...modal.form, city: e.target.value } })} /></label>
            <label>Kapasitas<input type="number" data-testid="wh-capacity" value={modal.form.capacity} onChange={(e) => setModal({ ...modal, form: { ...modal.form, capacity: Number(e.target.value) } })} /></label>
          </div>
          <label>Alamat<textarea data-testid="wh-location" value={modal.form.location} onChange={(e) => setModal({ ...modal, form: { ...modal.form, location: e.target.value } })} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={save} data-testid="wh-save">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
