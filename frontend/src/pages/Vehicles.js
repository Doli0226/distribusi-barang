import { useEffect, useState } from "react";
import { api } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import StatusBadge from "@/components/ui/StatusBadge";

const empty = { plate_number: "", vehicle_type: "", brand: "", capacity: "", status: "available", note: "" };

export default function Vehicles() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [modal, setModal] = useState(null);
  const load = () => api.get("/vehicles").then((r) => setItems(r.data.items));
  useEffect(() => { load(); }, []);
  const save = async () => {
    try {
      if (modal.editing) await api.put(`/vehicles/${modal.editing}`, modal.form);
      else await api.post("/vehicles", modal.form);
      toast.show("Kendaraan tersimpan", "success"); setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">ARMADA</p><h1>Manajemen kendaraan</h1><p className="subtitle">Kelola armada distribusi.</p></div>
        <button className="primary-button compact" onClick={() => setModal({ form: { ...empty }, editing: null })} data-testid="add-vehicle-button">＋ Tambah kendaraan</button>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>PLAT</th><th>JENIS</th><th>MERK</th><th>KAPASITAS</th><th>STATUS</th><th>KETERANGAN</th><th></th></tr></thead>
            <tbody>{items.map((v) => (
              <tr key={v.id} data-testid={`vehicle-row-${v.plate_number.replace(/\s/g, "")}`}>
                <td><b className="request-id">{v.plate_number}</b></td>
                <td>{v.vehicle_type}</td><td>{v.brand}</td><td>{v.capacity}</td>
                <td><StatusBadge status={v.status} /></td><td>{v.note || "-"}</td>
                <td><div className="row-actions">
                  <button onClick={() => setModal({ form: { ...v }, editing: v.id })}>Edit</button>
                </div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow="KENDARAAN" title={modal.editing ? "Edit kendaraan" : "Kendaraan baru"}>
          <div className="two-col-form">
            <label>Nomor plat<input required data-testid="veh-plate" value={modal.form.plate_number} onChange={(e) => setModal({ ...modal, form: { ...modal.form, plate_number: e.target.value } })} /></label>
            <label>Jenis<input required data-testid="veh-type" value={modal.form.vehicle_type} onChange={(e) => setModal({ ...modal, form: { ...modal.form, vehicle_type: e.target.value } })} /></label>
            <label>Merk<input data-testid="veh-brand" value={modal.form.brand} onChange={(e) => setModal({ ...modal, form: { ...modal.form, brand: e.target.value } })} /></label>
            <label>Kapasitas<input data-testid="veh-capacity" value={modal.form.capacity} onChange={(e) => setModal({ ...modal, form: { ...modal.form, capacity: e.target.value } })} /></label>
            <label>Status<select data-testid="veh-status" value={modal.form.status} onChange={(e) => setModal({ ...modal, form: { ...modal.form, status: e.target.value } })}>
              <option value="available">Tersedia</option><option value="in_use">Digunakan</option><option value="maintenance">Perawatan</option>
            </select></label>
          </div>
          <label>Keterangan<textarea data-testid="veh-note" value={modal.form.note} onChange={(e) => setModal({ ...modal, form: { ...modal.form, note: e.target.value } })} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={save} data-testid="veh-save">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
