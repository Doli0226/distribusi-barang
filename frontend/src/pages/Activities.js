import { useEffect, useState } from "react";
import { api } from "@/api";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";

export default function Activities() {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get("/activities").then((r) => setItems(r.data.items)); }, []);
  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">AUDIT TRAIL</p><h1>Aktivitas sistem</h1><p className="subtitle">Catatan semua aksi penting.</p></div>
      </div>
      <section className="panel product-page">
        {items.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>WAKTU</th><th>USER</th><th>AKSI</th><th>ENTITAS</th><th>DETAIL</th><th>IP</th></tr></thead>
            <tbody>{items.map((a) => (
              <tr key={a.id} data-testid={`activity-row-${a.id}`}>
                <td>{a.created_at}</td>
                <td><b>{a.user}</b></td>
                <td><span className="pill blue">{a.action}</span></td>
                <td>{a.entity} {a.entity_id && `#${a.entity_id}`}</td>
                <td>{a.detail || "-"}</td>
                <td style={{ fontFamily: "DM Mono", fontSize: 10 }}>{a.ip_address}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
    </>
  );
}
