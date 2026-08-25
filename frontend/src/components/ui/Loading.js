export default function Loading({ label = "Memuat data..." }) {
  return <div className="loading" data-testid="loading">{label}</div>;
}
