import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import StatusBadge from "@/components/ui/StatusBadge";
import { statusLabel } from "@/constants/status";

const STATUS_FLOW = ["prepared", "in_transit", "arrived", "completed"];

export default function DistributionDetail() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const toast = useToast();
  const [d, setD] = useState(null);
  const load = () => api.get(`/distributions/${id}`).then((r) => setD(r.data));
  useEffect(() => { load(); }, [id]);

  const update = async (s) => {
    try { await api.post(`/distributions/${id}/status`, { status: s }); toast.show("Status diperbarui", "success"); load(); }
    catch (e) { toast.show(e.message, "danger"); }
  };
  if (!d) return <Loading />;
  const idx = STATUS_FLOW.indexOf(d.status);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">DETAIL DISTRIBUSI</p>
          <h1 style={{ display: "flex", gap: 12, alignItems: "center" }}>{d.number} <StatusBadge status={d.status} /></h1>
          <p className="subtitle">Dibuat {d.created_at} · dari {d.request_number}</p>
        </div>
        <Link to="/distribusi" className="outline-button" data-testid="back-to-dist">← Kembali</Link>
      </div>
      <div className="detail-grid">
        <section className="panel">
          <div className="panel-head"><div><h3>Informasi distribusi</h3></div></div>
          <div className="info-list">
            <div><p>GUDANG ASAL</p><b>{d.warehouse_name}</b></div>
            <div><p>PENERIMA</p><b>{d.recipient_name}</b></div>
            <div style={{ gridColumn: "span 2" }}><p>ALAMAT TUJUAN</p><b>{d.destination}</b></div>
            <div><p>KENDARAAN</p><b>{d.vehicle_plate || "-"}</b></div>
            <div><p>NOMOR RESI</p><b>{d.delivery_number || "-"}</b></div>
            <div><p>ESTIMASI TIBA</p><b>{d.estimated_arrival || "-"}</b></div>
            <div><p>DIKIRIM</p><b>{d.shipped_at || "-"}</b></div>
            <div><p>SELESAI</p><b>{d.completed_at || "-"}</b></div>
            {d.note && <div style={{ gridColumn: "span 2" }}><p>CATATAN</p><b>{d.note}</b></div>}
          </div>

          <div className="table-scroll" style={{ marginTop: 20 }}><table>
            <thead><tr><th>SKU</th><th>BARANG</th><th>JUMLAH</th></tr></thead>
            <tbody>{d.items.map((it, i) => (
              <tr key={i}><td><b className="request-id">{it.sku}</b></td><td>{it.name}</td><td>{it.quantity} {it.unit}</td></tr>
            ))}</tbody>
          </table></div>

          {isAdmin && d.status !== "completed" && (
            <div style={{ display: "flex", gap: 8, marginTop: 24, flexWrap: "wrap" }}>
              {STATUS_FLOW.slice(idx + 1).map((s) => (
                <button key={s} className="primary-button compact" onClick={() => update(s)} data-testid={`set-status-${s}`}>Set: {statusLabel(s)}</button>
              ))}
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-head"><div><h3>Timeline pengiriman</h3><p>Riwayat perubahan status.</p></div></div>
          <div className="progress-bar" style={{ marginTop: 16 }}>
            <i style={{ width: `${(Math.max(idx, 0) + 1) / STATUS_FLOW.length * 100}%` }} />
          </div>
          <div className="timeline" data-testid="dist-timeline">
            {STATUS_FLOW.map((s, i) => {
              const h = d.history.find((x) => x.status === s);
              return (
                <div key={s} className={`timeline-item ${i <= idx ? "done" : ""}`}>
                  <b>{statusLabel(s)}</b>
                  {h && <small>{h.created_at} · {h.user}</small>}
                  {h?.note && <span>{h.note}</span>}
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </>
  );
}
