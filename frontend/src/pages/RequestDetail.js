import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import Modal from "@/components/ui/Modal";
import StatusBadge from "@/components/ui/StatusBadge";
import { formatNumber } from "@/constants/status";

export default function RequestDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { isAdmin } = useAuth();
  const toast = useToast();
  const [req, setReq] = useState(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [distOpen, setDistOpen] = useState(false);
  const [vehicles, setVehicles] = useState([]);
  const [distForm, setDistForm] = useState({ vehicle_id: "", delivery_number: "", estimated_arrival: "", note: "" });

  const load = () => api.get(`/requests/${id}`).then((r) => setReq(r.data));
  useEffect(() => { load(); api.get("/vehicles").then((r) => setVehicles(r.data.items)); }, [id]);

  const doAction = async (action, extra = {}) => {
    try {
      const r = await api.post(`/requests/${id}/action`, { action, ...extra });
      toast.show(r.data.message, "success"); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  const createDist = async () => {
    try {
      const r = await api.post("/distributions", { request_id: Number(id), ...distForm });
      toast.show(`Distribusi ${r.data.number} dibuat`, "success");
      setDistOpen(false); nav(`/distribusi/${r.data.id}`);
    } catch (e) { toast.show(e.message, "danger"); }
  };

  if (!req) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">DETAIL PERMINTAAN</p>
          <h1 style={{ display: "flex", gap: 12, alignItems: "center" }}>{req.number} <StatusBadge status={req.status} /></h1>
          <p className="subtitle">{req.created_at} · dibuat oleh {req.requester_name}</p>
        </div>
        <Link to="/permintaan" className="outline-button" data-testid="back-to-requests">← Kembali</Link>
      </div>
      <div className="detail-grid">
        <section className="panel">
          <div className="panel-head"><div><h3>Informasi permintaan</h3><p>Detail item, tujuan, dan catatan.</p></div></div>
          <div className="info-list">
            <div><p>PEMOHON</p><b>{req.requester_name}</b></div>
            <div><p>GUDANG</p><b>{req.warehouse_name}</b></div>
            <div><p>PENERIMA</p><b>{req.recipient_name}</b></div>
            <div><p>TANGGAL DIBUTUHKAN</p><b>{req.needed_date || "-"}</b></div>
            <div style={{ gridColumn: "span 2" }}><p>TUJUAN</p><b>{req.destination}</b></div>
            {req.note && <div style={{ gridColumn: "span 2" }}><p>CATATAN</p><b>{req.note}</b></div>}
            {req.rejection_reason && <div style={{ gridColumn: "span 2" }}><p>ALASAN PENOLAKAN</p><b style={{ color: "#dc2626" }}>{req.rejection_reason}</b></div>}
          </div>

          <div className="table-scroll" style={{ marginTop: 20 }}><table>
            <thead><tr><th>SKU</th><th>BARANG</th><th>JUMLAH</th></tr></thead>
            <tbody>{req.items.map((it, i) => (
              <tr key={i}><td><b className="request-id">{it.product_sku}</b></td>
                <td>{it.product_name}</td><td><strong>{formatNumber(it.quantity)}</strong> {it.unit}</td></tr>
            ))}</tbody>
          </table></div>

          {isAdmin && (
            <div className="modal-actions" style={{ marginTop: 24, justifyContent: "flex-start", gap: 8 }}>
              {req.status === "pending" && (<>
                <button className="primary-button compact" onClick={() => doAction("approve")} data-testid="approve-request">Setujui</button>
                <button className="outline-button" style={{ borderColor: "#dc2626", color: "#dc2626" }} onClick={() => setRejectOpen(true)} data-testid="reject-request">Tolak</button>
                <button className="outline-button" onClick={() => doAction("process")}>Tandai Diproses</button>
              </>)}
              {req.status === "approved" && !req.distribution_number && (
                <button className="primary-button compact" onClick={() => setDistOpen(true)} data-testid="create-distribution">Buat Distribusi</button>
              )}
              {req.distribution_number && (
                <Link to={`/distribusi`} className="link-btn">Lihat distribusi {req.distribution_number} →</Link>
              )}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-head"><div><h3>Timeline</h3><p>Alur permintaan hingga selesai.</p></div></div>
          <div className="timeline" data-testid="request-timeline">
            {req.timeline.map((t, i) => (
              <div key={i} className={`timeline-item ${t.status === "done" ? "done" : ""}`}>
                <b>{t.label}</b>
                {t.at && <small>{t.at}</small>}
                {t.note && <span>{t.note}</span>}
              </div>
            ))}
          </div>
        </section>
      </div>

      {rejectOpen && (
        <Modal onClose={() => setRejectOpen(false)} eyebrow="TOLAK PERMINTAAN" title="Alasan penolakan">
          <label>Alasan<textarea required data-testid="reject-reason-input" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setRejectOpen(false)}>Batal</button>
            <button className="primary-button" style={{ background: "#dc2626", boxShadow: "0 3px 8px #dc262640" }}
                    onClick={() => { doAction("reject", { reason: rejectReason }); setRejectOpen(false); }} data-testid="reject-confirm">Tolak</button>
          </div>
        </Modal>
      )}

      {distOpen && (
        <Modal onClose={() => setDistOpen(false)} eyebrow="DISTRIBUSI" title="Buat distribusi" subtitle="Tentukan kendaraan dan detail pengiriman.">
          <div className="two-col-form">
            <label>Kendaraan<select data-testid="dist-vehicle" value={distForm.vehicle_id} onChange={(e) => setDistForm({ ...distForm, vehicle_id: e.target.value })}>
              <option value="">- pilih -</option>
              {vehicles.filter((v) => v.status === "available").map((v) => <option key={v.id} value={v.id}>{v.plate_number} · {v.vehicle_type}</option>)}
            </select></label>
            <label>Nomor resi<input data-testid="dist-delivery" value={distForm.delivery_number} onChange={(e) => setDistForm({ ...distForm, delivery_number: e.target.value })} placeholder="Opsional" /></label>
            <label>Estimasi tiba<input type="date" data-testid="dist-eta" value={distForm.estimated_arrival} onChange={(e) => setDistForm({ ...distForm, estimated_arrival: e.target.value })} /></label>
          </div>
          <label>Catatan<textarea data-testid="dist-note" value={distForm.note} onChange={(e) => setDistForm({ ...distForm, note: e.target.value })} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setDistOpen(false)}>Batal</button>
            <button className="primary-button" onClick={createDist} data-testid="dist-save">Buat distribusi <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
