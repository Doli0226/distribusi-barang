import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { api } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import Loading from "@/components/ui/Loading";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import Confirm from "@/components/ui/Confirm";
import StatusBadge from "@/components/ui/StatusBadge";
import { formatNumber } from "@/constants/status";

const emptyForm = { sku: "", name: "", category_id: "", unit: "pcs", description: "", minimum_stock: 0, active: true, image_url: "" };

export default function Products() {
  const { isAdmin } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [cats, setCats] = useState([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [modal, setModal] = useState(null); // {form, editing}
  const [confirm, setConfirm] = useState(null);
  const [page, setPage] = useState(1);
  const perPage = 8;

  const load = async () => {
    const [pRes, cRes] = await Promise.all([api.get("/products"), api.get("/categories")]);
    setItems(pRes.data.items); setCats(cRes.data.items);
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!items) return [];
    return items.filter((p) => {
      const t = `${p.name} ${p.sku}`.toLowerCase().includes(query.toLowerCase());
      const c = !category || p.category_id === Number(category);
      return t && c;
    });
  }, [items, query, category]);
  const paged = filtered.slice((page - 1) * perPage, page * perPage);
  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));

  const openNew = () => setModal({ form: { ...emptyForm, category_id: cats[0]?.id || "" }, editing: null });
  const openEdit = (p) => setModal({ form: { ...p }, editing: p.id });

  const save = async () => {
    const f = modal.form;
    if (!f.sku || !f.name || !f.category_id) return toast.show("SKU, nama, kategori wajib", "danger");
    try {
      if (modal.editing) {
        await api.put(`/products/${modal.editing}`, f);
        toast.show("Barang diperbarui", "success");
      } else {
        await api.post("/products", f);
        toast.show("Barang ditambahkan", "success");
      }
      setModal(null); load();
    } catch (e) { toast.show(e.message, "danger"); }
  };
  const deactivate = async () => {
    try { await api.delete(`/products/${confirm.id}`); toast.show("Barang dinonaktifkan", "success"); load(); }
    catch (e) { toast.show(e.message, "danger"); }
    setConfirm(null);
  };

  if (items === null) return <Loading />;
  return (
    <>
      <div className="page-heading">
        <div><p className="eyebrow">KATALOG</p><h1>Daftar barang</h1><p className="subtitle">Kelola katalog dan ketersediaan barang.</p></div>
        {isAdmin && <button className="primary-button compact" onClick={openNew} data-testid="add-product-button">＋ Tambah barang</button>}
      </div>
      <section className="panel product-page">
        <div className="filter-bar">
          <div className="search-box"><Search size={17} />
            <input data-testid="product-search-input" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Cari SKU atau nama barang..." />
          </div>
          <select data-testid="product-category-filter" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}>
            <option value="">Semua kategori</option>
            {cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        {paged.length === 0 ? <EmptyState /> : (
          <>
            <div className="table-scroll"><table>
              <thead><tr><th>SKU</th><th>NAMA</th><th>KATEGORI</th><th>STOK</th><th>MIN</th><th>STATUS</th>{isAdmin && <th></th>}</tr></thead>
              <tbody>{paged.map((p) => (
                <tr key={p.id} data-testid={`product-row-${p.sku}`}>
                  <td><b className="request-id">{p.sku}</b></td>
                  <td><strong>{p.name}</strong><small className="table-sub">Satuan: {p.unit}</small></td>
                  <td>{p.category}</td>
                  <td><strong>{formatNumber(p.stock)}</strong></td>
                  <td>{p.minimum_stock}</td>
                  <td><StatusBadge status={p.low_stock ? "Stok rendah" : (p.active ? "Aktif" : "Nonaktif")} /></td>
                  {isAdmin && <td><div className="row-actions">
                    <button onClick={() => openEdit(p)} data-testid={`edit-product-${p.sku}`}>Edit</button>
                    {p.active
                      ? <button className="danger" onClick={() => setConfirm(p)} data-testid={`deact-product-${p.sku}`}>Nonaktifkan</button>
                      : <button onClick={async () => { await api.put(`/products/${p.id}`, { active: true }); toast.show("Barang diaktifkan", "success"); load(); }} data-testid={`act-product-${p.sku}`}>Aktifkan</button>}
                  </div></td>}
                </tr>
              ))}</tbody>
            </table></div>
            {totalPages > 1 && (
              <div className="pagination">
                <span>Hal {page}/{totalPages}</span>
                <div>
                  <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>‹</button>
                  <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>›</button>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      {modal && (
        <Modal onClose={() => setModal(null)} eyebrow={modal.editing ? "EDIT" : "BARANG BARU"} title={modal.editing ? "Edit barang" : "Tambah barang"}>
          <div className="two-col-form">
            <label>SKU<input required data-testid="product-sku-input" value={modal.form.sku} onChange={(e) => setModal({ ...modal, form: { ...modal.form, sku: e.target.value } })} /></label>
            <label>Nama<input required data-testid="product-name-input" value={modal.form.name} onChange={(e) => setModal({ ...modal, form: { ...modal.form, name: e.target.value } })} /></label>
            <label>Kategori<select data-testid="product-category-input" value={modal.form.category_id} onChange={(e) => setModal({ ...modal, form: { ...modal.form, category_id: e.target.value } })}>
              <option value="">- pilih -</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select></label>
            <label>Satuan<input data-testid="product-unit-input" value={modal.form.unit} onChange={(e) => setModal({ ...modal, form: { ...modal.form, unit: e.target.value } })} /></label>
            <label>Stok minimum<input type="number" min="0" data-testid="product-min-input" value={modal.form.minimum_stock} onChange={(e) => setModal({ ...modal, form: { ...modal.form, minimum_stock: Number(e.target.value) } })} /></label>
            <label>URL Gambar<input data-testid="product-image-input" value={modal.form.image_url} onChange={(e) => setModal({ ...modal, form: { ...modal.form, image_url: e.target.value } })} /></label>
          </div>
          <label>Deskripsi<textarea data-testid="product-desc-input" value={modal.form.description} onChange={(e) => setModal({ ...modal, form: { ...modal.form, description: e.target.value } })} /></label>
          <div className="modal-actions">
            <button className="outline-button" onClick={() => setModal(null)}>Batal</button>
            <button className="primary-button" onClick={save} data-testid="product-save-button">Simpan <span>→</span></button>
          </div>
        </Modal>
      )}
      <Confirm open={!!confirm} title="Nonaktifkan barang?" message={`Barang "${confirm?.name}" akan dinonaktifkan.`}
                onClose={() => setConfirm(null)} onConfirm={deactivate} danger confirmLabel="Nonaktifkan" />
    </>
  );
}
