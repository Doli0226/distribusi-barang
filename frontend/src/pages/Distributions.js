import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Truck } from "lucide-react";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import StatusBadge from "@/components/ui/StatusBadge";

const STATUS = ["prepared", "in_transit", "arrived", "completed"];

export default function Distributions() {
  const { isAdmin } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [items, setItems] = useState(null);
  const [status, setStatus] = useState("");
  const load = () => api.get("/distributions").then((r) => setItems(r.data.items));
  useEffect(() => { load(); }, []);

  const updateStatus = async (id, newStatus) => {
    try {
      await api.post(`/distributions/${id}/status`, { status: newStatus });
      toast.show("Status diperbarui", "success"); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };

  if (items === null) return <Loading />;
  const list = items.filter((i) => !status || i.status === status);
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">DISTRIBUSI</p><h1>Distribusi & pengiriman</h1><p className="subtitle">Pantau seluruh pengiriman.</p></div>
      </div>
      <section className="panel product-page">
        <div className="filter-bar">
          <select data-testid="dist-status-filter" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Semua status</option>
            {STATUS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        {list.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>NO. DISTRIBUSI</th><th>PERMINTAAN</th><th>GUDANG</th><th>TUJUAN</th><th>KENDARAAN</th><th>STATUS</th><th>ETA</th><th></th></tr></thead>
            <tbody>{list.map((d) => (
              <tr key={d.id} data-testid={`dist-row-${d.number}`}>
                <td><b className="request-id">{d.number}</b></td>
                <td>{d.request_number}</td>
                <td>{d.warehouse_name}</td>
                <td>{d.destination}</td>
                <td>{d.vehicle_plate || "-"}</td>
                <td><StatusBadge status={d.status} /></td>
                <td>{d.estimated_arrival || "-"}</td>
                <td><div className="row-actions">
                  <button onClick={() => nav(`/distribusi/${d.id}`)} data-testid={`view-dist-${d.number}`}>Detail</button>
                  {isAdmin && d.status !== "completed" && (
                    <select className="filter-button" data-testid={`dist-set-status-${d.number}`} onChange={(e) => e.target.value && updateStatus(d.id, e.target.value)} value="">
                      <option value="">Ubah status</option>
                      {STATUS.filter((s) => s !== d.status).map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  )}
                </div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
    </>
  );
}
