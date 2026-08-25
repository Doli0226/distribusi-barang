import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import { formatNumber } from "@/constants/status";

export default function Stock() {
  const { isAdmin } = useAuth();
  const toast = useToast();
  const [stocks, setStocks] = useState(null);
  const [txs, setTxs] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [tab, setTab] = useState("current");
  const [modal, setModal] = useState(null);

  const load = async () => {
    const [s, t, p, w] = await Promise.all([api.get("/stocks"), api.get("/stocks/transactions"),
                                              api.get("/products"), api.get("/warehouses")]);
    setStocks(s.data.items); setTxs(t.data.items);
    setProducts(p.data.items); setWarehouses(w.data.items);
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    try {
      const f = modal;
      if (!f.product_id || !f.warehouse_id || !f.quantity) return toast.show("Lengkapi form", "danger");
      await api.post("/stocks/transaction", f);
      toast.show("Transaksi tersimpan", "success"); setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };

  if (stocks === null) return <Loading />;
  const low = stocks.filter((s) => s.low_stock);
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">INVENTORI</p><h1>Stok & mutasi</h1><p className="subtitle">Pantau stok per gudang dan riwayat mutasi.</p></div>
        {isAdmin && <button className="primary-button compact" onClick={() => setModal({ type: "in", product_id: "", warehouse_id: "", quantity: 1, note: "" })} data-testid="stock-tx-button">＋ Transaksi stok</button>}
      </div>
      {low.length > 0 && (
        <section className="low-stock" data-testid="low-stock-panel">
          <div className="low-stock-icon"><AlertTriangle size={22} /></div>
          <div><b>Stok rendah</b><p>{low.length} item di bawah stok minimum. Segera lakukan penambahan.</p></div>
        </section>
      )}
      <section className="panel product-page" style={{ marginTop: 18 }}>
        <div className="tabs">
          <button className={tab === "current" ? "active" : ""} onClick={() => setTab("current")} data-testid="tab-current-stock">Stok saat ini <b>{stocks.length}</b></button>
          <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")} data-testid="tab-stock-history">Riwayat mutasi <b>{txs.length}</b></button>
        </div>
        {tab === "current" ? (
          stocks.length === 0 ? <EmptyState /> : (
            <div className="table-scroll"><table>
              <thead><tr><th>SKU</th><th>BARANG</th><th>GUDANG</th><th>STOK</th><th>MIN</th><th>STATUS</th></tr></thead>
              <tbody>{stocks.map((s) => (
                <tr key={s.id} data-testid={`stock-row-${s.id}`}>
                  <td><b className="request-id">{s.product_sku}</b></td>
                  <td>{s.product_name}<small className="table-sub">{s.category} · {s.unit}</small></td>
                  <td>{s.warehouse_name}</td>
                  <td><strong>{formatNumber(s.quantity)}</strong></td>
                  <td>{s.minimum_stock}</td>
                  <td><span className={`badge ${s.low_stock ? "red" : "green"}`}>{s.low_stock ? "Rendah" : "Aman"}</span></td>
                </tr>
              ))}</tbody>
            </table></div>
          )
        ) : (
          txs.length === 0 ? <EmptyState desc="Belum ada transaksi stok." /> : (
            <div className="table-scroll"><table>
              <thead><tr><th>TANGGAL</th><th>TIPE</th><th>SKU</th><th>BARANG</th><th>GUDANG</th><th>JUMLAH</th><th>SALDO</th><th>USER</th><th>CATATAN</th></tr></thead>
              <tbody>{txs.map((t) => (
                <tr key={t.id}>
                  <td>{t.created_at}</td>
                  <td><span className={`badge ${t.type === "in" ? "green" : t.type === "out" ? "red" : "blue"}`}>{t.type.toUpperCase()}</span></td>
                  <td>{t.sku}</td><td>{t.product}</td><td>{t.warehouse}</td>
                  <td><strong>{formatNumber(t.quantity)}</strong></td><td>{formatNumber(t.balance_after)}</td>
                  <td>{t.user}</td><td>{t.note || "-"}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )
        )}
      </section>

      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow="STOK" title="Transaksi stok" subtitle="Tambah, keluar, atau penyesuaian stok gudang.">
          <div className="two-col-form">
            <label>Tipe<select data-testid="tx-type" value={modal.type} onChange={(e) => setModal({ ...modal, type: e.target.value })}>
              <option value="in">Masuk</option><option value="out">Keluar</option><option value="adjust">Penyesuaian</option>
            </select></label>
            <label>Jumlah<input type="number" min={1} data-testid="tx-qty" value={modal.quantity} onChange={(e) => setModal({ ...modal, quantity: Number(e.target.value) })} /></label>
            <label>Barang<select data-testid="tx-product" value={modal.product_id} onChange={(e) => setModal({ ...modal, product_id: e.target.value })}>
              <option value="">- pilih -</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
            </select></label>
            <label>Gudang<select data-testid="tx-warehouse" value={modal.warehouse_id} onChange={(e) => setModal({ ...modal, warehouse_id: e.target.value })}>
              <option value="">- pilih -</option>{warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select></label>
          </div>
          <label>Catatan<textarea data-testid="tx-note" value={modal.note} onChange={(e) => setModal({ ...modal, note: e.target.value })} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={submit} data-testid="tx-submit">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
