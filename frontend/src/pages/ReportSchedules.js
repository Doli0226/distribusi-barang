import { useEffect, useState } from "react";
import { api } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";

const KINDS = [
  { key: "stock", label: "Laporan Stok" },
  { key: "stock_transactions", label: "Riwayat Mutasi Stok" },
  { key: "requests", label: "Laporan Permintaan" },
  { key: "distributions", label: "Laporan Distribusi" },
];
const FREQ = [
  { key: "daily", label: "Harian" },
  { key: "weekly", label: "Mingguan" },
  { key: "monthly", label: "Bulanan" },
];
const DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];

const empty = { name: "", kind: "stock", format: "pdf", frequency: "monthly", day_of_month: 1, day_of_week: 0, active: true };

export default function ReportSchedules() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [modal, setModal] = useState(null);
  const load = () => api.get("/report-schedules").then((r) => setItems(r.data.items));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!modal.form.name) return toast.show("Nama wajib", "danger");
    try {
      if (modal.editing) await api.put(`/report-schedules/${modal.editing}`, modal.form);
      else await api.post("/report-schedules", modal.form);
      toast.show("Jadwal tersimpan", "success"); setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  const runNow = async (id) => {
    try { const r = await api.post(`/report-schedules/${id}/run`); toast.show(`${r.data.filename} siap di inbox`, "success"); load(); }
    catch (e) { toast.show(e.message, "danger"); }
  };
  const remove = async (id) => {
    if (!window.confirm("Hapus jadwal ini?")) return;
    try { await api.delete(`/report-schedules/${id}`); toast.show("Jadwal dihapus", "success"); load(); }
    catch (e) { toast.show(e.message, "danger"); }
  };
  const toggle = async (s) => {
    try { await api.put(`/report-schedules/${s.id}`, { active: !s.active }); load(); }
    catch (e) { toast.show(e.message, "danger"); }
  };
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">OTOMASI</p><h1>Jadwal laporan</h1>
          <p className="subtitle">Setelan laporan berulang. Setiap kali jadwal jatuh tempo, laporan otomatis dibuat dan masuk ke Inbox.</p>
        </div>
        <button className="primary-button compact" onClick={() => setModal({ form: { ...empty }, editing: null })} data-testid="add-schedule-button">＋ Buat jadwal</button>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState desc="Belum ada jadwal laporan. Buat satu untuk mendapatkan laporan berulang di Inbox." /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>NAMA</th><th>JENIS</th><th>FORMAT</th><th>FREKUENSI</th><th>TERAKHIR</th><th>BERIKUTNYA</th><th>STATUS</th><th></th></tr></thead>
            <tbody>{items.map((s) => (
              <tr key={s.id} data-testid={`schedule-row-${s.id}`}>
                <td><strong>{s.name}</strong></td>
                <td>{KINDS.find((k) => k.key === s.kind)?.label || s.kind}</td>
                <td><span className="pill blue">{s.format.toUpperCase()}</span></td>
                <td>{FREQ.find((f) => f.key === s.frequency)?.label}
                  {s.frequency === "monthly" && <small className="table-sub">Tanggal {s.day_of_month}, jam 08.00</small>}
                  {s.frequency === "weekly" && <small className="table-sub">{DAYS[s.day_of_week]}, jam 08.00</small>}
                  {s.frequency === "daily" && <small className="table-sub">Setiap hari, jam 08.00</small>}
                </td>
                <td>{s.last_run_at || "-"}</td>
                <td>{s.next_run_at}</td>
                <td><span className={`badge ${s.active ? "green" : "gray"}`}>{s.active ? "Aktif" : "Nonaktif"}</span></td>
                <td><div className="row-actions">
                  <button onClick={() => runNow(s.id)} data-testid={`run-schedule-${s.id}`}>Jalankan</button>
                  <button onClick={() => setModal({ form: { ...s }, editing: s.id })} data-testid={`edit-schedule-${s.id}`}>Edit</button>
                  <button onClick={() => toggle(s)}>{s.active ? "Nonaktifkan" : "Aktifkan"}</button>
                  <button className="danger" onClick={() => remove(s.id)}>Hapus</button>
                </div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow="JADWAL" title={modal.editing ? "Edit jadwal" : "Jadwal baru"} subtitle="Laporan dibuat otomatis setiap jadwal jatuh tempo, dan muncul di Inbox Laporan.">
          <div className="two-col-form">
            <label>Nama<input required data-testid="sch-name" value={modal.form.name} onChange={(e) => setModal({ ...modal, form: { ...modal.form, name: e.target.value } })} /></label>
            <label>Jenis laporan<select data-testid="sch-kind" value={modal.form.kind} onChange={(e) => setModal({ ...modal, form: { ...modal.form, kind: e.target.value } })}>
              {KINDS.map((k) => <option key={k.key} value={k.key}>{k.label}</option>)}
            </select></label>
            <label>Format<select data-testid="sch-format" value={modal.form.format} onChange={(e) => setModal({ ...modal, form: { ...modal.form, format: e.target.value } })}>
              <option value="pdf">PDF</option><option value="excel">Excel</option><option value="csv">CSV</option>
            </select></label>
            <label>Frekuensi<select data-testid="sch-freq" value={modal.form.frequency} onChange={(e) => setModal({ ...modal, form: { ...modal.form, frequency: e.target.value } })}>
              {FREQ.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select></label>
            {modal.form.frequency === "monthly" && (
              <label>Tanggal (1-28)<input type="number" min={1} max={28} data-testid="sch-dom" value={modal.form.day_of_month} onChange={(e) => setModal({ ...modal, form: { ...modal.form, day_of_month: Number(e.target.value) } })} /></label>
            )}
            {modal.form.frequency === "weekly" && (
              <label>Hari<select data-testid="sch-dow" value={modal.form.day_of_week} onChange={(e) => setModal({ ...modal, form: { ...modal.form, day_of_week: Number(e.target.value) } })}>
                {DAYS.map((d, i) => <option key={i} value={i}>{d}</option>)}
              </select></label>
            )}
          </div>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={save} data-testid="sch-save">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
