import { useEffect, useState } from "react";
import { api } from "@/api";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";

export default function Notifications() {
  const [data, setData] = useState(null);
  const load = () => api.get("/notifications").then((r) => setData(r.data));
  useEffect(() => { load(); }, []);
  const markAll = async () => { await api.post("/notifications", { mark_all: true }); load(); window.dispatchEvent(new Event("notifs:refresh")); };
  if (!data) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">NOTIFIKASI</p><h1>Notifikasi</h1><p className="subtitle">{data.unread} belum dibaca.</p></div>
        {data.unread > 0 && <button className="outline-button" onClick={markAll} data-testid="mark-all-page">Tandai semua dibaca</button>}
      </div>
      <section className="panel product-page">
        {data.items.length === 0 ? <EmptyState /> : (
          <div className="card-list">
            {data.items.map((n) => (
              <article key={n.id} style={n.read ? {} : { borderLeft: "4px solid #2563eb" }} data-testid={`notif-item-${n.id}`}>
                <h4>{n.title} {!n.read && <span className="pill blue" style={{ marginLeft: 8 }}>Baru</span>}</h4>
                <p>{n.message}</p>
                <small style={{ color: "#94a3b8", fontSize: 10 }}>{n.created_at}</small>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
