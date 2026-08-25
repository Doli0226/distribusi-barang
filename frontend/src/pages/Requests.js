import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import StatusBadge from "@/components/ui/StatusBadge";

const TABS = [
  { key: "", label: "Semua" },
  { key: "pending", label: "Menunggu" },
  { key: "approved", label: "Disetujui" },
  { key: "rejected", label: "Ditolak" },
  { key: "completed", label: "Selesai" },
];

export default function Requests() {
  const { isAdmin } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState(null);
  const [tab, setTab] = useState("");
  const [modal, setModal] = useState(null);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [recipients, setRecipients] = useState([]);

  const load = () => api.get("/requests").then((r) => setItems(r.data.items));

  useEffect(() => {
    load();
    Promise.all([api.get("/products"), api.get("/warehouses"), api.get("/recipients")]).then(([p, w, r]) => {
      setProducts(p.data.items); setWarehouses(w.data.items); setRecipients(r.data.items);
    });
    if (params.get("new") === "1") setModal(newForm());
  }, []);

  function newForm() {
    return {
      warehouse_id: "", recipient_id: "", destination: "", needed_date: "",
      note: "", items: [{ product_id: "", quantity: 1 }],
    };
  }
  const setLine = (idx, field, val) => setModal((m) => ({
    ...m, items: m.items.map((it, i) => (i === idx ? { ...it, [field]: val } : it)),
  }));

  const create = async () => {
    if (!modal.warehouse_id || !modal.recipient_id || !modal.destination) return toast.show("Lengkapi form", "danger");
    if (modal.items.some((i) => !i.product_id || !i.quantity)) return toast.show("Lengkapi item", "danger");
    try {
      const r = await api.post("/requests", modal);
      toast.show(`Permintaan ${r.data.number} berhasil dibuat`, "success");
      setModal(null); setParams({}); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };

  const counts = useMemo(() => {
    if (!items) return {};
    const c = { "": items.length };
    for (const it of items) c[it.status] = (c[it.status] || 0) + 1;
    return c;
  }, [items]);

  const list = items?.filter((i) => !tab || i.status === tab) ?? [];
  if (items === null) return <Loading />;

  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">WORKFLOW</p><h1>{isAdmin ? "Permintaan barang" : "Permintaan saya"}</h1>
          <p className="subtitle">{isAdmin ? "Review dan proses permintaan dari tim." : "Buat dan pantau permintaan Anda."}</p>
        </div>
        <button className="primary-button compact" onClick={() => setModal(newForm())} data-testid="new-request-button">＋ Buat permintaan</button>
      </div>
      <section className="panel product-page">
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t.key} className={tab === t.key ? "active" : ""} onClick={() => setTab(t.key)} data-testid={`req-tab-${t.key || "all"}`}>
              {t.label} <b>{counts[t.key] || 0}</b>
            </button>
          ))}
        </div>
        {list.length === 0 ? <EmptyState /> : (
          <div className="table-scroll"><table>
            <thead><tr><th>NO. PERMINTAAN</th><th>PEMOHON</th><th>BARANG</th><th>TUJUAN</th><th>STATUS</th><th>TANGGAL</th><th></th></tr></thead>
            <tbody>{list.map((r) => (
              <tr key={r.id} data-testid={`request-row-${r.number}`}>
                <td><b className="request-id">{r.number}</b></td>
                <td>{r.requester_name}</td>
                <td>{r.items[0]?.product_name || "-"}<small className="table-sub">{r.total_quantity} unit, {r.items.length} item</small></td>
                <td>{r.destination}</td>
                <td><StatusBadge status={r.status} /></td>
                <td>{r.created_at}</td>
                <td><div className="row-actions">
                  <button onClick={() => nav(`/permintaan/${r.id}`)} data-testid={`view-request-${r.number}`}>Detail</button>
                </div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </section>

      {modal && (
        <Modal onClose={() => { setModal(null); setParams({}); }} wide eyebrow="PERMINTAAN BARU" title="Buat permintaan barang" subtitle="Lengkapi detail kebutuhan distribusi Anda.">
          <div className="two-col-form">
            <label>Gudang tujuan<select required data-testid="req-warehouse" value={modal.warehouse_id} onChange={(e) => setModal({ ...modal, warehouse_id: e.target.value })}>
              <option value="">- pilih -</option>{warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select></label>
            <label>Penerima<select required data-testid="req-recipient" value={modal.recipient_id} onChange={(e) => setModal({ ...modal, recipient_id: e.target.value })}>
              <option value="">- pilih -</option>{recipients.map((r) => <option key={r.id} value={r.id}>{r.name} · {r.city}</option>)}
            </select></label>
            <label>Tanggal kebutuhan<input type="date" data-testid="req-needed-date" value={modal.needed_date} onChange={(e) => setModal({ ...modal, needed_date: e.target.value })} /></label>
            <label>Kota tujuan / alamat<input required data-testid="req-destination" value={modal.destination} onChange={(e) => setModal({ ...modal, destination: e.target.value })} placeholder="Kota atau alamat lengkap" /></label>
          </div>

          <div style={{ marginTop: 22 }}>
            <b style={{ fontSize: 12 }}>Barang yang diminta</b>
            {modal.items.map((it, i) => (
              <div key={i} className="two-col-form" style={{ marginTop: 8 }}>
                <label>Barang<select required data-testid={`req-item-product-${i}`} value={it.product_id} onChange={(e) => setLine(i, "product_id", e.target.value)}>
                  <option value="">- pilih -</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
                </select></label>
                <label>Jumlah<input type="number" min={1} required data-testid={`req-item-qty-${i}`} value={it.quantity} onChange={(e) => setLine(i, "quantity", Number(e.target.value))} /></label>
              </div>
            ))}
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button type="button" className="link-btn" onClick={() => setModal({ ...modal, items: [...modal.items, { product_id: "", quantity: 1 }] })} data-testid="req-add-item">＋ Tambah item</button>
              {modal.items.length > 1 && <button type="button" className="link-btn" style={{ color: "#dc2626" }} onClick={() => setModal({ ...modal, items: modal.items.slice(0, -1) })}>− Hapus item terakhir</button>}
            </div>
          </div>
          <label>Catatan<textarea data-testid="req-note" value={modal.note} onChange={(e) => setModal({ ...modal, note: e.target.value })} placeholder="Catatan tambahan (opsional)" /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => { setModal(null); setParams({}); }}>Batal</button>
            <button className="primary-button" onClick={create} data-testid="req-submit-button">Kirim permintaan <span>→</span></button>
          </div>
        </Modal>
      )}
    </>
  );
}
