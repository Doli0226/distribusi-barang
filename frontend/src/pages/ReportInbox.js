import { useEffect, useState } from "react";
import { Download, FileBox } from "lucide-react";
import { api, download } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";

const kb = (n) => (n < 1024 ? `${n} B` : `${(n / 1024).toFixed(1)} KB`);

export default function ReportInbox() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const load = () => api.get("/generated-reports").then((r) => setData(r.data));
  useEffect(() => { load(); }, []);
  const doDownload = async (r) => {
    try { await download(`/generated-reports/${r.id}/download`, r.filename); toast.show(`Diunduh ${r.filename}`, "success"); load(); }
    catch (e) { toast.show(e.message, "danger"); }
  };
  if (!data) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">INBOX</p><h1>Inbox laporan</h1>
          <p className="subtitle">{data.unread} laporan belum diunduh. Setiap jadwal yang jatuh tempo akan otomatis muncul di sini.</p>
        </div>
      </div>
      <section className="panel product-page">
        {data.items.length === 0 ? <EmptyState desc="Belum ada laporan. Buat jadwal di halaman 'Jadwal Laporan' atau jalankan manual." /> : (
          <div className="card-list">
            {data.items.map((r) => (
              <article key={r.id} data-testid={`inbox-item-${r.id}`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
                  <div style={{ width: 42, height: 42, borderRadius: 10, background: "#eff6ff", color: "#2563eb", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <FileBox size={20} />
                  </div>
                  <div>
                    <h4>{r.filename} {!r.downloaded && <span className="pill blue" style={{ marginLeft: 6 }}>Baru</span>}</h4>
                    <p>{r.schedule_name} · {r.format.toUpperCase()} · {kb(r.size)} · {r.created_at}</p>
                  </div>
                </div>
                <button className="outline-button" onClick={() => doDownload(r)} data-testid={`download-${r.id}`}>
                  <Download size={13} style={{ marginRight: 6, verticalAlign: -2 }} /> Unduh
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
