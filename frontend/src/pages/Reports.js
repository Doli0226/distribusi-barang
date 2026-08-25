import { useEffect, useState } from "react";
import { api, download } from "@/api";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import { formatNumber } from "@/constants/status";

const KINDS = [
  { key: "stock", label: "Laporan stok" },
  { key: "stock_transactions", label: "Riwayat mutasi stok" },
  { key: "requests", label: "Laporan permintaan" },
  { key: "distributions", label: "Laporan distribusi" },
];

export default function Reports() {
  const toast = useToast();
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [data, setData] = useState(null);

  const load = async () => {
    const p = new URLSearchParams();
    if (start) p.set("start", start); if (end) p.set("end", end);
    const r = await api.get(`/reports/summary?${p.toString()}`);
    setData(r.data);
  };
  useEffect(() => { load(); }, []);

  const exportFile = async (kind, fmt) => {
    try {
      const filename = `${kind}-${new Date().toISOString().slice(0, 10)}.${fmt === "excel" ? "xlsx" : fmt}`;
      await download(`/reports/${kind}/export/${fmt}`, filename);
      toast.show(`Diunduh ${filename}`, "success");
    } catch (e) { toast.show(e.message, "danger"); }
  };
  const doPrint = () => window.print();

  if (!data) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">LAPORAN</p><h1>Laporan operasional</h1><p className="subtitle">Ekspor data ke PDF, Excel, CSV atau cetak langsung.</p></div>
      </div>
      <section className="panel product-page">
        <div className="print-only print-header">
          <b>Laporan Operasional — LogistiPro Indonesia</b>
          <p>Periode: {start || "awal"} s/d {end || "sekarang"} · Dicetak {new Date().toLocaleString("id-ID")}</p>
        </div>
        <div className="filter-bar">
          <label style={{ fontSize: 11, color: "#64748b" }}>Dari<input type="date" data-testid="report-start" value={start} onChange={(e) => setStart(e.target.value)} style={{ marginLeft: 6 }} /></label>
          <label style={{ fontSize: 11, color: "#64748b" }}>Sampai<input type="date" data-testid="report-end" value={end} onChange={(e) => setEnd(e.target.value)} style={{ marginLeft: 6 }} /></label>
          <button className="outline-button" onClick={load} data-testid="apply-filter">Terapkan filter</button>
          <button className="outline-button" onClick={doPrint} data-testid="print-button">Cetak halaman</button>
        </div>
        <div className="grid-6" style={{ marginTop: 22 }}>
          <div className="stat-card"><p>Total permintaan</p><strong>{formatNumber(data.requests_total)}</strong><small>disetujui: {data.requests_approved}</small></div>
          <div className="stat-card"><p>Distribusi</p><strong>{formatNumber(data.distributions_total)}</strong><small>selesai: {data.distributions_completed}</small></div>
          <div className="stat-card"><p>Stok masuk</p><strong>{formatNumber(data.stock_in)}</strong></div>
          <div className="stat-card"><p>Stok keluar</p><strong>{formatNumber(data.stock_out)}</strong></div>
        </div>

        <div className="panel-head" style={{ marginTop: 24 }}><div><h3>Barang paling banyak didistribusikan</h3></div></div>
        <div className="table-scroll"><table>
          <thead><tr><th>SKU</th><th>NAMA</th><th>TOTAL DIMINTA</th></tr></thead>
          <tbody>{data.top_products.map((p) => (
            <tr key={p.sku}><td><b className="request-id">{p.sku}</b></td><td>{p.name}</td><td><strong>{formatNumber(p.total)}</strong></td></tr>
          ))}</tbody>
        </table></div>

        <div className="panel-head" style={{ marginTop: 30 }}><div><h3>Export data</h3><p>Unduh laporan lengkap</p></div></div>
        <div className="card-list">
          {KINDS.map((k) => (
            <article key={k.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div><h4>{k.label}</h4><p>Ekspor data {k.label.toLowerCase()} dalam berbagai format.</p></div>
              <div className="export-buttons">
                <button onClick={() => exportFile(k.key, "csv")} data-testid={`export-${k.key}-csv`}>CSV</button>
                <button onClick={() => exportFile(k.key, "excel")} data-testid={`export-${k.key}-excel`}>Excel</button>
                <button onClick={() => exportFile(k.key, "pdf")} data-testid={`export-${k.key}-pdf`}>PDF</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
