import { useEffect, useState } from "react";
import { Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import StatusBadge from "@/components/ui/StatusBadge";

export default function Tracking() {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get("/tracking").then((r) => setItems(r.data.items)); }, []);
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">TRACKING</p><h1>Tracking distribusi</h1><p className="subtitle">Pantau distribusi yang sedang berjalan.</p></div>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState desc="Tidak ada distribusi yang sedang berjalan." /> : (
          <div className="tracking-list">
            {items.map((d) => (
              <div className="tracking-row" key={d.id} data-testid={`tracking-row-${d.number}`}>
                <div className="truck-circle"><Truck size={19} /></div>
                <div className="tracking-info">
                  <b>{d.number} <StatusBadge status={d.status} /></b>
                  <strong>{d.origin} → {d.destination}</strong>
                  <small>{d.items_summary || "-"}</small>
                  <div className="progress"><i style={{ width: `${d.progress}%` }} /></div>
                </div>
                <Link to={`/distribusi/${d.id}`} className="text-button">Detail →</Link>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
