export default function EmptyState({ title = "Belum ada data", desc = "Data akan tampil di sini setelah tersedia." }) {
  return (
    <div className="empty-state" data-testid="empty-state">
      <b>{title}</b>
      <p>{desc}</p>
    </div>
  );
}
