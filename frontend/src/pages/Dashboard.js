import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, ClipboardList, Package, Truck, Warehouse } from "lucide-react";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import StatusBadge from "@/components/ui/StatusBadge";
import { formatNumber } from "@/constants/status";

const Stat = ({ icon: Icon, label, value, hint, tone }) => (
  <div className="stat-card" data-testid={`stat-${label.toLowerCase().replaceAll(" ", "-")}`}>
    <div className={`stat-icon ${tone}`}><Icon size={21} /></div>
    <p>{label}</p><strong>{formatNumber(value)}</strong>
    {hint && <small className={hint.startsWith("+") ? "positive" : "neutral"}>{hint}</small>}
  </div>
);

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/dashboard").then((r) => setData(r.data)); }, []);
  if (!data) return <Loading />;
  const s = data.stats;

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">{new Date().toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).toUpperCase()}</p>
          <h1>Selamat datang, {user?.full_name || user?.username}</h1>
          <p className="subtitle">Berikut ringkasan aktivitas distribusi hari ini.</p>
        </div>
        <Link to="/permintaan?new=1" className="primary-button compact" data-testid="create-request-shortcut"><span>＋</span> Buat Permintaan</Link>
      </div>

      {isAdmin ? (
        <>
          <div className="stats-grid">
            <Stat icon={Package} label="Total barang" value={s.total_products} hint={`${s.low_stock_count} stok rendah`} tone="blue" />
            <Stat icon={Warehouse} label="Total stok" value={s.total_stock} hint="unit tersedia" tone="teal" />
            <Stat icon={ClipboardList} label="Permintaan pending" value={s.pending_requests} hint={`${s.total_requests} total`} tone="amber" />
            <Stat icon={Truck} label="Distribusi aktif" value={s.active_distributions} hint={`${s.completed_distributions} selesai`} tone="orange" />
          </div>

          <div className="content-grid">
            <section className="panel chart-panel">
              <div className="panel-head">
                <div><h3>Aktivitas distribusi</h3><p>6 bulan terakhir</p></div>
              </div>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.distribution_chart}>
                    <CartesianGrid vertical={false} stroke="#e8edf3" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} allowDecimals={false} />
                    <Tooltip cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="total" fill="#2563eb" radius={[5, 5, 0, 0]} barSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
            <section className="panel category-panel">
              <div className="panel-head">
                <div><h3>Barang terdistribusi</h3><p>Berdasarkan kategori</p></div>
              </div>
              <div className="donut">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={data.category_chart} dataKey="value" innerRadius={55} outerRadius={78} paddingAngle={4}>
                      {data.category_chart.map((e) => <Cell key={e.name} fill={e.color} />)}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div><strong>{formatNumber(data.category_chart.reduce((a, x) => a + x.value, 0))}</strong><span>total unit</span></div>
              </div>
              <div className="legend">
                {data.category_chart.map((e) => (
                  <span key={e.name}><i style={{ background: e.color }} />{e.name}<b>{e.value}</b></span>
                ))}
              </div>
            </section>
          </div>

          <section className="panel table-panel">
            <div className="panel-head">
              <div><h3>Permintaan terbaru</h3><p>Permintaan yang membutuhkan perhatian</p></div>
              <Link to="/permintaan" className="text-button">Lihat semua <span>→</span></Link>
            </div>
            {data.recent_requests.length === 0 ? <EmptyState /> : (
              <div className="table-scroll"><table>
                <thead><tr><th>NO. PERMINTAAN</th><th>PEMOHON</th><th>BARANG</th><th>JUMLAH</th><th>STATUS</th><th>TANGGAL</th></tr></thead>
                <tbody>{data.recent_requests.map((r) => (
                  <tr key={r.number}><td><b className="request-id">{r.number}</b></td><td>{r.requester}</td>
                    <td>{r.item}</td><td>{r.quantity}</td><td><StatusBadge status={r.status} /></td><td>{r.created_at}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </section>

          {data.low_stock.length > 0 && (
            <section className="low-stock" data-testid="low-stock-section">
              <div className="low-stock-icon"><AlertTriangle size={22} /></div>
              <div>
                <b>Perhatian stok rendah</b>
                <p>{data.low_stock.length} barang di bawah stok minimum: {data.low_stock.slice(0, 3).map((p) => p.name).join(", ")}{data.low_stock.length > 3 ? "…" : ""}</p>
              </div>
              <Link to="/stok" className="outline-button" data-testid="review-stock-button">Tinjau stok</Link>
            </section>
          )}
        </>
      ) : (
        <>
          <div className="stats-grid">
            <Stat icon={ClipboardList} label="Total permintaan saya" value={s.total_requests} tone="blue" />
            <Stat icon={ClipboardList} label="Menunggu" value={s.pending_requests} tone="amber" />
            <Stat icon={Truck} label="Distribusi berjalan" value={s.active_distributions} tone="teal" />
            <Stat icon={Truck} label="Selesai" value={s.completed_distributions} tone="orange" />
          </div>
          <section className="panel table-panel">
            <div className="panel-head"><div><h3>Riwayat permintaan</h3><p>Permintaan Anda</p></div></div>
            {data.recent_requests.length === 0 ? <EmptyState desc="Buat permintaan pertama Anda untuk memulai." /> : (
              <div className="table-scroll"><table>
                <thead><tr><th>NO. PERMINTAAN</th><th>BARANG</th><th>JUMLAH</th><th>STATUS</th><th>TANGGAL</th></tr></thead>
                <tbody>{data.recent_requests.map((r) => (
                  <tr key={r.number}><td><b className="request-id">{r.number}</b></td>
                    <td>{r.item}</td><td>{r.quantity}</td><td><StatusBadge status={r.status} /></td><td>{r.created_at}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </section>
        </>
      )}
    </>
  );
}
